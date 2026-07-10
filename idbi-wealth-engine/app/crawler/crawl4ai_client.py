"""
IDBI Bank Website Crawler using Crawl4AI

Strategy:
1. Discovery: Try sitemap-based URL seeding first
2. Fallback: If sitemap yields <100 URLs, do bounded BFS deep crawl (max_depth=3)
3. Exclusions: Skip login/auth pages, non-HTML files
4. Extraction: Use PruningContentFilter for cleaned fit_markdown
5. CTA Detection: Extract action links from internal links
6. Output: One JSON file per page in app/kb_raw/

Usage:
    python -m app.crawler.crawl4ai_client --max-pages 50  # Dry run
    python -m app.crawler.crawl4ai_client                 # Full crawl
"""

import asyncio
import json
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse, urljoin, urljoin
import argparse

from crawl4ai import (
    AsyncWebCrawler,
    AsyncUrlSeeder,
    SeedingConfig,
    CrawlerRunConfig,
    BrowserConfig,
    CacheMode,
)
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter, URLPatternFilter
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


# Configuration
# Note: The canonical domain is idbi.bank.in (with dot), not idbibank.in (legacy)
DOMAIN = "www.idbi.bank.in"  # Canonical domain
DOMAIN_VARIANTS = ["www.idbi.bank.in", "idbi.bank.in"]  # Include apex domain too
BASE_URL = f"https://{DOMAIN}"
SITEMAP_URL = f"{BASE_URL}/sitemap.aspx"
DEFAULT_MAX_PAGES = 1500
SITEMAP_THRESHOLD = 100  # If sitemap finds fewer than this, use BFS fallback (HTML sitemap typically yields 500+)
MAX_DEPTH_BFS = 3
CONCURRENCY = 5  # Conservative for politeness
REQUEST_DELAY = (0.5, 1.0)  # Random delay between requests (min, max) seconds

# Directories
KB_RAW_DIR = Path(__file__).parent.parent / "kb_raw"
MANIFEST_PATH = KB_RAW_DIR / "crawl_manifest.json"

# Exclusion patterns (auth, non-HTML, problematic pages)
# Note: Subdomain-based exclusions (ebanking.*, corp.*, etc.) are handled by DomainFilter's blocked_domains
# These patterns are for same-domain path exclusions only
SKIP_PATTERNS = [
    "*/login/*",
    "*/logout/*",
    "*/account/*",
    "*/dashboard/*",
    "*/otp/*",
    "*AuthenticationController*",
    "*.pdf",
    "*.zip",
    "*.doc",
    "*.docx",
    "*.xls",
    "*.xlsx",
    "*.ppt",
    "*.pptx",
]

# Dangerous subdomains that MUST be blocked (banking portals, authentication systems)
# These are true subdomains of idbi.bank.in and would match allowed_domains without explicit blocking
# Other domains like clms.idbibank.co.in, secureonline.idbibank.com, etc. are on different
# apex domains (idbibank.co.in, idbibank.com vs our idbi.bank.in), so allowed_domains scoping
# already excludes them without needing explicit blocking.
BLOCKED_SUBDOMAINS = [
    "ebanking.idbi.bank.in",      # Internet banking portal (authentication required)
    "corp.idbi.bank.in",          # Corporate banking portal (authentication required)
    "samriddhigsec.idbi.bank.in", # Securities portal (authentication required)
    "apps.idbi.bank.in",          # Application forms subdomain (may contain sensitive forms/data)
]

# CTA patterns for action link detection
CTA_PATTERNS = [
    r"apply\s+now",
    r"open\s+account",
    r"calculate\s+emi",
    r"get\s+started",
    r"learn\s+more",
    r"download\s+form",
    r"register",
    r"sign\s+up",
    r"book\s+appointment",
    r"contact\s+us",
]

# Page type classification keywords
PAGE_TYPE_KEYWORDS = {
    "faq": [r"\bfaq\b", r"frequently\s+asked", r"questions\s+and\s+answers"],
    "rates": [r"interest\s+rate", r"charges", r"fees", r"tariff"],
    "product_info": [r"apply\s+now", r"features", r"benefits", r"eligibility"],
    "calculator": [r"calculator", r"calculate", r"emi"],
    "forms": [r"download\s+form", r"application\s+form", r"forms"],
    "contact": [r"contact\s+us", r"branch\s+locator", r"customer\s+care"],
}


