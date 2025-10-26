"""
Yahoo client module with anti-detection measures.

Purpose
- Fetch one Yahoo Search results page (SERP) for a query and save the raw HTML.
- Each query -> one HTML file named yahoo-0001.html, yahoo-0002.html, ... in data/raw_html/
- Parsing of organic results happens in `yahoo_parser.py` (not here).

Notes:
- URL: https://search.yahoo.com/search?p=<query>&n=30 (Assignment FAQ suggests n=30)
- Anti-detection: rotating User-Agent, proxy support, slower timing
- Delay: random 2-5 minutes **between queries** (call from main loop)
- No query text modifications from original query file
"""

from pathlib import Path
from urllib.parse import urlencode
import time
import random
from typing import Tuple, Optional, Dict, List
import requests

# Project paths
ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_HTML_DIR = ROOT_DIR / "data" / "raw_html"

# Yahoo endpoint
YAHOO_BASE_URL = "https://search.yahoo.com/search"

# Brand new user agent pool with different versions and platforms for maximum stealth
USER_AGENTS = [
    # Ultra-fresh Chrome versions (December 2024/January 2025)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    
    # Fresh Firefox builds (latest stable and beta)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    
    # Latest Safari versions on different macOS builds
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    
    # Fresh Edge versions
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    
    # Chrome on different Linux distributions
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    
    # Opera browsers (different versions)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/109.0.0.0",
    
    
    

]

# Free proxy list (you might need to find active ones)
PROXY_LIST = [
    # Add working proxies here in format "http://ip:port" or None for no proxy
    None,  # No proxy (direct connection)
    # "http://proxy1.com:8080",
    # "http://proxy2.com:3128",
]

def get_random_user_agent() -> str:
    """Get a random user agent from the pool."""
    return random.choice(USER_AGENTS)

def get_random_proxy() -> Optional[str]:
    """Get a random proxy from the list (can return None for direct connection)."""
    return random.choice(PROXY_LIST)

def create_headers() -> Dict[str, str]:
    """Create headers with random user agent and realistic browser headers with enhanced variety."""
    import random
    
    # Expanded accept-language options for better geo-diversity
    accept_languages = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.8,es;q=0.7,fr;q=0.6",
        "en-CA,en;q=0.9,fr;q=0.8",
        "en-AU,en;q=0.9,en-GB;q=0.8",
        "en-US,en;q=0.7,de;q=0.3",
        "en-GB,en;q=0.8,fr;q=0.6,es;q=0.4",
    ]
    
    # Updated accept values for modern browsers
    accept_values = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    ]
    
    # Modern encoding options
    encodings = [
        "gzip, deflate, br",
        "gzip, deflate, br, zstd",
        "gzip, deflate",
        "br, gzip, deflate",
    ]
    
    # Cache control variations
    cache_controls = ["no-cache", "max-age=0", "no-store", "private"]
    
    # Base headers that all browsers have
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": random.choice(accept_values),
        "Accept-Language": random.choice(accept_languages),
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    # Add optional headers with higher probability for better realism
    if random.random() < 0.7:  # 70% chance
        headers["Cache-Control"] = random.choice(cache_controls)
    
    if random.random() < 0.6:  # 60% chance
        headers["DNT"] = "1"  # Do Not Track
    
    if random.random() < 0.4:  # 40% chance
        headers["Sec-GPC"] = "1"  # Global Privacy Control
        
    # Modern Chrome/Edge headers (add more frequently)
    if random.random() < 0.8:  # 80% chance for modern browsers
        headers.update({
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": random.choice(["none", "same-origin", "cross-site"]),
            "Sec-Fetch-User": "?1",
        })
    
    # Add some browser-specific headers occasionally
    if random.random() < 0.3:  # 30% chance
        headers["Pragma"] = "no-cache"
    
    if random.random() < 0.2:  # 20% chance
        headers["Priority"] = random.choice(["u=0, i", "u=1", "u=2"])
    
    return headers

def save_html(qid: int, html: str, page: int = 1) -> Path:
    """Save the fetched HTML as yahoo-0001-p1.html, yahoo-0001-p2.html, etc. under data/raw_html/."""
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_HTML_DIR / f"yahoo-{qid:04d}-p{page}.html"  # Always use -pX format for consistency
    path.write_text(html, encoding="utf-8", errors="ignore")
    return path

def polite_sleep_between_queries(min_seconds: int = 120, max_seconds: int = 300) -> int:
    """Sleep a random delay between queries per HW FAQ (prevents blocking). Default 2-5 minutes."""
    # Add initial random delay (10-30 seconds)
    initial_delay = random.randint(10, 30)
    print(f"Initial random delay: {initial_delay}s")
    time.sleep(initial_delay)
    
    # Main delay (increased for better anti-detection)
    seconds = random.randint(min_seconds, max_seconds)
    print(f"Main delay: {seconds}s ({seconds/60:.1f} minutes)")
    time.sleep(seconds)
    return seconds + initial_delay

