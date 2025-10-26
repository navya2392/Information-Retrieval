package edu.usc.cs.hw2;  // File: src/edu/usc/cs/hw2/ReportGenerator.java

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;

/**
 * ReportGenerator: reads the crawler CSV outputs and writes CrawlReport_<site>.txt
 * in the exact format required by HW2 Appendix A.
 *
 * Inputs (default values work for your current setup):
 *   args[0] = siteTag           (default: "USAToday")               // must match the tag used in Controller/MyCrawler
 *   args[1] = newsDomain        (default: "usatoday.com")
 *   args[2] = numberOfThreads   (default: "7")
 *   args[3] = outputDir         (default: "data" + sep + "output")
 *   args[4] = reportDir         (default: "data" + sep + "report")
 *   args[5] = studentName       (default: "Your Name")
 *   args[6] = uscId             (default: "0000000000")
 *
 * It expects the following files under outputDir:
 *   fetch_<siteTag>.csv  (columns: URL,Status)
 *   visit_<siteTag>.csv  (columns: URL,Size (Bytes),# Outlinks,Content-Type)
 *   urls_<siteTag>.csv   (columns: URL,Indicator)              // used for URL statistics; NOT submitted
 *
 * Output:
 *   reportDir/CrawlReport_<newsSite>.txt  // e.g., CrawlReport_usatoday.txt
 *
 * FAQ alignment summary:
 *  - "# fetches succeeded" counts **all 2xx** status codes (200–299).
 *  - Unique URL counting treats full URL strings distinctly (case-sensitive path; query retained).
 *  - Size buckets use 1KB = 1024 bytes, 1MB = 1024 KB.
 *  - Content types are normalized to the base type (e.g., "text/html; charset=UTF-8" -> "text/html").
 *  - Robust CSV parsing: lines with commas inside URL are safely parsed by extracting trailing fields from the end.
 */
public class ReportGenerator {

    private static final String SEP = System.getProperty("file.separator");

