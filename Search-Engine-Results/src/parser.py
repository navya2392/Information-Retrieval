"""
Yahoo Search Results Parser

This module extracts organic search results from Yahoo HTML files.
It handles both mobile (p1) and desktop (p2/p3) layouts, decodes Yahoo redirect URLs,
and extracts the top 10 organic URLs per query across multiple pages.
"""

import re
import urllib.parse
from bs4 import BeautifulSoup
import os
import json


def normalize_url(url):
    """
    Normalize URL to treat similar URLs as duplicates.
    
    Normalizations:
    - Convert http:// to https://
    - Remove www. prefix  
    - Remove trailing slash
    - Convert to lowercase
    - Remove common tracking parameters
    
    Args:
        url (str): Original URL
        
    Returns:
        str: Normalized URL for duplicate detection
    """
    if not url or not isinstance(url, str):
        return url
        
    try:
        # Parse the URL
        parsed = urllib.parse.urlparse(url.lower().strip())
        
        # Normalize scheme (always use https)
        scheme = 'https'
        
        # Normalize netloc (remove www prefix)
        netloc = parsed.netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
            
        # Normalize path (remove trailing slash, except for root)
        path = parsed.path
        if path.endswith('/') and path != '/':
            path = path[:-1]
            
        # Remove common tracking parameters
        if parsed.query:
            query_params = urllib.parse.parse_qs(parsed.query)
            # Keep only meaningful parameters, filter out tracking
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'ref', 'source', 'campaign', 'medium',
                '_ga', '_gid', 'mc_cid', 'mc_eid', 'affiliate_id'
            }
            filtered_params = {k: v for k, v in query_params.items() 
                             if k.lower() not in tracking_params}
            query = urllib.parse.urlencode(filtered_params, doseq=True) if filtered_params else ''
        else:
            query = parsed.query
            
        # Rebuild normalized URL
        normalized = urllib.parse.urlunparse((
            scheme, netloc, path, parsed.params, query, ''  # Remove fragment
        ))
        
        return normalized
        
    except Exception as e:
        # If normalization fails, return original URL
        return url


def decode_yahoo_url(yahoo_redirect_url):
    """
    Decode Yahoo redirect URL to get the actual destination URL.
    
    Yahoo uses redirect URLs like:
    https://r.search.yahoo.com/_ylt=...;_ylu=...;_ylc=...;_ylv=3?actrs=1&...&RU=https%3a%2f%2fwww.example.com%2f&RK=...
    
    Args:
        yahoo_redirect_url (str): Yahoo redirect URL
        
    Returns:
        str: Decoded actual URL, or original URL if decoding fails
    """
    try:
        if 'r.search.yahoo.com' in yahoo_redirect_url:
            # Look for RU= parameter which contains the actual URL
            # Yahoo uses patterns like: /RU=encoded_url/RK=... or &RU=encoded_url&... or ?RU=encoded_url&...
            for prefix in ['/RU=', '&RU=', '?RU=']:
                if prefix in yahoo_redirect_url:
                    ru_start = yahoo_redirect_url.find(prefix) + len(prefix)
                    
                    # Find the end delimiter (& for query params, / for path params)
                    ru_end = len(yahoo_redirect_url)
                    for delimiter in ['&', '/']:
                        delim_pos = yahoo_redirect_url.find(delimiter, ru_start)
                        if delim_pos != -1:
                            ru_end = min(ru_end, delim_pos)
                    
                    encoded_url = yahoo_redirect_url[ru_start:ru_end]
                    decoded_url = urllib.parse.unquote(encoded_url)
                    return decoded_url
        
        return yahoo_redirect_url
    except Exception as e:
        print(f"Error decoding Yahoo URL: {e}")
        return yahoo_redirect_url


