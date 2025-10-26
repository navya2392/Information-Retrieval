Project: HW2Navya
Language: Java + crawler4j 4.4.0 (SLF4J + Logback)
Package: edu.usc.cs.hw2
News site: https://www.usatoday.com/  (domain key: usatoday.com)
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

1) Controller configuration / settings
- Seed: https://www.usatoday.com/
- Threads: 7, Max pages to fetch: 10,000, Max depth: 16, Politeness delay: 1500 ms, Max download size per page: 10 MB (to speed up crawling) 
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

2) Code structure 
- Controller.java wires crawler4j (CrawlConfig, PageFetcher, RobotstxtServer), sets knobs (threads/depth/politeness/max pages/10MB cap), seeds usatoday.com, and starts the crawl (controller.start(MyCrawler.class, threads)).
- MyCrawler.java extends WebCrawler and produces the three CSVs: fetch_*.csv (every attempt), visit_*.csv (only allowed successful visits), urls_*.csv (all discovered outlinks labeled OK/N_OK).

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
3) Workflow & filtering logic
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
A. URL discovery & filtering: 
   1) Normalize URL to lowercase for checks.
   2) Scheme filter: allow only http:// or https://. 
   3) Extension filter: reject .css, .js, .json, .zip, .rar, .gz. I
   4) Same-website rule:  domain == usatoday.com and subdomain ∈ {"", "www"}.OK if domain == usatoday.com and subdomain ∈ {"", "www"}; N_OK otherwise.
   [Impact: offsite links appear in urls.csv as N_OK (increases N_OK), but do not add to fetch/visit counts; keeps fetch.csv/visit.csv focused on the target site.]
   5) Duplicates: Frontier (crawler4j queue) de-dup happens after shouldVisit(...) returns true. crawler4j keeps an internal “seen” set. If a candidate URL has already been seen/enqueued/fetched, it won’t be enqueued again. This cuts down duplicate fetch attempts.
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
B. Writing to csv files 
   6) Log every HTTP attempt logs to fetch_*.csv via handlePageStatusCode(URL, status) (2xx/3xx/4xx/5xx).
      [Impact: fetch.csv is the complete ledger; counts here can be greater than visit rows.]
   7) Content-Type normalized, e.g., "text/html; charset=UTF-8" → "text/html" for cleaner aggregation for content-type tallies.  
   8) If allowed → write (URL, SizeBytes, #Outlinks, BaseContentType) to visit_*.csv.
       Allowed for visit.csv: text/html, image/*, application/pdf, application/msword, application/vnd.openxmlformats-officedocument.wordprocessingml.document.
      Excluded from visit.csv: CSS/JS/JSON (even if 2xx).
   9) If HTML: extract outlinks; write each to urls_*.csv as (URL, OK|N_OK) using the same-website rule.
       [Impact: urls.csv grows quickly (duplicates allowed); only HTML pages contribute outlinks, so images/PDF/DOC usually have Outlinks=0.]
   10) Redirects: For 3xx, record the redirect target URL in urls_*.csv with OK/N_OK.
       [Note: increases urls.csv totals and OK/N_OK counts; fetch.csv still records the 3xx status for the attempt.]
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
4) Other comments on filtering: 
- Note: Why 2xx in fetch.csv (e.g., 9795) ≠ visit rows (e.g., 9629): fetch.csv logs all 2xx responses; visit.csv only records allowed MIME (HTML, images, PDF, DOC/DOCX). So 2xx JSON/CSS/JS are counted as successful fetches but not written to visit.csv.
- 10MB max per page enforced to avoid oversized responses.
- I counted all 2xx as “succeeded” (not just 200).
- Outlinks are extracted only from HTML pages and then written to urls_*.csv (OK/N_OK), which also affects #Outlinks in visit.csv

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
5) Statistics calculation 
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Fetch Statistics (from fetch_*.csv)
- # fetches attempted = number of lines in fetch_*.csv.
- # fetches succeeded = all 2xx (200–299). 
- # failed or aborted = attempted − succeeded (includes 3xx/4xx/5xx and any aborted/timeouts).
- Status Codes: exact count of each HTTP status present (200, 301, 404, …).
Note: The number of correct responses (2xx) is high and the number of 3xx/4xx/5xx is comparatively low possibly because the crawler aggressively filters and gates URLs before fetching, is polite, and only targets first-party pages
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Outgoing URLs (from urls_*.csv)
- Total URLs extracted = lines in urls_*.csv (including repeats).
- # unique URLs extracted = unique count of the URL column.
- # unique URLs within News Site = unique URL where Indicator == "OK".
- # unique URLs outside News Site = unique URL where Indicator == "N_OK".
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Visits / Sizes / Content Types (from visit_*.csv)
- File size buckets (1KB = 1024B): <1KB, 1KB–<10KB, 10KB–<100KB, 100KB–<1MB, ≥1MB.
- Content types: normalize to the base MIME ("text/html; charset=UTF-8" → "text/html") and tally counts by base type

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
6) AI tool disclosure
- Tool used: ChatGPT.
- LLM contributions: starter scaffold (controller wiring and crawler skeleton), CSV writer utilities, detailed in-code comments, and configuration alignment (robots on, depth/politeness choices, domain rule, MIME filters, 10MB cap).
- My contributions: Eclipse setup and classpath fixes, choosing seed/parameters, executing smoke/full runs, validating CSV outputs, finalizing same-website rule and MIME filters, and tuning runtime knobs (threads/politeness) for stability.
