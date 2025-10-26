package edu.usc.cs.hw2;  // File: src/edu/usc/cs/hw2/MyCrawler.java

// ===== Imports specific to MyCrawler =====
import edu.uci.ics.crawler4j.crawler.Page;        // fetched page (content + metadata)
import edu.uci.ics.crawler4j.crawler.WebCrawler;   // base crawler class to extend
import edu.uci.ics.crawler4j.url.WebURL;           // wrapper for discovered URLs
import edu.uci.ics.crawler4j.parser.HtmlParseData; // HTML parse data (title/text/outgoing URLs)

// Java stdlib
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.file.Files;   // createDirectories + newBufferedWriter
import java.nio.file.Paths;   // build output file paths
import java.util.Set;                               // iterate outlinks per page
import java.util.regex.Pattern;                    // filter binary/static URLs

/*
 * =============================== Flow of Program  ===============================

* - Controller creates the CrawlConfig/PageFetcher/RobotstxtServer and then calls controller.start(MyCrawler.class, nThreads).
* - crawler4j will construct multiple instances of this MyCrawler (one per thread).
* - BEFORE start(...), Controller calls: MyCrawler.configureOutputs(<siteTag>, <outDir>) to open CSV writers.
* - DURING the crawl:
*     • shouldVisit(...) is asked for each discovered URL to decide if it should be enqueued (FETCH step).
*     • handlePageStatusCode(...) is called on every fetch attempt (success or failure) — log to fetch_*.csv.
*     • visit(...) is called after a successful fetch+parse — log to visit_*.csv and emit outlinks to urls_*.csv.
*     • onRedirectedStatusCode(...) fires on 3xx redirects — record the redirect target in urls_*.csv.
* - AFTER start(...) returns, Controller calls: MyCrawler.closeOutputs() to flush/close the CSV files.
* ==================================================================================================
 */

/**
 * MyCrawler: per-thread crawler logic (place in its own file).
* Extends WebCrawler and overrides the following methods: 
* - shouldVisit: decide whether to fetch a URL
* - visit: process the fetched page
* - handlePageStatusCode: log all fetch attempts (success and failure)
* Also includes static methods to configure and close shared CSV writers.
* Generates the three CSVs
*   1) fetch_<NewsSite>.csv  : URL, Status  — one row for every fetch attempt (2xx/3xx/4xx/5xx).
*   2) visit_<NewsSite>.csv  : URL, Size (Bytes), # Outlinks, Content-Type — only for allowed successful visits.
*   3) urls_<NewsSite>.csv   : URL, Indicator(OK|N_OK) for every discovered outlink (including repeats).
*/
public class MyCrawler extends WebCrawler {

    // ====== Thread-safe CSV writers shared by all crawler threads ======
    private static PrintWriter fetchWriter;  // Writer for fetch_<site>.csv
    private static PrintWriter visitWriter;  // Writer for visit_<site>.csv 
    private static PrintWriter urlsWriter;   // Writer for urls_<site>.csv 

    /**
     * configureOutputs: called by Controller BEFORE controller.start(...)
     * Opens the three CSV files in <outDir> and writes headers. Synchronized so only first thread does it.
     */
    public static synchronized void configureOutputs(String siteTag, String outDir) throws IOException {
        // Create output directory if missing and open writers (overwrite files each run)
        
    	Files.createDirectories(Paths.get(outDir)); // ensure output directory exists
        if (fetchWriter != null) return; // if already configured, do nothing (only first thread does this)
        
        // Open writers for the three CSV files
        fetchWriter = new PrintWriter(Files.newBufferedWriter(Paths.get(outDir, "fetch_" + siteTag + ".csv"))); 
        visitWriter = new PrintWriter(Files.newBufferedWriter(Paths.get(outDir, "visit_" + siteTag + ".csv")));
        urlsWriter  = new PrintWriter(Files.newBufferedWriter(Paths.get(outDir,  "urls_"  + siteTag + ".csv")));

        // CSV headers for each file
        fetchWriter.println("URL,Status");
        visitWriter.println("URL,Size (Bytes),# Outlinks,Content-Type");
        urlsWriter.println("URL,Indicator"); // OK or N_OK
    }

    /**
     * closeOutputs: called by Controller AFTER controller.start(...) returns.
     * Flushes and closes the writers.  Synchronized to avoid conflicts.
     */
    public static synchronized void closeOutputs() {
        if (fetchWriter != null) { fetchWriter.flush(); fetchWriter.close(); fetchWriter = null; }
        if (visitWriter != null) { visitWriter.flush(); visitWriter.close(); visitWriter = null; }
        if (urlsWriter  != null) { urlsWriter.flush();  urlsWriter.close();  urlsWriter  = null; }
    }

    // Crawler configuration constants, filter out JSON/CSS/ZIP/ARCHIVE files
    private static final Pattern FILTERS = Pattern.compile(
        ".*(\\.(css|js|json|zip|rar|gz))$", // Regex filters for static resources (case-insensitive)
        Pattern.CASE_INSENSITIVE); 

    // Domain used to define the same "website": only bare domain or 'www' are in-domain
    public static final String TARGET_DOMAIN = "usatoday.com"; 