def is_organic_url(url):
    """
    Check if a URL is an organic search result (not an ad or internal link).
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if URL is organic (external website), False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Must be a valid HTTP/HTTPS URL
    if not (url.lower().startswith('http://') or url.lower().startswith('https://')):
        return False
    
    # Exclude ALL Yahoo domains and subdomains
    url_lower = url.lower()
    exclude_patterns = [
        'yahoo.com',           # All Yahoo domains and subdomains (covers uservoice.com too)
        'yahooapis.com',       # Yahoo API domains  
        'yimg.com',            # Yahoo image domains
        'flickr.com',          # Yahoo-owned
        'tumblr.com',          # Yahoo-owned
        'aol.com',             # Yahoo-owned
        'engadget.com',        # Yahoo-owned
        'techcrunch.com',      # Yahoo-owned
        'uservoice.com',       # Yahoo feedback system
        # Add other common non-organic patterns
        'javascript:',
        'mailto:',
        'tel:',
        'ftp:',
        '#'                    # Fragment-only URLs
    ]
    
    for pattern in exclude_patterns:
        if pattern in url_lower:
            return False
    
    # Must have a proper domain structure
    try:
        parsed = urllib.parse.urlparse(url)
        return bool(parsed.netloc and '.' in parsed.netloc)
    except:
        return False


def parse_html_file(html_file_path):
    """
    Parse Yahoo HTML file using universal redirect-based approach.
    
    This simplified approach works for ALL Yahoo layout types by:
    1. Finding ALL Yahoo redirect links (a[href*="r.search.yahoo.com"])
    2. Decoding the /RU= parameters to get real URLs  
    3. Filtering for organic URLs only
    4. Returning unique results (no layout detection needed)
    
    Args:
        html_file_path (str): Path to Yahoo HTML file
        
    Returns:
        list: List of organic URLs found in the file (in order)
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        organic_urls = []
        seen_normalized = set()  # Track normalized URLs to detect duplicates
        
        # Universal approach: Find ALL Yahoo redirect links (works for all layouts)
        redirect_links = soup.find_all('a', href=re.compile(r'r\.search\.yahoo\.com'))
        
        for link in redirect_links:
            href = link.get('href')
            if href:
                decoded_url = decode_yahoo_url(href)
                if is_organic_url(decoded_url):
                    # Use normalized URL for duplicate detection
                    normalized_url = normalize_url(decoded_url)
                    if normalized_url not in seen_normalized:
                        seen_normalized.add(normalized_url)
                        organic_urls.append(decoded_url)  # Store original URL, not normalized
        
        return organic_urls
        
    except Exception as e:
        print(f"Error parsing {html_file_path}: {e}")
        return []


def extract_top_k_from_multipage(query_number, k=10, base_path='data/raw_html'):
    """
    Extract top k organic URLs from multiple pages of a single query.
    
    Args:
        query_number (int or str): Query number (1-based) 
        k (int): Number of top URLs to return (default: 10)
        base_path (str): Base path to HTML files
        
    Returns:
        list: Top k organic URLs in order of appearance across pages
    """
    all_urls = []
    seen_normalized = set()  # Track normalized URLs for cross-page deduplication
    
    # Convert query_number to string for filename formatting
    query_str = str(query_number).zfill(4)
    
    # Process pages 1, 2, 3 in order
    for page in [1, 2, 3]:
        filename = f"yahoo-{query_str}-p{page}.html"
        file_path = os.path.join(base_path, filename)
        
        if os.path.exists(file_path):
            # parse_html_file already handles per-page deduplication
            page_urls = parse_html_file(file_path)
            
            # Add URLs that aren't duplicates across pages (using normalized comparison)
            for url in page_urls:
                normalized_url = normalize_url(url)
                if normalized_url not in seen_normalized:
                    seen_normalized.add(normalized_url)
                    all_urls.append(url)  # Keep original URL in results
                    
                    # Stop once we have enough URLs
                    if len(all_urls) >= k:
                        return all_urls[:k]
    
    # Return all URLs found (may be less than k)
    return all_urls


def process_all_queries(max_queries=30, k=10, base_path='data/raw_html'):
    """
    Process all queries and generate JSON output compatible with Google format.
    
    Args:
        max_queries (int): Maximum number of queries to process
        k (int): Number of top URLs per query
        base_path (str): Base path to HTML files
        
    Returns:
        dict: Results in Google-compatible JSON format
    """
    results = {}
    
    # Load query texts
    queries_file = 'data/queries/100QueriesSet2.txt'
    queries = []
    if os.path.exists(queries_file):
        with open(queries_file, 'r', encoding='utf-8') as f:
            queries = [line.strip() for line in f if line.strip()]
    
    for query_num in range(1, max_queries + 1):
        # Check if we have files for this query
        has_files = False
        for page in [1, 2, 3]:
            filename = f"yahoo-{query_num:04d}-p{page}.html"
            file_path = os.path.join(base_path, filename)
            if os.path.exists(file_path):
                has_files = True
                break
        
        if has_files:
            # Get query text (queries are 0-indexed, files are 1-indexed)
            query_text = queries[query_num - 1] if (query_num - 1) < len(queries) else f"Query {query_num}"
            top_urls = extract_top_k_from_multipage(query_num, k, base_path)
            
            # Format exactly like Google results: {"query_text": ["url1", "url2", ...]}
            results[query_text] = top_urls
            
            print(f"Processed Query {query_num:04d} ({len(top_urls)} URLs): {query_text[:50]}...")
        else:
            print(f"No files found for Query {query_num}")
    
    return results


def save_results_json(results, output_file='output/Yahoo_Results.json'):
    """
    Save results to JSON file.
    
    Args:
        results (dict): Results dictionary
        output_file (str): Output file path
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    # Process all available queries
    print("Starting Yahoo results processing...")
    results = process_all_queries()
    
    # Save results
    save_results_json(results)
    
    # Print summary
    total_queries = len(results)
    total_urls = sum(len(query_results) for query_results in results.values())
    print(f"\nSummary:")
    print(f"- Processed {total_queries} queries")
    print(f"- Extracted {total_urls} total URLs")
    print(f"- Average URLs per query: {total_urls/total_queries:.1f}")