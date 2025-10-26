package edu.usc.cs.hw2;  // File: src/edu/usc/cs/hw2/Controller.java

// ==== crawler4j core config/types used by Controller ====
import edu.uci.ics.crawler4j.crawler.CrawlConfig;      // holds crawl settings (storage, politeness, limits)
import edu.uci.ics.crawler4j.crawler.CrawlController;  // orchestrates/forks multiple crawler threads
import edu.uci.ics.crawler4j.fetcher.PageFetcher;      // fetches pages from the web
import edu.uci.ics.crawler4j.robotstxt.RobotstxtConfig; // robots.txt config 
import edu.uci.ics.crawler4j.robotstxt.RobotstxtServer; // handles robots.txt per domain

// ==== Java stdlib (filesystem helpers) ====
import java.nio.file.Files;   // create directories for storage/output
import java.nio.file.Paths;   // build filesystem paths

/**
 * Controller: entry point that wires up crawler4j configuration and starts the crawl.
 */
public class Controller {
    public static void main(String[] args) throws Exception {
        // ===== Step 1: Define storage folder =====
        // crawler4j needs a folder to store intermediate crawl data.
        String crawlStorageFolder = System.getProperty("user.dir")
                + System.getProperty("file.separator") + "data"
                + System.getProperty("file.separator") + "crawl";

        // ===== Step 2: Define crawler settings =====
        int numberOfCrawlers = 7;     // number of concurrent threads 
        int maxPagesToFetch = 10000;  // stop after ~10k fetch attempts
        int politenessDelay = 1000;    // milliseconds between requests *per thread* 
        int maxDepth = 16;            // per HW2 PDF: limit crawl depth to 16 levels

        // ---- Ensure storage and output directories exist (prevents /data/crawl error) ----
		String sep = System.getProperty("file.separator"); 
		String outputDir = System.getProperty("user.dir") + sep + "data" + sep + "output"; // output folder
		Files.createDirectories(Paths.get(crawlStorageFolder)); // create crawl storage folder, i.e. /data/crawl
		Files.createDirectories(Paths.get(outputDir)); // create output folder, i.e. /data/output

		// ===== Step 3: Configure the crawler =====
        CrawlConfig config = new CrawlConfig();                 // create config object to store crawler settings
        config.setCrawlStorageFolder(crawlStorageFolder);       // where crawler4j stores frontier/checkpoints
        config.setPolitenessDelay(politenessDelay);             // politeness to avoid hammering servers
        config.setMaxPagesToFetch(maxPagesToFetch);             // global hard stop on fetch attempts
        config.setMaxDepthOfCrawling(maxDepth);                 // max link depth to crawl 
        config.setIncludeHttpsPages(true);                      // modern sites are HTTPS-first
        config.setIncludeBinaryContentInCrawling(true);         // include HTML, images, PDF/DOC so visit.csv can log them
        config.setResumableCrawling(false);                     // keep off unless you implement resume
        
        // =====  network guardrails =====
        config.setConnectionTimeout(30_000);                    // ms to wait to connect to a server
        config.setSocketTimeout(30_000);                        // ms to wait for data on an established connection
        config.setMaxDownloadSize(10 * 1024 * 1024);            // 10 MB max per page (default 1 MB)

        // ===== Step 4: Set up robots.txt compliance =====
        PageFetcher pageFetcher = new PageFetcher(config);      // fetcher honoring config (timeouts, politeness)
        RobotstxtConfig robotsConfig = new RobotstxtConfig();   // create robots.txt config
        robotsConfig.setEnabled(true);                          // enable robots.txt handling
        RobotstxtServer robotsServer = new RobotstxtServer(robotsConfig, pageFetcher); // uses fetcher to get robots.txt

        // ===== Step 5: Initialize CrawlController =====
        CrawlController controller = new CrawlController(config, pageFetcher, robotsServer); // orchestrator

        // ===== Step 6: Define seed URLs =====
		controller.addSeed("https://www.usatoday.com/");


        // ===== Step 7: Open CSV outputs and start the crawl =====
		// Open CSV writers before starting crawl (so MyCrawler can use them)
		MyCrawler.configureOutputs("USAToday", outputDir); 

		// Start the crawl
        System.out.println("Starting crawl with " + numberOfCrawlers + " threads..."); // console marker
        controller.start(MyCrawler.class, numberOfCrawlers);     // this call blocks until crawling is finished

		// Close CSV writers after crawl ends
		MyCrawler.closeOutputs();
		System.out.println("Crawl finished.");               
    }
}