    public static void main(String[] args) throws Exception {
        // ==== Args with sensible defaults (easy to tweak in Eclipse Run Config) ====
        String siteTag         = argOr(args, 0, "USAToday");
        String newsDomain      = argOr(args, 1, "usatoday.com");
        String threadsStr      = argOr(args, 2, "7");
        String outputDir       = argOr(args, 3, "data" + SEP + "output");
        String reportDir       = argOr(args, 4, "data" + SEP + "report");
        String studentName     = argOr(args, 5, "Your Name");
        String uscId           = argOr(args, 6, "0000000000");

        Path fetchCsv = Paths.get(outputDir, "fetch_" + siteTag + ".csv");
        Path visitCsv = Paths.get(outputDir, "visit_" + siteTag + ".csv");
        Path urlsCsv  = Paths.get(outputDir, "urls_"  + siteTag + ".csv");

        // ==== Read CSVs (robust split from the end; safe with commas in URL) ====
        List<String[]> fetchRows = readFetchCsv(fetchCsv, true); // URL, Status
        List<String[]> visitRows = readVisitCsv(visitCsv, true); // URL, Size, Outlinks, Content-Type
        List<String[]> urlsRows  = Files.exists(urlsCsv) ? readUrlsCsv(urlsCsv, true) : Collections.emptyList();

        /*
 * STATISTIC: Fetch Statistics
 * - # fetches attempted  => attempts = number of rows in fetch_<site>.csv
 * - # fetches succeeded  => count of HTTP status in [200..299] across fetch rows
 * - # failed or aborted  => attempts - succeeded (this groups 3xx/4xx/5xx and any request that crawler4j logs as a non-2xx attempt)
 * - Status Codes table   => statusCounts map (per-code tallies), printed later in the "Status Codes" section
 * Implementation details:
 *   - We parse the status from each fetch row, ignore malformed lines (status < 0),
 *   - Update statusCounts, and if 2xx increment 'succeeded'.
 */
// ==== Fetch stats ====
        int attempts  = fetchRows.size();
        Map<Integer,Integer> statusCounts = new TreeMap<>();
        int succeeded = 0; // count all 2xx
        for (String[] row : fetchRows) {
            int status = parseIntSafe(row, 1, -1);
            // UPDATED: ignore malformed status rows so we don't emit a "-1" status bucket
            if (status >= 0) {
                statusCounts.put(status, statusCounts.getOrDefault(status, 0) + 1);
                if (status >= 200 && status <= 299) succeeded++;
            }
        }
        int failedOrAborted = attempts - succeeded; // includes 3xx/4xx/5xx and timeouts mapped by crawler4j

        /*
 * STATISTIC: Outgoing URLs
 * - Total URLs extracted     => totalExtracted = number of rows in urls_<site>.csv (includes repeats by design)
 * - # unique URLs extracted  => |uniqueAll| (HashSet of every URL string; case-sensitive path, query retained)
 * - # unique within site     => |uniqueOK| (URLs labeled "OK" by the crawler as same-site)
 * - # unique outside site    => |uniqueNOK| (URLs labeled "N_OK" by the crawler as off-site)
 * Implementation detail:
 *   - We do not re-evaluate domain here; we trust MyCrawler's labeling per FAQ, so generator remains pure aggregation.
 */
// ==== Outgoing URLs (urls_*.csv) ====
        int totalExtracted = urlsRows.size(); // includes repeats by design
        Set<String> uniqueAll  = new HashSet<>();
        Set<String> uniqueOK   = new HashSet<>();
        Set<String> uniqueNOK  = new HashSet<>();
        for (String[] row : urlsRows) {
            if (row.length < 2) continue;
            String url  = row[0].trim();
            String flag = row[1].trim();
            uniqueAll.add(url);
            if ("OK".equalsIgnoreCase(flag)) uniqueOK.add(url);
            else uniqueNOK.add(url);
        }

        /*
 * STATISTICS: File Sizes & Content Types (from visit_<site>.csv)
 * - File size buckets: <1KB, 1KB~<10KB, 10KB~<100KB, 100KB~<1MB, >=1MB
 *   * Uses 1KB = 1024 bytes, 1MB = 1024 KB (per PDF).
 *   * Each visited row contributes exactly one bucket; sum equals visitRows.size().
 * - Content types: counts by base MIME type (e.g., "text/html"; parameters like charset are stripped).
 * Notes:
 *   - visit_<site>.csv should contain only allowed MIME types (HTML, images, PDF, DOC) because MyCrawler filters; 
 *     therefore, 'visit' count may be less than 2xx fetches and that's OK (FAQ).
 */
// ==== File-size buckets & content-types (visit_*.csv) ====
        long lt1KB = 0, bt1_10KB = 0, bt10_100KB = 0, bt100KB_1MB = 0, ge1MB = 0;
        Map<String,Integer> ctypeCounts = new TreeMap<>();
        for (String[] row : visitRows) {
            // UPDATED: use long for size to be extra safe with large files
            long size = parseLongSafe(row, 1, 0L);
            String ctype = row.length >= 4 ? normalizeBaseContentType(row[3]) : "";
            if (!ctype.isEmpty()) {
                ctypeCounts.put(ctype, ctypeCounts.getOrDefault(ctype, 0) + 1);
            }
            if (size < 1024L) lt1KB++;
            else if (size < 10L * 1024L) bt1_10KB++;
            else if (size < 100L * 1024L) bt10_100KB++;
            else if (size < 1024L * 1024L) bt100KB_1MB++;
            else ge1MB++;
        }

        /*
 * WRITING THE REPORT:
 *   The following block prints the five report sections in Appendix A using the values computed above:
 *   1) "Fetch Statistics"   -> attempts, succeeded, failedOrAborted
 *   2) "Outgoing URLs"      -> totalExtracted, |uniqueAll|, |uniqueOK|, |uniqueNOK|
 *   3) "Status Codes"       -> iterate statusCounts (one line per HTTP code)
 *   4) "File Sizes"         -> five size-bucket counters
 *   5) "Content Types"      -> MIME tallies in ctypeCounts (base types)
 */
// ==== Build report text ====
        String reportName = "CrawlReport_" + domainBase(newsDomain) + ".txt"; // e.g., CrawlReport_usatoday.txt
        Files.createDirectories(Paths.get(reportDir));
        Path reportPath = Paths.get(reportDir, reportName);

        try (PrintWriter out = new PrintWriter(Files.newBufferedWriter(reportPath))) {
            out.println("Name: " + studentName);
            out.println("USC ID: " + uscId);
            out.println("News site crawled: " + newsDomain);
            out.println("Number of threads: " + threadsStr);
            out.println();

            out.println("Fetch Statistics:");
            out.println("==================");
            out.println("# fetches attempted: " + attempts);
            out.println("# fetches succeeded: " + succeeded);
            out.println("# fetches failed or aborted: " + failedOrAborted);
            out.println();

            out.println("Outgoing URLs:");
            out.println("==============");
            out.println("Total URLs extracted: " + totalExtracted);
            out.println("# unique URLs extracted: " + uniqueAll.size());
            out.println("# unique URLs within News Site: " + uniqueOK.size());
            out.println("# unique URLs outside News Site: " + uniqueNOK.size());
            out.println();

            out.println("Status Codes:");
            out.println("=============");
            for (Map.Entry<Integer,Integer> e : statusCounts.entrySet()) {
                out.println(e.getKey() + ": " + e.getValue());
            }
            out.println();

            out.println("File Sizes:");
            out.println("===========");
            out.println("< 1KB: " + lt1KB);
            out.println("1KB ~ <10KB: " + bt1_10KB);
            out.println("10KB ~ <100KB: " + bt10_100KB);
            out.println("100KB ~ <1MB: " + bt100KB_1MB);
            out.println(">= 1MB: " + ge1MB);
            out.println();

            out.println("Content Types:");
            out.println("==============");
            for (Map.Entry<String,Integer> e : ctypeCounts.entrySet()) {
                out.println(e.getKey() + ": " + e.getValue());
            }
        }

        /*
 * SANITY CHECKS (console only; not part of the report):
 * - Warn if visit row count != #2xx fetches (expected when crawler filters non-HTML/CSS/JS/JSON etc.)
 * - Warn if size-bucket sum != visit row count (should match exactly)
 * - Info if uniqueWithin + uniqueOutside != uniqueAll (would indicate inconsistent OK/N_OK labeling)
 */
// ==== Sanity checks to console (not in report) ====
        int visitCount = visitRows.size();
        if (visitCount != succeeded) {
            System.out.println("[WARN] visit.csv rows (" + visitCount + ") != #2xx in fetch.csv (" + succeeded + ")");
        }
        if (urlsRows.isEmpty()) {
            System.out.println("[INFO] urls_*.csv missing or empty — URL uniqueness stats will be zero.");
        }

        // Extra sanity checks that are NOT part of the report file
        long bucketSum = lt1KB + bt1_10KB + bt10_100KB + bt100KB_1MB + ge1MB;
        if (bucketSum != visitRows.size()) {
            System.out.println("[WARN] size-bucket sum (" + bucketSum + ") != visit.csv rows (" + visitRows.size() + ")");
        }
        if (!urlsRows.isEmpty() && (uniqueOK.size() + uniqueNOK.size() != uniqueAll.size())) {
            System.out.println("[INFO] uniqueWithin+uniqueOutside != uniqueAll — this can happen if the same URL was labeled both OK and N_OK. Check domain labeling.");
        }

        System.out.println("Wrote report to: " + reportPath.toString());
    }

