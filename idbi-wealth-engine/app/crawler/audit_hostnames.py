"""
Independent hostname audit script.
Extracts and displays all distinct hostnames from crawled URLs without relying on
any hardcoded pattern lists. This is a blunt sanity check to catch violations that
weren't anticipated in the exclusion patterns.

Usage:
    python -m app.crawler.audit_hostnames
"""

import json
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter
from typing import Set, List, Tuple


def extract_hostnames_from_manifest() -> Tuple[Set[str], int]:
    """
    Extract all distinct hostnames from the crawl manifest.
    
    Returns:
        Tuple of (set of hostnames, total URL count)
    """
    manifest_path = Path(__file__).parent.parent / "kb_raw" / "crawl_manifest.json"
    
    if not manifest_path.exists():
        return set(), 0
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    hostnames = set()
    url_count = 0
    
    # Extract from crawled pages
    for page in manifest.get("crawled_pages", []):
        url = page["url"]
        hostname = urlparse(url).netloc
        if hostname:
            hostnames.add(hostname)
            url_count += 1
    
    # Extract from failed URLs (should also be checked)
    for failure in manifest.get("failed_urls", []):
        url = failure["url"]
        hostname = urlparse(url).netloc
        if hostname:
            hostnames.add(hostname)
            url_count += 1
    
    return hostnames, url_count


def extract_hostnames_from_json_files() -> Tuple[Counter, int]:
    """
    Extract all distinct hostnames from individual JSON files with counts.
    
    Returns:
        Tuple of (Counter of hostnames, total URL count)
    """
    kb_raw_dir = Path(__file__).parent.parent / "kb_raw"
    
    if not kb_raw_dir.exists():
        return Counter(), 0
    
    hostname_counts = Counter()
    json_files = list(kb_raw_dir.glob("*.json"))
    
    # Exclude manifest
    json_files = [f for f in json_files if f.name != "crawl_manifest.json"]
    
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            url = data.get("url", "")
            hostname = urlparse(url).netloc
            if hostname:
                hostname_counts[hostname] += 1
        except Exception as e:
            print(f"⚠️  Error reading {json_file.name}: {e}")
    
    return hostname_counts, sum(hostname_counts.values())


def main():
    """Run hostname audit"""
    print("\n" + "="*70)
    print(" HOSTNAME AUDIT")
    print("="*70)
    print("\nThis is an independent verification that doesn't rely on pattern lists.")
    print("It shows ALL hostnames found in crawled URLs.\n")
    
    # Check if any data exists
    manifest_path = Path(__file__).parent.parent / "kb_raw" / "crawl_manifest.json"
    kb_raw_dir = Path(__file__).parent.parent / "kb_raw"
    
    has_data = manifest_path.exists() or (kb_raw_dir.exists() and any(kb_raw_dir.glob("*.json")))
    
    if not has_data:
        print("❌ NO CRAWL DATA FOUND")
        print("   No data in app/kb_raw/ to audit.")
        print("\n   Run the crawler first:")
        print("   python -m app.crawler.crawl4ai_client --max-pages 50")
        print("\n" + "="*70)
        return
    
    # Extract hostnames from manifest
    print("🔍 Extracting hostnames from manifest...")
    manifest_hostnames, manifest_url_count = extract_hostnames_from_manifest()
    
    if manifest_hostnames:
        print(f"   Found {len(manifest_hostnames)} distinct hostname(s) in {manifest_url_count} URLs")
    else:
        print("   ⚠️  No manifest data found")
    
    # Extract hostnames from JSON files
    print("\n🔍 Extracting hostnames from JSON files...")
    hostname_counts, json_url_count = extract_hostnames_from_json_files()
    
    if hostname_counts:
        print(f"   Found {len(hostname_counts)} distinct hostname(s) in {json_url_count} files")
    else:
        print("   ⚠️  No JSON files found")
    
    # Combine and display results
    print("\n" + "="*70)
    print(" DISTINCT HOSTNAMES FOUND")
    print("="*70)
    
    if not manifest_hostnames and not hostname_counts:
        print("\n⚠️  No hostnames found in crawl data")
        print("\n" + "="*70)
        return
    
    # Use hostname_counts if available (more detailed), otherwise manifest_hostnames
    if hostname_counts:
        print(f"\nTotal distinct hostnames: {len(hostname_counts)}")
        print(f"Total URLs crawled: {json_url_count}\n")
        
        for hostname, count in hostname_counts.most_common():
            print(f"  {hostname:<40} ({count} pages)")
    else:
        print(f"\nTotal distinct hostnames: {len(manifest_hostnames)}")
        print(f"Total URLs in manifest: {manifest_url_count}\n")
        
        for hostname in sorted(manifest_hostnames):
            print(f"  {hostname}")
    
    # Validation check
    print("\n" + "="*70)
    print(" VALIDATION")
    print("="*70)
    
    expected_hostnames = {"www.idbi.bank.in", "idbi.bank.in"}
    actual_hostnames = set(hostname_counts.keys()) if hostname_counts else manifest_hostnames
    
    if actual_hostnames.issubset(expected_hostnames):
        print("\n✅ ALL HOSTNAMES ARE VALID!")
        print(f"   Only expected domains found: {', '.join(sorted(actual_hostnames))}")
        print("   No auth subdomains or external domains detected.")
    else:
        unexpected = actual_hostnames - expected_hostnames
        print(f"\n❌ UNEXPECTED HOSTNAMES DETECTED: {len(unexpected)}")
        print("\n⚠️  The following hostnames should NOT be in the crawl output:\n")
        for hostname in sorted(unexpected):
            count = hostname_counts.get(hostname, "?") if hostname_counts else "?"
            print(f"  ❌ {hostname:<40} ({count} pages)")
        
        print("\n⚠️  ACTION REQUIRED:")
        print("   - These domains should be in BLOCKED_SUBDOMAINS in crawl4ai_client.py")
        print("   - Review DomainFilter configuration")
        print("   - Do NOT proceed with full crawl until this is fixed")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
