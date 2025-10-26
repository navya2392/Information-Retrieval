#!/usr/bin/env python3
"""
Generate Yahoo Search Results JSON

This script processes all collected Yahoo HTML files (queries 1-100) and generates
a JSON output file compatible with the Google Results format for evaluation.

The script:
1. Scans for available HTML files for each query (1-100)
2. Uses parser.py functions to extract top 10 organic URLs per query
3. Combines results from multiple pages (p1, p2, p3) per query
4. Outputs results in the required JSON format: {"query_text": ["url1", "url2", ...]}
5. Saves to output/Yahoo_Results.json
6. Provides detailed logging of URLs extracted per page
7. Flags any pages with 0 URLs extracted

Usage:
    python src/generate_results.py
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path for imports
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

# Import parser functions
from parser import extract_top_k_from_multipage, save_results_json, parse_html_file


def process_all_queries_with_logging(max_queries=100, k=10, base_path='data/raw_html'):
    """
    Process all queries with detailed logging of URLs per page.
    
    Args:
        max_queries (int): Maximum number of queries to process
        k (int): Number of top URLs per query
        base_path (str): Base path to HTML files
        
    Returns:
        tuple: (results dict, page_stats list)
    """
    results = {}
    page_stats = []
    zero_url_pages = []
    
    # Load query texts
    queries_file = 'data/queries/100QueriesSet2.txt'
    queries = []
    if os.path.exists(queries_file):
        with open(queries_file, 'r', encoding='utf-8') as f:
            queries = [line.strip() for line in f if line.strip()]
    
    print("Detailed URL Extraction Log:")
    print("=" * 80)
    
    for query_num in range(1, max_queries + 1):
        # Check if we have files for this query
        available_pages = []
        for page in [1, 2, 3]:
            filename = f"yahoo-{query_num:04d}-p{page}.html"
            file_path = os.path.join(base_path, filename)
            if os.path.exists(file_path):
                available_pages.append(page)
        
        if not available_pages:
            print(f"❌ Query {query_num:04d}: No HTML files found")
            continue
            
        # Get query text
        query_text = queries[query_num - 1] if (query_num - 1) < len(queries) else f"Query {query_num}"
        
        print(f"\n📋 Query {query_num:04d}: {query_text[:60]}{'...' if len(query_text) > 60 else ''}")
        
        # Process each page individually to get detailed stats
        all_urls = []
        page_url_counts = []
        
        for page in [1, 2, 3]:
            filename = f"yahoo-{query_num:04d}-p{page}.html"
            file_path = os.path.join(base_path, filename)
            
            if os.path.exists(file_path):
                try:
                    # Parse individual page
                    page_urls = parse_html_file(file_path)
                    url_count = len(page_urls)
                    page_url_counts.append(url_count)
                    
                    # Add to combined list
                    all_urls.extend(page_urls)
                    
                    # Log page results
                    status = "✅" if url_count > 0 else "⚠️"
                    print(f"   {status} Page {page}: {url_count:2d} URLs extracted")
                    
                    # Track zero-URL pages
                    if url_count == 0:
                        zero_url_pages.append({
                            'query': query_num,
                            'page': page,
                            'filename': filename,
                            'query_text': query_text
                        })
                        
                    # Store page stats
                    page_stats.append({
                        'query': query_num,
                        'page': page,
                        'url_count': url_count,
                        'filename': filename
                    })
                    
                except Exception as e:
                    print(f"   ❌ Page {page}: Error parsing - {str(e)}")
                    page_url_counts.append(0)
                    zero_url_pages.append({
                        'query': query_num,
                        'page': page,
                        'filename': filename,
                        'query_text': query_text,
                        'error': str(e)
                    })
            else:
                print(f"   ❌ Page {page}: File missing")
                page_url_counts.append(0)
        
        # Remove duplicates and get top k
        seen = set()
        unique_urls = []
        for url in all_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        top_urls = unique_urls[:k]
        
        # Summary for this query
        total_raw = sum(page_url_counts)
        total_unique = len(unique_urls)
        total_final = len(top_urls)
        
        print(f"   📊 Summary: {total_raw} total → {total_unique} unique → {total_final} final")
        
        # Store results
        results[query_text] = top_urls
    
    return results, page_stats, zero_url_pages


def print_zero_url_report(zero_url_pages):
    """Print detailed report of pages with zero URLs."""
    if not zero_url_pages:
        print("\n🎉 SUCCESS: All pages extracted at least 1 URL!")
        return
        
    print(f"\n⚠️  WARNING: {len(zero_url_pages)} pages extracted 0 URLs:")
    print("=" * 80)
    
    for page_info in zero_url_pages:
        error_msg = f" (Error: {page_info.get('error', 'N/A')})" if 'error' in page_info else ""
        print(f"❌ Query {page_info['query']:04d} Page {page_info['page']}: {page_info['filename']}{error_msg}")
        print(f"   Query: {page_info['query_text'][:70]}{'...' if len(page_info['query_text']) > 70 else ''}")
        print()


def print_summary_stats(page_stats, results):
    """Print overall summary statistics."""
    if not page_stats:
        return
        
    # Calculate stats
    total_pages = len(page_stats)
    pages_with_urls = sum(1 for stat in page_stats if stat['url_count'] > 0)
    pages_with_zero = total_pages - pages_with_urls
    
    total_urls_extracted = sum(stat['url_count'] for stat in page_stats)
    avg_urls_per_page = total_urls_extracted / total_pages if total_pages > 0 else 0
    
    total_queries = len(results)
    total_final_urls = sum(len(urls) for urls in results.values())
    avg_final_per_query = total_final_urls / total_queries if total_queries > 0 else 0
    
    print("\n" + "=" * 80)
    print("📈 EXTRACTION STATISTICS")
    print("=" * 80)
    print(f"Total pages processed: {total_pages}")
    print(f"Pages with URLs: {pages_with_urls} ({pages_with_urls/total_pages*100:.1f}%)")
    print(f"Pages with 0 URLs: {pages_with_zero} ({pages_with_zero/total_pages*100:.1f}%)")
    print(f"Total raw URLs extracted: {total_urls_extracted:,}")
    print(f"Average URLs per page: {avg_urls_per_page:.1f}")
    print(f"Final unique URLs in JSON: {total_final_urls:,}")
    print(f"Average final URLs per query: {avg_final_per_query:.1f}")
    print(f"Queries successfully processed: {total_queries}/100")


def main():
    """
    Main function to generate Yahoo results JSON for all 100 queries.
    """
    print("=" * 60)
    print("Yahoo Search Results JSON Generation")
    print("=" * 60)
    print()
    
    # Check if output directory exists
    output_dir = Path("output")
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created output directory: {output_dir}")
    
    # Check if queries file exists
    queries_file = Path("data/queries/100QueriesSet2.txt")
    if not queries_file.exists():
        print(f"❌ ERROR: Query file not found: {queries_file}")
        return
    
    # Check if HTML files directory exists
    html_dir = Path("data/raw_html")
    if not html_dir.exists():
        print(f"❌ ERROR: HTML files directory not found: {html_dir}")
        return
    
    # Count available HTML files
    html_files = list(html_dir.glob("yahoo-*.html"))
    print(f"Found {len(html_files)} Yahoo HTML files in {html_dir}")
    print()
    
    # Process all queries (1-100) with detailed logging
    print("Processing all queries (1-100) with detailed page-by-page logging...")
    print("This may take a few minutes...")
    print()
    
    try:
        # Use our detailed processing function
        results, page_stats, zero_url_pages = process_all_queries_with_logging(
            max_queries=100, k=10, base_path='data/raw_html'
        )
        
        if not results:
            print("❌ No results generated. Check if HTML files are available.")
            return
        
        # Print zero URL report
        print_zero_url_report(zero_url_pages)
        
        # Print summary statistics
        print_summary_stats(page_stats, results)
        
        # Save results to JSON file
        output_file = 'output/yahoo_results2.json'
        save_results_json(results, output_file)
        
        # Print final summary
        print()
        print("=" * 60)
        print("GENERATION COMPLETE")
        print("=" * 60)
        
        total_queries = len(results)
        total_urls = sum(len(query_results) for query_results in results.values())
        avg_urls = total_urls / total_queries if total_queries > 0 else 0
        
        print(f"✅ Successfully processed {total_queries} queries")
        print(f"✅ Generated final JSON with {total_urls:,} URLs")
        print(f"✅ Average URLs per query: {avg_urls:.1f}")
        print(f"✅ Results saved to: {output_file}")
        
        # Show sample of results
        print()
        print("Sample results:")
        for i, (query, urls) in enumerate(results.items()):
            if i >= 3:  # Show first 3 queries
                break
            print(f"  Query: {query[:50]}{'...' if len(query) > 50 else ''}")
            print(f"  URLs ({len(urls)}): {urls[0] if urls else 'No URLs'}")
            print()
        
        print(f"Total queries in final JSON: {total_queries}")
        
        # Final quality check
        zero_count = len(zero_url_pages)
        if zero_count == 0:
            print("\n🎉 QUALITY CHECK PASSED: All pages extracted URLs successfully!")
        else:
            print(f"\n⚠️  QUALITY WARNING: {zero_count} pages extracted 0 URLs (see report above)")
        
    except Exception as e:
        print(f"❌ ERROR during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()