def setup_directories():
    """Create output directories if they don't exist"""
    KB_RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory: {KB_RAW_DIR}")


def url_to_slug(url: str) -> str:
    """Convert URL to a filesystem-safe slug"""
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_")
    if not path or path == "index":
        path = "homepage"
    # Truncate and clean
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", path)[:150]
    return slug.strip("-").lower()


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for deduplication"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def classify_page_type(url: str, content: str, title: str = "") -> str:
    """
    Classify page type based on URL path and content keywords.
    
    Args:
        url: Page URL
        content: Page content (markdown)
        title: Page title
        
    Returns:
        Page type string
    """
    text = f"{url} {title} {content[:1000]}".lower()
    
    for page_type, patterns in PAGE_TYPE_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return page_type
    
    return "general"


def extract_cta(links: List[Dict[str, Any]], page_type: str = "general") -> Optional[Dict[str, str]]:
    """
    Extract the most relevant Call-To-Action link from internal links.
    Prioritizes specific actions with product-specific URLs, falling back to generic
    ones, and only falling back to 'Contact Us' if the page is contact-related.
    
    Args:
        links: List of link dictionaries with 'href', 'text', 'title'
        page_type: Page type classification
        
    Returns:
        Dictionary with 'cta_label' and 'cta_url', or None
    """
    # Define generic/sitewide URLs to avoid matching them as specific CTAs
    GENERIC_CTA_URLS = {
        "apply-now.aspx",
        "contact-us.aspx",
        "customer-care-centre.aspx",
        "customer-care.aspx",
        "24-7-care.aspx",
    }
    
    # Specific high-intent action patterns
    SPECIFIC_PATTERNS = [
        r"apply\s+now",
        r"open\s+account",
        r"calculate\s+emi",
        r"download\s+form",
        r"register",
        r"sign\s+up",
        r"book\s+appointment",
    ]
    
    # 1. Search for a specific CTA with a product-specific (non-generic) URL
    for link in links:
        href = link.get("href", "")
        if not href:
            continue
        
        # Check if URL matches any generic CTA pages
        href_lower = href.lower()
        is_generic = any(g_url in href_lower for g_url in GENERIC_CTA_URLS)
        
        if not is_generic:
            link_text = (link.get("text", "") + " " + link.get("title", "")).lower()
            for pattern in SPECIFIC_PATTERNS:
                if re.search(pattern, link_text, re.IGNORECASE):
                    return {
                        "cta_label": link.get("text", "").strip() or link.get("title", "").strip(),
                        "cta_url": href,
                    }
                    
    # 2. Fallback to a specific CTA with a generic URL (e.g. "Apply Now" -> apply-now.aspx)
    for link in links:
        href = link.get("href", "")
        if not href:
            continue
            
        link_text = (link.get("text", "") + " " + link.get("title", "")).lower()
        for pattern in SPECIFIC_PATTERNS:
            if re.search(pattern, link_text, re.IGNORECASE):
                return {
                    "cta_label": link.get("text", "").strip() or link.get("title", "").strip(),
                    "cta_url": href,
                }
                
    # 3. Fallback to generic "Contact Us" ONLY if page_type is "contact"
    if page_type == "contact":
        for link in links:
            href = link.get("href", "")
            if not href:
                continue
                
            link_text = (link.get("text", "") + " " + link.get("title", "")).lower()
            if re.search(r"contact\s+us", link_text, re.IGNORECASE):
                return {
                    "cta_label": "Contact Us",
                    "cta_url": href,
                }
                
    return None


