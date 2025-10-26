# Search Engine Results Comparison

## 📌 Overview
This Python-based project compares **Google** and **Yahoo** search results for a set of 100 predefined queries.  
It analyzes the **ranking overlap**, **Spearman correlation**, and other metrics to measure search engine similarity.
---

## ⚙️ Technologies Used
- Python 3  
- pandas, numpy  
- requests, BeautifulSoup  
- JSON handling  
- Excel for result summary visualization
---

## 📁 Folder Structure
```
Search-Engine-Results/
│
├── .venv/               # Virtual environment
├── .vscode/             # Editor settings
├── data/                # Query and result data
├── docs/                # Project documentation
├── output/              # Final processed data
├── results/             # Spearman correlation and overlap reports
├── src/                 # Python scripts for data parsing and analysis
│
├── 100QueriesSet2       # Input query list
├── Google_Result2.json  # Example search result dataset
├── requirements.txt     # Dependencies list
├── Summary of Results.txt
└── readme
```
## 🧠 Source Code Structure
The `src` folder contains all core scripts for data collection, parsing, and evaluation. 
- `yahoo_client.py` fetches Yahoo search results
- `parser.py` extracts and cleans URLs, and
- `generate_results.py` merges data into a unified JSON.
- Evaluation scripts (`evaluate_new.py`, `evaluate_rerank.py`) compute overlap and ranking metrics, while `main.py` orchestrates the entire workflow end-to-end.

## 🚀 How to Run
- Create and activate a virtual environment:  
  `python -m venv .venv`  
  `source .venv/Scripts/activate` (Windows) or `source .venv/bin/activate` (macOS/Linux)
- Install dependencies:  
  `pip install -r requirements.txt`
- Fetch Yahoo search results for all queries:  
  `python src/main.py`
- Parse and generate combined JSON output:  
  `python src/generate_results.py`
- Evaluate overlap and ranking correlation:  
  `python src/evaluate_new.py`  
  *(Optionally re-run with `evaluate_rerank.py` for reranked data)*
- View summarized outputs (overlap %, ρ, etc.) in `/results/`  
  — includes `results.csv`, `summary.json`, and `Summary of Results.txt`


## 📈 Outputs
- **Average overlap:** 11.8% — fewer than 1.2 common results per query.  
- **Average Spearman ρ:** 0.19 — a weak positive correlation, indicating limited ranking similarity.  
 - Yahoo and Google return largely **independent** result sets, meaning users gain broader coverage by searching both engines.

## 🔄 Process Used

1. **Query Selection**  
   - 100 predefined search queries were used to ensure a consistent comparison across both Yahoo and Google.  
   - Queries covered diverse topics to avoid domain bias.

2. **Data Collection**  
   - For each query, the top-10 search results were fetched from **Yahoo** and **Google**.  
   - Yahoo results were retrieved from `r.search.yahoo.com`, which required decoding redirect links to extract the true destination URLs.  
   - When Yahoo returned fewer than 10 results, additional pages were scraped to ensure parity with Google’s 10 results.

3. **Data Cleaning**  
   - Redirect URLs were decoded to absolute URLs.  
   - Non-organic results were filtered out — e.g., links to Yahoo-owned domains (`yahoo.com`, `flickr.com`, `tumblr.com`, `engadget.com`, etc.) and non-HTTP protocols (`mailto:`, `javascript:`, `tel:`, etc.).  
   - URLs differing only in case were treated as **distinct** (case-sensitive comparison).  
   - Fragment-only and invalid URLs were excluded to maintain uniformity.

4. **Analysis**  
   - Computed the **percentage overlap** (shared URLs between engines).  
   - Computed **Spearman’s rank correlation coefficient (ρ)** to assess ranking similarity.  
   - Aggregated results into per-query and average statistics.

5. **Result Generation**  
   - Outputs were stored as `results.csv` and `results_summary.json`.  
   - A text summary (`Summary of Results.txt`) consolidates final findings.
---
### 📈 Spearman Rank Correlation Calculation

To measure how similarly Yahoo and Google ranked the overlapping URLs, the **Spearman’s rank correlation coefficient (ρ)** was used.

For each query:
1. Only URLs common to both Yahoo and Google top-10 lists were considered.  
2. Each shared URL was assigned a rank in both engines (1–10).  
3. The difference in ranks (`d`) was calculated for each URL.  
4. ρ was computed using the formula:

   \[
   \rho = 1 - \frac{6 \sum d^2}{n(n^2 - 1)}
   \]

   where *n* = number of overlapping URLs.  
5. ρ values range from **+1 (identical order)** to **–1 (inverse order)**.  

In this project, the **average ρ = 0.19**, indicating a weak positive correlation — meaning Yahoo and Google tend to rank even common results quite differently.

## 🧩 Notes
- Uses publicly available search result APIs.  
- For large result sets, analysis can be batched.  
- The project focuses on comparing **ranking similarity**, not content relevance.
