"""
Yahoo multi-page data collection: fetch 3 pages per query from 100QueriesSet2.txt with anti-detection.

This will create yahoo-0001-p1.html, yahoo-0001-p2.html, yahoo-0001-p3.html for each query.

Run: python src/main.py
"""

from pathlib import Path
from yahoo_client import fetch_query_multipage, polite_sleep_between_queries

# Project paths
ROOT_DIR = Path(__file__).resolve().parents[1]
QUERIES_PATH = ROOT_DIR / "data" / "queries" / "100QueriesSet2.txt"

# How many queries to try (query 85 only) - missing file recovery
TEST_COUNT = 85
START_FROM_QUERY = 85  # Start from query number 85


def read_queries(path: Path, max_n: int) -> list[str]:
    """Return up to max_n queries, stripping only the trailing newline."""
    out: list[str] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            q = line.rstrip("\n")  # do not alter spaces inside the query
            print(q)  # debug: show the exact query string we will use
            if q:
                out.append(q)
            if len(out) >= max_n:
                break
    return out


def main() -> None:
    if not QUERIES_PATH.exists():
        raise FileNotFoundError(f"Queries file not found: {QUERIES_PATH}")

    print(f"Starting Yahoo data collection from query {START_FROM_QUERY} to {TEST_COUNT} from 100QueriesSet2.txt")
    print("=" * 60)
    
    queries = read_queries(QUERIES_PATH, TEST_COUNT)
    print(f"Loaded {len(queries)} queries for processing")
    print(f"Processing queries {START_FROM_QUERY} through {TEST_COUNT}")
    print("=" * 60)

    successful = 0
    failed = 0

    # Start from the specified query number
    for idx in range(START_FROM_QUERY, len(queries) + 1):
        query = queries[idx - 1]  # Convert to 0-based index
        print(f"\n[Q{idx:04d}/{len(queries)}] Processing: '{query}'")
        
        # Fetch 3 pages for this query
        results = fetch_query_multipage(query, idx, num_pages=3)
        
        # Count successful pages
        successful_pages = sum(1 for ok, _, _ in results if ok)
        failed_pages = 3 - successful_pages
        
        if successful_pages > 0:
            print(f"[Q{idx:04d}] ✅ SUCCESS - {successful_pages}/3 pages collected")
            successful += 1
        else:
            print(f"[Q{idx:04d}] ❌ FAILED - 0/3 pages collected")
            failed += 1

        # Sleep BETWEEN queries (per HW FAQ). Skip after last query.
        if idx < len(queries):
            print(f"[Q{idx:04d}] Sleeping before next query...")
            slept = polite_sleep_between_queries(60, 120)  # 1-2 minutes with anti-detection
            print(f"[Q{idx:04d}] Slept {slept}s total before next query")
        else:
            print(f"\n[FINAL] Multi-page collection completed!")
    
    print("=" * 60)
    print(f"SUMMARY: {successful} successful queries, {failed} failed out of {len(queries) - START_FROM_QUERY + 1} processed")
    if successful > 0:
        print(f"HTML files saved as yahoo-XXXX-p1.html, yahoo-XXXX-p2.html, yahoo-XXXX-p3.html")
        print(f"Total files: up to {successful * 3} HTML files collected")
    print("=" * 60)


if __name__ == "__main__":
    main()