def fetch_query_html(query: str, qid: int, page: int = 1, *, timeout: int = 30, max_retries: int = 2) -> Tuple[bool, str, Optional[int]]:
    """
    Fetch a single Yahoo SERP and save the raw HTML with anti-detection measures.
    
    Args:
        query: Search query string
        qid: Query ID number  
        page: Page number (1, 2, 3, ...)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts for failed requests
        
    Returns (ok, path_or_error, status_code):
      ok=True  -> (True, "<path to yahoo-0001.html>", 200)
      ok=False -> (False, "HTTP <code>", <code>) or (False, "RequestException: ...", None)
    """
    
    for attempt in range(max_retries + 1):
        # Yahoo search parameters with pagination
        # Yahoo uses 'b' parameter for pagination: page 1 = b=0, page 2 = b=10, page 3 = b=20, etc.
        start_index = (page - 1) * 10  # Yahoo shows 10 results per page by default
        params = {"p": query, "n": "30", "b": str(start_index)}
        
        # Get random headers and proxy for each attempt
        headers = create_headers()
        proxy = get_random_proxy()
        proxies = {"http": proxy, "https": proxy} if proxy else None
        
        attempt_suffix = f" (attempt {attempt + 1}/{max_retries + 1})" if attempt > 0 else ""
        page_info = f" page {page}" if page > 1 else ""
        print(f"Query {qid:04d}{page_info}{attempt_suffix}: Using User-Agent: {headers['User-Agent'][:50]}...")
        if proxy:
            print(f"Query {qid:04d}{page_info}{attempt_suffix}: Using proxy: {proxy}")
        else:
            print(f"Query {qid:04d}{page_info}{attempt_suffix}: Direct connection (no proxy)")

        try:
            # Add random delay before request (longer for retries)
            pre_request_delay = random.randint(5, 15) if attempt > 0 else random.randint(1, 5)
            print(f"Query {qid:04d}{page_info}{attempt_suffix}: Waiting {pre_request_delay}s before request...")
            time.sleep(pre_request_delay)
            
            resp = requests.get(
                YAHOO_BASE_URL, 
                headers=headers, 
                params=params, 
                proxies=proxies,
                timeout=timeout,
                allow_redirects=True
            )
            
            if resp.status_code == 200:
                path = save_html(qid, resp.text, page)
                print(f"Query {qid:04d}{page_info}{attempt_suffix}: ✅ SUCCESS - saved HTML ({len(resp.text)} chars)")
                return True, str(path), 200
            elif resp.status_code in [429, 500, 502, 503, 504] and attempt < max_retries:
                # Retry on rate limiting or server errors
                retry_delay = random.randint(30, 60) * (attempt + 1)  # Exponential backoff
                print(f"Query {qid:04d}{page_info}{attempt_suffix}: HTTP {resp.status_code} - retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            else:
                print(f"Query {qid:04d}{page_info}{attempt_suffix}: ❌ HTTP {resp.status_code}")
                return False, f"HTTP {resp.status_code}", resp.status_code
                
        except requests.RequestException as e:
            if attempt < max_retries:
                retry_delay = random.randint(20, 40) * (attempt + 1)
                print(f"Query {qid:04d}{page_info}{attempt_suffix}: Request failed: {e} - retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            else:
                print(f"Query {qid:04d}{page_info}{attempt_suffix}: ❌ Request failed: {e}")
                return False, f"RequestException: {e}", None
    
    # If we get here, all retries failed
    return False, "All retry attempts failed", None


def fetch_query_multipage(query: str, qid: int, num_pages: int = 3, *, timeout: int = 30) -> List[Tuple[bool, str, Optional[int]]]:
    """
    Fetch multiple pages for a single query with anti-detection measures.
    
    Args:
        query: Search query string
        qid: Query ID number
        num_pages: Number of pages to collect (default 3)
        timeout: Request timeout in seconds
        
    Returns:
        List of (ok, path_or_error, status_code) tuples, one per page
    """
    results = []
    
    print(f"\n[Q{qid:04d}/MultiPage] Collecting {num_pages} pages for: '{query[:60]}{'...' if len(query) > 60 else ''}'")
    
    for page in range(1, num_pages + 1):
        print(f"[Page {page}/{num_pages}] Fetching page {page}...")
        
        # Fetch this page
        ok, path_or_error, status_code = fetch_query_html(query, qid, page, timeout=timeout)
        results.append((ok, path_or_error, status_code))
        
        if ok:
            print(f"[Page {page}/{num_pages}] ✅ SUCCESS - status={status_code} - saved={path_or_error}")
        else:
            print(f"[Page {page}/{num_pages}] ❌ FAILED - {path_or_error}")
            
        # Add delay between pages (shorter than between queries)
        if page < num_pages:  # Don't sleep after the last page
            page_delay = random.randint(10, 30)  # 10-30 seconds between pages
            print(f"[Page {page}/{num_pages}] Waiting {page_delay}s before next page...")
            time.sleep(page_delay)
    
    successful_pages = sum(1 for ok, _, _ in results if ok)
    print(f"[Q{qid:04d}/MultiPage] Completed: {successful_pages}/{num_pages} pages successful")
    
    return results

