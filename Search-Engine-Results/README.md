# Search Engine Results Comparison

## 📌 Overview
This Python-based project compares **Google** and **Bing** search results for a set of 100 predefined queries.  
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

---

## 🚀 How to Run
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the main analysis script (inside `src/`):
   ```bash
   python compare_results.py
   ```
4. View the output reports in `/results` and `/output`.

---

## 📈 Outputs
- **Google vs Bing Overlap**  
- **Spearman Correlation** between rankings  
- **Top-10 Precision & Recall**  
- **Query-wise Analysis Table**

---

## 🧩 Notes
- Uses publicly available search result APIs.  
- For large result sets, analysis can be batched.  
- The project focuses on comparing **ranking similarity**, not content relevance.
