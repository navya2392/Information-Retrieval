
# 🧠 Information Retrieval Projects

This repository contains two projects developed as part of the **CSCI 572: Information Retrieval** course at the University of Southern California.  
Both simulate core components of a modern search engine — **Web Crawling** and **Search Result Comparison** — to demonstrate practical information retrieval concepts.

---

## 📘 Projects Overview

### 🕸️ 1. Web Crawler
A Java-based web crawler built using the `crawler4j` framework to traverse and collect web pages while obeying politeness policies and robots.txt rules. It was tested on the **USAToday** domain to analyze fetch statistics, content types, and response codes.

**Tech Stack:** Java, crawler4j, jsoup, Eclipse IDE  
**Outputs:** Crawled data, logs, unique URLs, and summary reports  
**Location:** `/Web Crawler`

---

### 🔍 2. Search Engine Results Comparison
A Python-based project comparing search results from **Yahoo** and **Google** for 100 predefined queries. It measures **overlap**, **ranking correlation**, and **diversity** using Spearman’s rank correlation coefficient (ρ).

**Tech Stack:** Python, BeautifulSoup, pandas, requests  
**Outputs:** Query-level overlap metrics, Spearman ρ, and summary reports  
**Location:** `/Search-Engine-Results`
