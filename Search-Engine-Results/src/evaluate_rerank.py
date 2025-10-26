#!/usr/bin/env python3
"""
CSCI 572 HW1 - Search Engine Comparison with RE-RANKING METHOD
Compares Yahoo and Google search results using Spearman correlation with re-ranking of overlaps only.

Re-ranking method:
- Only overlapping URLs are considered
- Overlapping URLs are re-ranked from 1 to n based on their relative positions
- Example: If overlaps are at positions [1,5,6,7] and [1,9,2,6], they become:
  Google: [1,2,3,4] (based on sorted order of Google positions)  
  Yahoo: [1,4,2,3] (based on sorted order of Yahoo positions)
"""

import csv
import json
import logging
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    Normalize URL for comparison according to assignment FAQ.
    
    Treats as identical:
    - http vs https
    - www vs non-www
    - trailing slash vs no trailing slash
    - CASE SENSITIVE (URLs are case-sensitive)
    
    Args:
        url: Original URL string
        
    Returns:
        Normalized URL string for comparison
    """
    if not url or not isinstance(url, str):
        return ""
    
    # Strip whitespace but preserve case
    url = url.strip()
    
    # Parse URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return url
    
    # Remove scheme (http/https treated as same)
    domain = parsed.netloc
    path = parsed.path
    
    # Remove www. prefix (case insensitive for domain only)
    if domain.lower().startswith('www.'):
        domain = domain[4:]
    
    # Remove trailing slash
    if path.endswith('/') and len(path) > 1:
        path = path[:-1]
    
    # Reconstruct normalized URL without scheme
    normalized = domain + path
    
    # Add query and fragment if present
    if parsed.query:
        normalized += '?' + parsed.query
    if parsed.fragment:
        normalized += '#' + parsed.fragment
        
    return normalized


def find_url_matches(google_urls: List[str], yahoo_urls: List[str]) -> List[Tuple[int, int]]:
    """
    Find matching URLs between Google and Yahoo results.
    
    Args:
        google_urls: List of Google result URLs (ranked 1 to N)
        yahoo_urls: List of Yahoo result URLs (ranked 1 to N)
        
    Returns:
        List of (google_rank, yahoo_rank) tuples for matches (1-indexed)
    """
    matches = []
    
    # Normalize all URLs for comparison
    google_normalized = [normalize_url(url) for url in google_urls]
    yahoo_normalized = [normalize_url(url) for url in yahoo_urls]
    
    # Find matches
    for g_idx, g_norm in enumerate(google_normalized):
        if g_norm:  # Skip empty/invalid URLs
            for y_idx, y_norm in enumerate(yahoo_normalized):
                if y_norm and g_norm == y_norm:
                    # Convert to 1-indexed ranks
                    matches.append((g_idx + 1, y_idx + 1))
                    break  # Each Google URL matches at most one Yahoo URL
    
    return matches


def calculate_percent_overlap(google_urls: List[str], yahoo_urls: List[str]) -> float:
    """
    Calculate percent overlap between two result sets.
    
    Args:
        google_urls: List of Google result URLs
        yahoo_urls: List of Yahoo result URLs
        
    Returns:
        Percent overlap (0-100)
    """
    matches = find_url_matches(google_urls, yahoo_urls)
    
    if not google_urls:
        return 0.0
        
    # Overlap percentage based on Google results (baseline)
    overlap_percent = (len(matches) / len(google_urls)) * 100
    return round(overlap_percent, 1)


def calculate_spearman_correlation_rerank(google_urls: List[str], yahoo_urls: List[str]) -> Optional[float]:
    """
    Calculate Spearman's rank correlation coefficient using RE-RANKING METHOD.
    
    Method (as shown in instructor's example):
    - 0 matches: ρ = 0
    - 1 match: ρ = 1 if same rank, ρ = 0 if different rank
    - 2+ matches: Re-rank only the overlapping URLs from 1 to n based on relative positions
    - Uses formula: ρ = 1 - (6 * Σd²) / (n * (n² - 1))
    
    Example: Overlaps at Google [1,5,6,7] and Yahoo [1,9,2,6] become:
    - Google re-ranks: [1,2,3,4] (1st, 2nd, 3rd, 4th in Google order)
    - Yahoo re-ranks: [1,4,2,3] (1st, 4th, 2nd, 3rd when sorted by Yahoo positions)
    
    Args:
        google_urls: List of Google result URLs
        yahoo_urls: List of Yahoo result URLs
        
    Returns:
        Spearman correlation coefficient (-1 to +1), or 0 if no matches
    """
    matches = find_url_matches(google_urls, yahoo_urls)
    
    if len(matches) == 0:
        # No overlap case
        return 0.0
    
    if len(matches) == 1:
        # Single match case: ρ = 1 if same rank, ρ = 0 if different rank
        google_rank, yahoo_rank = matches[0]
        return 1.0 if google_rank == yahoo_rank else 0.0
    
    # Multiple matches case: RE-RANK overlapping URLs from 1 to n
    n = len(matches)
    
    # Sort matches by Google rank to establish re-ranking order
    matches_sorted_by_google = sorted(matches, key=lambda x: x[0])
    
    # Create Google re-ranks: 1, 2, 3, ... (based on Google order)
    google_reranks = list(range(1, n + 1))
    
    # Create Yahoo re-ranks based on sorted Yahoo positions
    yahoo_ranks_in_google_order = [match[1] for match in matches_sorted_by_google]
    yahoo_ranks_sorted = sorted(yahoo_ranks_in_google_order)
    
    # Create mapping from original Yahoo rank to its re-ranked position
    yahoo_rank_to_rerank = {rank: i + 1 for i, rank in enumerate(yahoo_ranks_sorted)}
    yahoo_reranks = [yahoo_rank_to_rerank[rank] for rank in yahoo_ranks_in_google_order]
    
    # Calculate rank differences for re-ranked positions
    sum_d_squared = 0
    for g_rerank, y_rerank in zip(google_reranks, yahoo_reranks):
        d = g_rerank - y_rerank
        sum_d_squared += d * d
    
    # Apply Spearman formula: ρ = 1 - (6 * Σd²) / (n * (n² - 1))
    denominator = n * (n * n - 1)
    
    if denominator == 0:
        return 0.0
        
    rho = 1.0 - (6.0 * sum_d_squared) / denominator
    
    # Round to reasonable precision
    return round(rho, 3)


def load_google_results(filepath: Path) -> Dict[str, List[str]]:
    """Load Google reference results from JSON file."""
    try:
        with filepath.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise FileNotFoundError(f"Could not load Google results from {filepath}: {e}")


def load_yahoo_results(filepath: Path) -> Dict[str, List[str]]:
    """Load Yahoo results from JSON file."""
    try:
        with filepath.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise FileNotFoundError(f"Could not load Yahoo results from {filepath}: {e}")


def compare_search_results_rerank(google_results: Dict[str, List[str]], 
                                 yahoo_results: Dict[str, List[str]]) -> List[Dict]:
    """
    Compare Google and Yahoo results for all queries using re-ranking method.
    
    Returns:
        List of comparison results, one dict per query in original order
    """
    comparisons = []
    
    # Find common queries but preserve original Google order
    google_queries = list(google_results.keys())
    common_queries = [q for q in google_queries if q in yahoo_results]
    
    if not common_queries:
        raise ValueError("No common queries found between Google and Yahoo results")
    
    print(f"Analyzing {len(common_queries)} common queries...")
    
    for i, query in enumerate(common_queries, 1):
        print(f"[{i:2d}/{len(common_queries)}] Analyzing: {query[:50]}...")
        
        google_urls = google_results[query]
        yahoo_urls = yahoo_results[query]
        
        # Calculate metrics using re-ranking method
        overlap_percent = calculate_percent_overlap(google_urls, yahoo_urls)
        spearman_coeff = calculate_spearman_correlation_rerank(google_urls, yahoo_urls)
        
        # Count overlapping results
        matches = find_url_matches(google_urls, yahoo_urls)
        num_overlapping = len(matches)
        
        comparison = {
            'query': query,
            'num_overlapping': num_overlapping,
            'percent_overlap': overlap_percent,
            'spearman_coefficient': spearman_coeff,
            'google_count': len(google_urls),
            'yahoo_count': len(yahoo_urls)
        }
        
        comparisons.append(comparison)
    
    return comparisons


def generate_csv_report_rerank(comparisons: List[Dict], output_path: Path) -> None:
    """Generate CSV file with comparison results using re-ranking method."""
    
    # Calculate averages
    valid_overlaps = [c['num_overlapping'] for c in comparisons]
    valid_percents = [c['percent_overlap'] for c in comparisons]
    valid_spearmans = [c['spearman_coefficient'] for c in comparisons]
    
    avg_overlapping = sum(valid_overlaps) / len(valid_overlaps) if valid_overlaps else 0
    avg_percent = sum(valid_percents) / len(valid_percents) if valid_percents else 0
    avg_spearman = sum(valid_spearmans) / len(valid_spearmans) if valid_spearmans else 0
    
    with output_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header row
        writer.writerow(['Queries', 'Number of Overlapping Results', 'Percent Overlap', 'Spearman Coefficient'])
        
        # Data rows
        for i, comp in enumerate(comparisons, 1):
            spearman_val = comp['spearman_coefficient']
            spearman_str = f"{spearman_val:.2f}"
            
            writer.writerow([
                f"Query {i}",
                comp['num_overlapping'],
                f"{comp['percent_overlap']:.1f}",
                spearman_str
            ])
        
        # Averages row
        writer.writerow([
            "Averages",
            f"{avg_overlapping:.1f}",
            f"{avg_percent:.1f}",
            f"{avg_spearman:.2f}"
        ])
    
    print(f"✅ CSV report saved to: {output_path}")


def generate_text_report_rerank(comparisons: List[Dict], output_path: Path) -> None:
    """Generate text analysis report using re-ranking method."""
    
    # Calculate statistics
    valid_overlaps = [c['num_overlapping'] for c in comparisons]
    valid_percents = [c['percent_overlap'] for c in comparisons]
    valid_spearmans = [c['spearman_coefficient'] for c in comparisons]
    
    avg_overlapping = sum(valid_overlaps) / len(valid_overlaps) if valid_overlaps else 0
    avg_percent = sum(valid_percents) / len(valid_percents) if valid_percents else 0
    avg_spearman = sum(valid_spearmans) / len(valid_spearmans) if valid_spearmans else 0
    
    # Overlap distribution
    high_overlap = sum(1 for p in valid_percents if p >= 50)
    medium_overlap = sum(1 for p in valid_percents if 20 <= p < 50)
    low_overlap = sum(1 for p in valid_percents if p < 20)
    
    # Spearman statistics
    spearman_available = len(valid_spearmans)
    spearman_positive = sum(1 for s in valid_spearmans if s > 0)
    spearman_negative = sum(1 for s in valid_spearmans if s < 0)
    spearman_zero = sum(1 for s in valid_spearmans if s == 0)
    
    with output_path.open('w', encoding='utf-8') as f:
        f.write("CSCI 572 Homework 1 - Yahoo vs Google Search Engine Comparison (RE-RANKING METHOD)\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("METHODOLOGY: RE-RANKING OF OVERLAPPING RESULTS ONLY\n")
        f.write("-" * 50 + "\n")
        f.write("This analysis uses the re-ranking method where only overlapping URLs are considered.\n")
        f.write("Overlapping URLs are re-ranked from 1 to n based on their relative positions.\n")
        f.write("Example: Overlaps at [1,5,6,7] and [1,9,2,6] become [1,2,3,4] and [1,4,2,3]\n\n")
        
        f.write("OVERALL PERFORMANCE ANALYSIS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total queries analyzed: {len(comparisons)}\n")
        f.write(f"Average overlapping results: {avg_overlapping:.1f}\n")
        f.write(f"Average percent overlap: {avg_percent:.1f}%\n")
        f.write(f"Average Spearman coefficient: {avg_spearman:.3f}\n")
        f.write("\n")
        
        f.write("OVERLAP DISTRIBUTION\n")
        f.write("-" * 20 + "\n")
        f.write(f"High overlap (≥50%): {high_overlap} queries ({high_overlap/len(comparisons)*100:.1f}%)\n")
        f.write(f"Medium overlap (20-49%): {medium_overlap} queries ({medium_overlap/len(comparisons)*100:.1f}%)\n")
        f.write(f"Low overlap (<20%): {low_overlap} queries ({low_overlap/len(comparisons)*100:.1f}%)\n")
        f.write("\n")
        
        f.write("SPEARMAN CORRELATION ANALYSIS (RE-RANKING METHOD)\n")
        f.write("-" * 45 + "\n")
        f.write(f"Queries with computable correlation: {spearman_available}/{len(comparisons)}\n")
        if spearman_available > 0:
            f.write(f"Positive correlations: {spearman_positive} ({spearman_positive/spearman_available*100:.1f}%)\n")
            f.write(f"Negative correlations: {spearman_negative} ({spearman_negative/spearman_available*100:.1f}%)\n")
            f.write(f"Zero correlations: {spearman_zero} ({spearman_zero/spearman_available*100:.1f}%)\n")
        f.write("\n")
        
        f.write("METHOD COMPARISON NOTE\n")
        f.write("-" * 20 + "\n")
        f.write("Re-ranking method correlations are bounded within [-1, +1] range,\n")
        f.write("unlike global ranking method which can exceed these bounds.\n")
        f.write("This method focuses purely on relative ordering of overlapping results.\n")
    
    print(f"✅ Text report saved to: {output_path}")


def main():
    """Main function to run the re-ranking evaluation."""
    # File paths
    ROOT_DIR = Path(__file__).parent.parent
    GOOGLE_PATH = ROOT_DIR / "data" / "reference" / "Google_Result2.json"
    YAHOO_PATH = ROOT_DIR / "output" / "yahoo_results2.json"
    
    # Output paths (different from global ranking method)
    CSV_OUTPUT = ROOT_DIR / "hw1_rerank.csv"
    TXT_OUTPUT = ROOT_DIR / "hw1_rerank.txt"
    
    print("🔍 CSCI 572 HW1 - Search Engine Comparison Tool (RE-RANKING METHOD)")
    print("=" * 70)
    
    try:
        # Load data
        print("📁 Loading Google reference results...")
        google_results = load_google_results(GOOGLE_PATH)
        print(f"   Loaded {len(google_results)} Google queries")
        
        print("📁 Loading Yahoo results...")
        yahoo_results = load_yahoo_results(YAHOO_PATH)
        print(f"   Loaded {len(yahoo_results)} Yahoo queries")
        
        # Perform comparison using re-ranking method
        print("\n🔬 Performing comparison analysis with RE-RANKING method...")
        comparisons = compare_search_results_rerank(google_results, yahoo_results)
        
        # Generate reports
        print(f"\n📊 Generating reports...")
        generate_csv_report_rerank(comparisons, CSV_OUTPUT)
        generate_text_report_rerank(comparisons, TXT_OUTPUT)
        
        # Summary
        valid_spearmans = [c['spearman_coefficient'] for c in comparisons]
        avg_percent = sum(c['percent_overlap'] for c in comparisons) / len(comparisons)
        avg_spearman = sum(valid_spearmans) / len(valid_spearmans) if valid_spearmans else 0
        
        print(f"\n✅ Re-ranking Analysis Complete!")
        print(f"   Queries analyzed: {len(comparisons)}")
        print(f"   Average overlap: {avg_percent:.1f}%")
        print(f"   Average correlation: {avg_spearman:.3f}")
        print(f"   Reports saved as hw1_rerank.csv and hw1_rerank.txt")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()