def infer_category(url: str, title: str = "") -> str:
    """
    Infer product category from URL and title.
    
    Args:
        url: Page URL
        title: Page title
        
    Returns:
        Category string
    """
    text = f"{url} {title}".lower()
    
    # Priority order is important!
    # Put nri first to prevent sitewide "Corporate" in title from overriding it
    category_patterns = {
        "nri": [r"\bnri\b", r"non[-\s]resident", r"\bnre\b", r"\bnro\b", r"\bfcnr\b"],
        "deposits": [r"deposit", r"\bfd\b", r"savings", r"recurring"],
        "loans": [r"loan", r"lending", r"credit"],
        "cards": [r"credit\s+card", r"debit\s+card"],
        "insurance": [r"insurance", r"policy"],
        "investments": [r"mutual\s+fund", r"investment", r"sip", r"gold"],
        "digital_banking": [r"internet\s+banking", r"mobile\s+banking", r"online"],
        "corporate": [r"corporate", r"business", r"msme"],
        "about": [r"about\s+us", r"company", r"history"],
    }
    
    for category, patterns in category_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return category
    
    return "general"


async def discover_urls_from_html_sitemap(verbose: bool = True) -> List[str]:
    """
    Discover URLs by fetching and parsing the HTML sitemap page.
    
    IDBI Bank doesn't have a machine-readable sitemap.xml, but sitemap.aspx is a hand-curated
    HTML page with comprehensive product/service links (500+ URLs). This is more reliable than
    BFS discovery at shallow depth because:
    1. It's curated - only real product/service pages, no auto-generated cruft
    2. It's comprehensive - covers all major sections the bank wants indexed
    3. It's fast - one HTTP request vs dozens during BFS discovery
    
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
            valid_urls = set()
            skipped_by_pattern = 0
            
            for link in internal_links:
                href = link.get("href", "")
                if not href:
                    continue
                
                # Resolve relative URLs
                absolute_url = urljoin(SITEMAP_URL, href)
                parsed = urlparse(absolute_url)
                hostname = parsed.netloc.lower()
                
                # Validate URL: must be on allowed domain and not on blocked subdomain
                if parsed.scheme not in ("http", "https"):
                    continue
                
                # Check blocked subdomains first
                if any(hostname == blocked or hostname.endswith(f".{blocked}") 
                       for blocked in BLOCKED_SUBDOMAINS):
                    continue
                
                # Check allowed domains
                if not any(hostname == allowed or hostname.endswith(f".{allowed}") 
                           for allowed in DOMAIN_VARIANTS):
                    continue
                
                # Apply SKIP_PATTERNS to filter out PDFs, docs, etc.
                # Convert glob patterns to simple checks
                should_skip = False
                url_lower = absolute_url.lower()
                
                for pattern in SKIP_PATTERNS:
                    # Simple glob matching for common cases
                    if pattern.startswith("*.") and url_lower.endswith(pattern[1:]):
                        # Extension pattern like *.pdf
                        should_skip = True
                        break
                    elif pattern.startswith("*/") and pattern.endswith("/*"):
                        # Path pattern like */login/*
                        path_part = pattern[2:-2]  # Remove */ and /*
                        if f"/{path_part}/" in url_lower or url_lower.endswith(f"/{path_part}"):
                            should_skip = True
                            break
                    elif "*" not in pattern and pattern in url_lower:
                        # Simple substring match like AuthenticationController
                        should_skip = True
                        break
                
                if should_skip:
                    skipped_by_pattern += 1
                    continue
                
                valid_urls.add(absolute_url)
            
            # Convert to sorted list for reproducibility
            url_list = sorted(valid_urls)
            
            if verbose:
                print(f"✅ HTML sitemap discovery: Found {len(url_list)} unique valid URLs")
                if skipped_by_pattern > 0:
                    print(f"   Filtered out {skipped_by_pattern} URLs matching SKIP_PATTERNS")
            
            return url_list
    
    except Exception as e:
        if verbose:
            print(f"❌ HTML sitemap discovery failed: {e}")
        return []


async def discover_urls_sitemap(verbose: bool = True) -> List[str]:
    """
    Discover URLs from IDBI Bank sitemap.
    
    Note: IDBI Bank doesn't have a standard sitemap.xml. Instead, they have an HTML
    sitemap page (sitemap.aspx) with comprehensive product/service links.
    
    Args:
        verbose: Print progress messages
        
    Returns:
        List of discovered URLs
    """
    # Try standard sitemap.xml first (for future-proofing if they add one)
    if verbose:
        print(f"\n🔍 Checking for sitemap.xml...")
    
    try:
        async with AsyncUrlSeeder() as seeder:
            config = SeedingConfig(source="sitemap")
            results = await seeder.urls("www.idbi.bank.in", config)
            
            urls = [r["url"] for r in results if r.get("status") == "found"]
            
            if urls and verbose:
                print(f"✅ XML sitemap found: {len(urls)} URLs")
                return urls
            elif verbose:
                print(f"   No sitemap.xml found (this is expected)")
    
    except Exception as e:
        if verbose:
            print(f"   No sitemap.xml (this is expected): {e}")
    
    # Fall back to HTML sitemap (primary method for IDBI Bank)
    return await discover_urls_from_html_sitemap(verbose=verbose)


async def discover_urls_bfs(
    max_pages: int = DEFAULT_MAX_PAGES,
    verbose: bool = True
) -> List[str]:
    """
    Fallback: Discover URLs using bounded BFS deep crawl.
    
    NOTE: This fetches full page content during discovery but only returns URLs.
    Phase 3 will re-fetch everything. This is intentional for now (keeps phases
    decoupled), but if sitemap discovery fails and we rely on BFS for the full
    1500-page crawl, we're effectively crawling the site twice. Not critical if
    sitemap works well, which it should.
    
    Args:
        max_pages: Maximum pages to crawl
        verbose: Print progress messages
        
    Returns:
        List of discovered URLs
    """
    if verbose:
        print(f"\n🕷️  BFS Deep Crawl: max_depth={MAX_DEPTH_BFS}, max_pages={max_pages}")
    
    try:
        # Build filter chain
        # DomainFilter: allowed_domains uses subdomain matching, so ebanking.idbi.bank.in
        # is considered a subdomain of idbi.bank.in. We need to explicitly block auth subdomains.
        filter_chain = FilterChain([
            DomainFilter(
                allowed_domains=DOMAIN_VARIANTS,  # Accept www.idbi.bank.in and idbi.bank.in
                blocked_domains=BLOCKED_SUBDOMAINS  # Explicitly block auth/portal subdomains
            ),
            URLPatternFilter(patterns=SKIP_PATTERNS, reverse=True),  # reverse=True = exclude
        ])
        
        # Configure BFS strategy
        deep_crawl_strategy = BFSDeepCrawlStrategy(
            max_depth=MAX_DEPTH_BFS,
            max_pages=max_pages,
            include_external=False,
            filter_chain=filter_chain,
        )
        
        # Configure crawler
        browser_config = BrowserConfig(
            headless=True,
            verbose=verbose,
        )
        
        crawler_config = CrawlerRunConfig(
            deep_crawl_strategy=deep_crawl_strategy,
            cache_mode=CacheMode.BYPASS,
            verbose=verbose,
        )
        
        # Execute BFS crawl
        async with AsyncWebCrawler(config=browser_config) as crawler:
            results = await crawler.arun(BASE_URL, config=crawler_config)
            
            # Extract URLs from results (results is a list when using deep_crawl_strategy)
            if isinstance(results, list):
                urls = [r.url for r in results if r.success]
            else:
                urls = [results.url] if results.success else []
            
            if verbose:
                print(f"✅ BFS discovery: Found {len(urls)} URLs")
            
            return urls
    
    except Exception as e:
        if verbose:
            print(f"❌ BFS discovery failed: {e}")
        return []


def process_crawl_result(result) -> Optional[Dict[str, Any]]:
    """
    Process an already-fetched CrawlResult into structured JSON.
    No network call - just transforms the result object.
    Synchronous function (no async/await needed).
    
    Args:
        result: CrawlResult object from arun_many
        
    Returns:
        Dictionary with page data, or None if processing failed
    """
    try:
        # Extract cleaned markdown
        fit_markdown = result.markdown.fit_markdown or result.markdown.raw_markdown
        
        # Strip persistent sitewide alert banners and announcements table
        if fit_markdown:
            # 1. Strip announcements table (starts with eUWB notice and ends with table row formatting)
            announcements_pattern = re.compile(
                r"\|\s*\|\s*\[\s*Attention:\s*Shareholders of eUWB.*?\n\|\s*---\s*\|[^\n]*\n", 
                re.DOTALL | re.IGNORECASE
            )
            fit_markdown = announcements_pattern.sub("", fit_markdown)
            
            # 2. Strip maintenance banner (starts with "Due to technical reasons" and ends with "inconvenience caused")
            maintenance_pattern = re.compile(
                r"[“\"'\s]*Due to technical reasons, the site is not available.*?(inconvenience caused[”\"'\s]*\.*)",
                re.DOTALL | re.IGNORECASE
            )
            fit_markdown = maintenance_pattern.sub("", fit_markdown)
            
            fit_markdown = fit_markdown.strip()
        
        # Extract metadata
        title = result.metadata.get("title", "") or result.metadata.get("og:title", "")
        
        # Classify page type and category
        page_type = classify_page_type(result.url, fit_markdown, title)
        category = infer_category(result.url, title)
        
        # Extract CTA from internal links
        internal_links = result.links.get("internal", [])
        cta = extract_cta(internal_links, page_type)
        
        # Compute content hash
        content_hash = compute_content_hash(fit_markdown)
        
        # Build output structure
        page_data = {
            "url": result.url,
            "title": title,
            "content": fit_markdown,
            "category": category,
            "page_type": page_type,
            "cta_label": cta.get("cta_label") if cta else None,
            "cta_url": cta.get("cta_url") if cta else None,
            "content_hash": content_hash,
            "crawled_at": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "description": result.metadata.get("description", ""),
                "keywords": result.metadata.get("keywords", ""),
                "word_count": len(fit_markdown.split()),
                "internal_links_count": len(internal_links),
                "external_links_count": len(result.links.get("external", [])),
            }
        }
        
        return page_data
    
    except Exception as e:
        print(f"❌ Error processing result for {result.url}: {e}")
        return None


async def crawl_idbi_bank(
    max_pages: Optional[int] = None,
    use_sitemap: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Main crawl orchestrator for IDBI Bank website.
    
    Args:
        max_pages: Maximum pages to crawl (None = unlimited, use for dry runs)
        use_sitemap: Try sitemap discovery first
        verbose: Print progress messages
        
    Returns:
        Crawl manifest dictionary
    """
    setup_directories()
    
    # Phase 1: URL Discovery
    urls = []
    discovery_method = "none"
    
    if use_sitemap:
        urls = await discover_urls_sitemap(verbose=verbose)
        discovery_method = "sitemap"
        
        # Fallback to BFS if sitemap yields too few URLs
        if len(urls) < SITEMAP_THRESHOLD:
            if verbose:
                print(f"⚠️  Sitemap yielded only {len(urls)} URLs (threshold: {SITEMAP_THRESHOLD})")
                print("   Falling back to BFS deep crawl...")
            bfs_urls = await discover_urls_bfs(max_pages=max_pages or DEFAULT_MAX_PAGES, verbose=verbose)
            urls.extend(bfs_urls)
            # Deduplicate
            urls = list(set(urls))
            discovery_method = "sitemap+bfs"
    else:
        urls = await discover_urls_bfs(max_pages=max_pages or DEFAULT_MAX_PAGES, verbose=verbose)
        discovery_method = "bfs"
    
    if not urls:
        print("❌ No URLs discovered. Exiting.")
        return {"error": "No URLs discovered", "urls_found": 0}
    
    # Apply max_pages limit if specified
    if max_pages and len(urls) > max_pages:
        if verbose:
            print(f"⚠️  Limiting crawl to {max_pages} URLs (discovered {len(urls)})")
        urls = urls[:max_pages]
    
    if verbose:
        print(f"\n📋 Total URLs to crawl: {len(urls)}")
        print(f"   Discovery method: {discovery_method}")
    
    # Phase 2: Configure crawler for content extraction
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,  # Reduce noise during batch crawl
    )
    
    # Configure content filter for cleaned markdown
    content_filter = PruningContentFilter(
        threshold=0.45,
        threshold_type="dynamic",
        min_word_threshold=10,
    )
    
    markdown_generator = DefaultMarkdownGenerator(content_filter=content_filter)
    
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=markdown_generator,
        only_text=False,  # We want links and media
        verbose=False,
    )
    
    # Phase 3: Batch crawl with concurrency control
    if verbose:
        print(f"\n🚀 Starting batch crawl (concurrency: {CONCURRENCY})...")
    
    crawled_pages = []
    failed_urls = []
    skipped_urls = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Use arun_many for efficient batch processing
        batch_config = crawler_config.clone(stream=True)
        
        crawl_count = 0
        async for result in await crawler.arun_many(urls, config=batch_config):
            crawl_count += 1
            
            if result.success:
                # Process the already-fetched result (no second network call)
                page_data = process_crawl_result(result)
                
                if page_data:
                    # Save to JSON file
                    slug = url_to_slug(result.url)
                    filename = f"{slug}_{page_data['content_hash'][:8]}.json"
                    filepath = KB_RAW_DIR / filename
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(page_data, f, indent=2, ensure_ascii=False)
                    
                    crawled_pages.append({
                        "url": result.url,
                        "file": filename,
                        "category": page_data["category"],
                        "page_type": page_data["page_type"],
                    })
                    
                    if verbose and crawl_count % 10 == 0:
                        print(f"   ✅ Progress: {crawl_count}/{len(urls)} pages")
                else:
                    skipped_urls.append(result.url)
            else:
                failed_urls.append({
                    "url": result.url,
                    "error": result.error_message,
                })
                if verbose:
                    print(f"   ❌ Failed: {result.url}")
    
    # Phase 4: Generate manifest
    manifest = {
        "crawl_timestamp": datetime.utcnow().isoformat() + "Z",
        "domain": DOMAIN,
        "discovery_method": discovery_method,
        "urls_discovered": len(urls),
        "pages_crawled": len(crawled_pages),
        "pages_failed": len(failed_urls),
        "pages_skipped": len(skipped_urls),
        "crawled_pages": crawled_pages,
        "failed_urls": failed_urls,
        "skipped_urls": skipped_urls,
    }
    
    # Save manifest
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    if verbose:
        print(f"\n✅ Crawl complete!")
        print(f"   📊 Successfully crawled: {len(crawled_pages)} pages")
        print(f"   ❌ Failed: {len(failed_urls)} pages")
        print(f"   ⏭️  Skipped: {len(skipped_urls)} pages")
        print(f"   📄 Manifest saved: {MANIFEST_PATH}")
        print(f"   📁 Output directory: {KB_RAW_DIR}")
    
    return manifest


