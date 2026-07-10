"""
Analyze seed URLs extracted from HTML sitemap.
Shows breakdown by scheme, extension, patterns to validate quality.
"""

import asyncio
from collections import Counter
from urllib.parse import urlparse
import re

# Import from crawl4ai_client directly (single source of truth)
try:
    from .crawl4ai_client import discover_urls_from_html_sitemap
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from crawl4ai_client import discover_urls_from_html_sitemap


def analyze_urls(urls):
    """Analyze URL list for quality issues"""
    
    schemes = Counter()
    extensions = Counter()
    patterns = {
        "pdf": 0,
        "doc/docx": 0,
        "xls/xlsx": 0,
        "zip": 0,
        "mailto": 0,
        "javascript": 0,
        "fragment_only": 0,  # #anchor with no path
        "aspx": 0,
        "asp": 0,
        "html": 0,
        "no_extension": 0,
    }
    
    for url in urls:
        parsed = urlparse(url)
        
        # Count schemes
        schemes[parsed.scheme] += 1
        
        # Check for problematic patterns
        if parsed.scheme == "mailto":
            patterns["mailto"] += 1
        elif parsed.scheme == "javascript":
            patterns["javascript"] += 1
        elif parsed.fragment and not parsed.path:
            patterns["fragment_only"] += 1
        
        # Extract extension
        path = parsed.path.lower()
        if path.endswith(".pdf"):
            extensions[".pdf"] += 1
            patterns["pdf"] += 1
        elif path.endswith((".doc", ".docx")):
            extensions[".doc/.docx"] += 1
            patterns["doc/docx"] += 1
        elif path.endswith((".xls", ".xlsx")):
            extensions[".xls/.xlsx"] += 1
            patterns["xls/xlsx"] += 1
        elif path.endswith(".zip"):
            extensions[".zip"] += 1
            patterns["zip"] += 1
        elif path.endswith(".aspx"):
            extensions[".aspx"] += 1
            patterns["aspx"] += 1
        elif path.endswith(".asp"):
            extensions[".asp"] += 1
            patterns["asp"] += 1
        elif path.endswith((".html", ".htm")):
            extensions[".html/.htm"] += 1
            patterns["html"] += 1
        elif "." not in path.split("/")[-1]:
            patterns["no_extension"] += 1
    
    return schemes, extensions, patterns


async def main():
    print("\n" + "="*70)
    print(" SEED URL ANALYSIS")
    print("="*70)
    
    urls = await discover_urls_from_html_sitemap(verbose=True)
    
    if not urls:
        print("\n❌ No URLs to analyze")
        return
    
    schemes, extensions, patterns = analyze_urls(urls)
    
    print(f"\n📊 ANALYSIS RESULTS")
    print("="*70)
    
    print(f"\nTotal URLs: {len(urls)}")
    
    print(f"\n🔗 URL Schemes:")
    for scheme, count in schemes.most_common():
        print(f"   {scheme}: {count}")
    
    print(f"\n📄 File Extensions:")
    for ext, count in sorted(extensions.items(), key=lambda x: -x[1]):
        print(f"   {ext}: {count}")
    
    print(f"\n⚠️  Problematic Patterns:")
    problematic = {k: v for k, v in patterns.items() 
                   if k in ["pdf", "doc/docx", "xls/xlsx", "zip", "mailto", "javascript", "fragment_only"] and v > 0}
    if problematic:
        for pattern, count in problematic.items():
            print(f"   {pattern}: {count}")
    else:
        print("   None found ✅")
    
    print(f"\n✅ Clean Web Pages:")
    clean_count = patterns["aspx"] + patterns["asp"] + patterns["html"] + patterns["no_extension"]
    print(f"   .aspx/.asp/.html/no-ext: {clean_count}")
    
    # Check for duplicates
    print(f"\n🔄 Duplicate Check:")
    unique_count = len(set(urls))
    duplicate_count = len(urls) - unique_count
    if duplicate_count > 0:
        print(f"   ❌ Found {duplicate_count} duplicates in seed list!")
        print(f"   Original: {len(urls)} URLs")
        print(f"   Unique: {unique_count} URLs")
    else:
        print(f"   ✅ No duplicates (all {len(urls)} URLs are unique)")
    
    # Sample URLs by category
    print(f"\n📋 Sample URLs by Type:")
    
    print(f"\n   Product Pages (.aspx):")
    aspx_urls = [u for u in urls if u.endswith(".aspx")][:5]
    for url in aspx_urls:
        print(f"      • {url}")
    
    if any(".pdf" in u for u in urls):
        print(f"\n   ⚠️  PDF Documents:")
        pdf_urls = [u for u in urls if ".pdf" in u][:5]
        for url in pdf_urls:
            print(f"      • {url}")
    
    if any("mailto:" in u for u in urls):
        print(f"\n   ⚠️  Mailto Links:")
        mailto_urls = [u for u in urls if "mailto:" in u][:5]
        for url in mailto_urls:
            print(f"      • {url}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