    // Helper: safe arg with default
    private static String argOr(String[] args, int idx, String def) {
        return (args != null && args.length > idx && args[idx] != null && !args[idx].isEmpty()) ? args[idx] : def;
    }

    // ===== Robust CSV readers (split trailing fields from the end) =====
    /**
 * Reads fetch_<site>.csv  [URL,Status]
 * Serves statistics:
 *   - attempts (#rows), succeeded (2xx count), failedOrAborted (= attempts - succeeded),
 *   - statusCounts for "Status Codes" section.
 */
private static List<String[]> readFetchCsv(Path path, boolean skipHeader) throws IOException {
        // fetch: URL,Status — parse last comma as separator
        if (!Files.exists(path)) return Collections.emptyList();
        try (BufferedReader br = Files.newBufferedReader(path)) {
            return br.lines()
                     .skip(skipHeader ? 1 : 0)
                     .filter(s -> !s.trim().isEmpty())
                     .map(ReportGenerator::splitFetchLine)
                     .filter(Objects::nonNull)
                     .collect(Collectors.toList());
        }
    }

    /**
 * Reads urls_<site>.csv  [URL,Indicator]
 * Serves "Outgoing URLs" statistics:
 *   - total extracted (row count), uniqueAll, uniqueOK (OK), uniqueNOK (N_OK).
 */
private static List<String[]> readUrlsCsv(Path path, boolean skipHeader) throws IOException {
        // urls: URL,Indicator — parse last comma as separator
        if (!Files.exists(path)) return Collections.emptyList();
        try (BufferedReader br = Files.newBufferedReader(path)) {
            return br.lines()
                     .skip(skipHeader ? 1 : 0)
                     .filter(s -> !s.trim().isEmpty())
                     .map(ReportGenerator::splitUrlsLine)
                     .filter(Objects::nonNull)
                     .collect(Collectors.toList());
        }
    }