    /**
     * shouldVisit: crawler4j asks this before enqueuing a URL. If return true, the URL will be fetched.
     * Filtering steps:
     *  - Drop static script/archive extensions via FILTERS.
     *  - Keep only http(s) schemes.
     *  - Restrict to the same website (domain == TARGET_DOMAIN and subdomain ∈ {empty, "www"}).
     */
    @Override
    public boolean shouldVisit(Page referringPage, WebURL url) {
        String href = url.getURL().toLowerCase(); // normalize URL to lowercase

        // 1) Drop obvious static/script/archive resources by extension
        if (FILTERS.matcher(href).matches()) return false;
        // 2) Only consider http/https
        boolean isHttp = href.startsWith("http://") || href.startsWith("https://");
        if (!isHttp) return false;
        // 3) Restrict FETCHING to the same website
        return isSameWebsite(url);
    }

    /** Website check: domain must equal TARGET_DOMAIN and subdomain must be empty or 'www'. 
     * Returns true if the URL is considered part of the same website.
     * This is used in shouldVisit (to restrict fetching) and in visit (to label outlinks).
     * */
    private static boolean isSameWebsite(WebURL url) {
        String domain = url.getDomain();
        String sub    = url.getSubDomain();
        if (domain == null) return false;
        boolean domainMatch = domain.equalsIgnoreCase(TARGET_DOMAIN);
        boolean subOk = (sub == null || sub.isEmpty() || sub.equalsIgnoreCase("www"));
        return domainMatch && subOk;
    }

    // Utility: replace commas in fields per FAQ (avoid breaking CSV)
    private static String safe(String s) { return (s == null) ? "" : s.replace(",", "_"); }

    // ---- Thread-safe CSV write helpers (used by overrides) ----
    // Each checks if the writer is non-null (in case configureOutputs was not called)
    private static synchronized void writeFetch(String url, int status) { 
        if (fetchWriter != null) { fetchWriter.println(safe(url) + "," + status); fetchWriter.flush(); }
    }
    private static synchronized void writeVisit(String url, int size, int outlinks, String contentType) {
        if (visitWriter != null) { visitWriter.println(safe(url) + "," + size + "," + outlinks + "," + contentType); visitWriter.flush(); }
    }
    private static synchronized void writeUrl(String url, String flag) {
        if (urlsWriter != null) { urlsWriter.println(safe(url) + "," + flag); urlsWriter.flush(); }
    }

    // ===== CSV #1: one row per attempt (success OR failure) =====
    @Override
    protected void handlePageStatusCode(WebURL webUrl, int statusCode, String statusDescription) {
        // Called for *every* fetch attempt, regardless of success.
        writeFetch(webUrl.getURL(), statusCode);
    }

    // Log redirect targets as discovered URLs (so urls_*.csv includes them per FAQ)
    protected void onRedirectedStatusCode(Page page, WebURL url, int statusCode, WebURL redirectedUrl) {
        if (redirectedUrl != null) {
            boolean ok = isSameWebsite(redirectedUrl);
            writeUrl(redirectedUrl.getURL(), ok ? "OK" : "N_OK");
        }
    }

    // ===== CSV #2 and #3: after a successful visit =====
    @Override
    public void visit(Page page) {
        // Only called when fetch succeeded and content was parsed.
        String url = page.getWebURL().getURL(); // the URL of the page
        int sizeBytes = (page.getContentData() != null) ? page.getContentData().length : 0; // size of downloaded content in bytes
        String contentType = (page.getContentType() == null) ? "" : page.getContentType();// MIME content type of page
        
        // Below lines normalize content-type to the MIME part only (e.g., "text/html; charset=UTF-8" -> "text/html")
        int scIdx = contentType.indexOf(';'); // strip any charset or other parameters
        if (scIdx >= 0) contentType = contentType.substring(0, scIdx).trim().toLowerCase(); // keep only MIME type
        else contentType = contentType.trim().toLowerCase(); // just trim whitespace
        
        // Below lines count outgoing links. if HTML, extract outlinks and count them; else 0 outlinks.
        int outCount = 0; //Holds number of outlinks extracted
        Set<WebURL> outlinks = null; //Will hold set of outlink URLs
        if (page.getParseData() instanceof HtmlParseData) { //Only have outlinks for HTML pages because only HTML can contain hyperlinks
            HtmlParseData html = (HtmlParseData) page.getParseData(); 
            outlinks = html.getOutgoingUrls(); 
            outCount = (outlinks != null) ? outlinks.size() : 0; 
        }

        // Allowed content-types: HTML, images, and DOC/PDF variants.
        // We *exclude* CSS/JS/JSON and also ignore audio/video/etc. even if the URL has no extension.
        boolean isHtml   = contentType.startsWith("text/html");
        boolean isImage  = contentType.startsWith("image/");
        boolean isPdf    = contentType.equals("application/pdf");
        boolean isDoc    = contentType.equals("application/msword")
                         || contentType.equals("application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        boolean isCssJsJson = contentType.contains("json") || contentType.contains("javascript") || contentType.contains("text/css");
        boolean allowed = (isHtml || isImage || isPdf || isDoc) && !isCssJsJson;
        if (!allowed) {
            return; // do not record disallowed types in visit.csv
        }

        // Write visit row
        writeVisit(url, sizeBytes, outCount, contentType);

        // Emit every discovered outlink to urls_*.csv with OK / N_OK label (including repeats). Logic: if same website, write OK else N_OK
        if (outlinks != null) {
            for (WebURL out : outlinks) {
                boolean ok = isSameWebsite(out);
                writeUrl(out.getURL(), ok ? "OK" : "N_OK"); 
            }
        }
    }
}