async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Crawl IDBI Bank website using Crawl4AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with 50 pages
  python -m app.crawler.crawl4ai_client --max-pages 50

  # Full crawl with sitemap discovery
  python -m app.crawler.crawl4ai_client

  # BFS-only crawl (skip sitemap)
  python -m app.crawler.crawl4ai_client --no-sitemap --max-pages 500
        """
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to crawl (default: unlimited)",
    )
    
    parser.add_argument(
        "--no-sitemap",
        action="store_true",
        help="Skip sitemap discovery, use BFS only",
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages",
    )
    
    args = parser.parse_args()
    
    # Run crawler
    manifest = await crawl_idbi_bank(
        max_pages=args.max_pages,
        use_sitemap=not args.no_sitemap,
        verbose=not args.quiet,
    )
    
    # Print summary
    if not args.quiet:
        print("\n" + "="*60)
        print("CRAWL SUMMARY")
        print("="*60)
        print(f"Discovery Method: {manifest.get('discovery_method', 'unknown')}")
        print(f"URLs Discovered:  {manifest.get('urls_discovered', 0)}")
        print(f"Pages Crawled:    {manifest.get('pages_crawled', 0)}")
        print(f"Pages Failed:     {manifest.get('pages_failed', 0)}")
        print(f"Pages Skipped:    {manifest.get('pages_skipped', 0)}")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