    /**
 * Reads visit_<site>.csv [URL,Size,Outlinks,Content-Type]
 * Serves "File Sizes" (size buckets) and "Content Types" (base MIME tallies).
 * Note: we parse trailing commas from the end so commas in URL don't break the split.
 */
private static List<String[]> readVisitCsv(Path path, boolean skipHeader) throws IOException {
        // visit: URL,Size,Outlinks,Content-Type — parse the last three commas from the end
        if (!Files.exists(path)) return Collections.emptyList();
        try (BufferedReader br = Files.newBufferedReader(path)) {
            return br.lines()
                     .skip(skipHeader ? 1 : 0)
                     .filter(s -> !s.trim().isEmpty())
                     .map(ReportGenerator::splitVisitLine)
                     .filter(Objects::nonNull)
                     .collect(Collectors.toList());
        }
    }

    /**
 * Robust line split for fetch.csv: split by the last comma only.
 * Supports URLs that may contain commas.
 */
private static String[] splitFetchLine(String line) {
        int last = line.lastIndexOf(',');
        if (last <= 0 || last >= line.length()-1) return null;
        String url = line.substring(0, last);
        String status = line.substring(last+1);
        return new String[]{url, status};
    }

    /**
 * Robust line split for urls.csv: split by the last comma only.
 */
private static String[] splitUrlsLine(String line) {
        int last = line.lastIndexOf(',');
        if (last <= 0 || last >= line.length()-1) return null;
        String url = line.substring(0, last);
        String indicator = line.substring(last+1);
        return new String[]{url, indicator};
    }

    /**
 * Robust line split for visit.csv: take the last three comma-separated fields from the end
 * to recover Size, Outlinks, and Content-Type safely when URL contains commas.
 */
private static String[] splitVisitLine(String line) {
        int last3 = line.lastIndexOf(',');
        if (last3 <= 0) return null;
        int last2 = line.lastIndexOf(',', last3 - 1);
        if (last2 <= 0) return null;
        int last1 = line.lastIndexOf(',', last2 - 1);
        if (last1 <= 0) return null;
        String url = line.substring(0, last1);
        String size = line.substring(last1 + 1, last2);
        String outlinks = line.substring(last2 + 1, last3);
        String ctype = line.substring(last3 + 1);
        return new String[]{url, size, outlinks, ctype};
    }

    /**
 * Safe integer parser used for HTTP status codes (serves Fetch Statistics & Status Codes).
 */
private static int parseIntSafe(String[] row, int idx, int def) {
        if (row == null || row.length <= idx) return def;
        try { return Integer.parseInt(row[idx].trim()); } catch (Exception e) { return def; }
    }

    // UPDATED: long parser for file sizes
/**
 * Safe long parser used for file sizes in visit.csv (serves File Sizes buckets).
 */
private static long parseLongSafe(String[] row, int idx, long def) {
    if (row == null || row.length <= idx) return def;
    try {
        return Long.parseLong(row[idx].trim());
    } catch (Exception e) {
        return def;
    }
}



    /**
 * Utility: convert "usatoday.com" -> "usatoday" to build the file name CrawlReport_usatoday.txt.
 */
private static String domainBase(String domain) {
        // Convert "usatoday.com" -> "usatoday" (matches PDF naming: CrawlReport_usatoday.txt)
        if (domain == null) return "news";
        int dot = domain.indexOf('.');
        return (dot > 0) ? domain.substring(0, dot) : domain;
    }

    /**
 * Utility: normalize content type by stripping parameters (e.g., charset);
 * used to tally base MIME types for the "Content Types" section.
 */
private static String normalizeBaseContentType(String raw) {
        if (raw == null) return "";
        String ct = raw.trim().toLowerCase();
        int sc = ct.indexOf(';');
        if (sc > 0) ct = ct.substring(0, sc).trim();  // drop charset, etc.
        return ct;
    }
}
