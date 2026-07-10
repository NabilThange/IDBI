"""
HTML Sitemap URL Seeder

IDBI Bank doesn't have a machine-readable sitemap.xml, but sitemap.aspx is a hand-curated
HTML page with comprehensive product/service links. This script fetches that page, extracts
all internal hrefs matching our allowed domain, and returns a deduplicated seed URL list.

This is more reliable than BFS discovery at shallow depth because:
1. It's curated - only real product/service pages, no auto-generated cruft
2. It's comprehensive - covers all major sections the bank wants indexed
3. It's fast - one HTTP request vs dozens during BFS discovery

Usage:
    python -m app.crawler.html_sitemap_seeder
"""

import asyncio
from typing import List, Set
from urllib.parse import urljoin, urlparse
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


# Configuration (import from crawl4ai_client to maintain single source of truth)
try:
    from .crawl4ai_client import BASE_URL, DOMAIN_VARIANTS, BLOCKED_SUBDOMAINS
except ImportError:
    from crawl4ai_client import BASE_URL, DOMAIN_VARIANTS, BLOCKED_SUBDOMAINS


SITEMAP_URL = f"{BASE_URL}/sitemap.aspx"


def is_valid_url(url: str, allowed_domains: List[str], blocked_domains: List[str]) -> bool:
    """
    Check if URL should be included in seed list.
    
    Args:
        url: URL to check
        allowed_domains: List of allowed domains
        blocked_domains: List of blocked subdomains
        
    Returns:
        True if URL is valid for crawling
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        
        # Must be HTTP/HTTPS
        if parsed.scheme not in ("http", "https"):
            return False
        
        # Check blocked domains first (exact match or subdomain)
        for blocked in blocked_domains:
            if hostname == blocked or hostname.endswith(f".{blocked}"):
                return False
        
        # Check allowed domains (exact match or subdomain)
        for allowed in allowed_domains:
            if hostname == allowed or hostname.endswith(f".{allowed}"):
                return True
        
        return False
    
    except Exception:
        return False


async def discover_urls_from_html_sitemap(verbose: bool = True) -> List[str]:
    """
    Discover URLs by fetching and parsing the HTML sitemap page.
    
    Args:
        verbose: Print progress messages
        
    Returns:
        List of discovered URLs
    """
    if verbose:
        print(f"\n🔍 Fetching HTML sitemap: {SITEMAP_URL}")
    
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            verbose=False,
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(SITEMAP_URL, config=crawler_config)
            
            if not result.success:
                if verbose:
                    print(f"❌ Failed to fetch sitemap: {result.error_message}")
                return []
            
            # Extract all internal links
            internal_links = result.links.get("internal", [])
            
            if verbose:
                print(f"   Found {len(internal_links)} internal links on sitemap page")
            
            # Build set of valid URLs (deduplicate automatically)
            valid_urls: Set[str] = set()
            
            for link in internal_links:
                href = link.get("href", "")
                if not href:
                    continue
                
                # Resolve relative URLs
                absolute_url = urljoin(SITEMAP_URL, href)
                
                # Validate URL
                if is_valid_url(absolute_url, DOMAIN_VARIANTS, BLOCKED_SUBDOMAINS):
                    valid_urls.add(absolute_url)
            
            # Convert to sorted list for reproducibility
            url_list = sorted(valid_urls)
            
            if verbose:
                print(f"✅ HTML sitemap seeding: Found {len(url_list)} unique valid URLs")
            
            return url_list
    
    except Exception as e:
        if verbose:
            print(f"❌ HTML sitemap seeding failed: {e}")
        return []


async def main():
    """CLI entry point for testing"""
    print("\n" + "="*70)
    print(" HTML SITEMAP URL SEEDER")
    print("="*70)
    
    urls = await discover_urls_from_html_sitemap(verbose=True)
    
    if urls:
        print(f"\n📋 Sample URLs (first 10):")
        for url in urls[:10]:
            print(f"   • {url}")
        
        if len(urls) > 10:
            print(f"   ... and {len(urls) - 10} more")
        
        print(f"\n💾 Would you like to save this seed list to a file? (y/n): ", end="")
        # In automation context, just show the list
        print("\n(Run interactively to save)")
    else:
        print("\n❌ No URLs discovered")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
