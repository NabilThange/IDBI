"""
Verification script to check that exclusion patterns are working correctly.
Scans crawl output for any auth/login/restricted URLs that should have been blocked.

Usage:
    python -m app.crawler.verify_exclusions
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Import exclusion patterns directly from crawl4ai_client to ensure single source of truth
# This prevents the drift that caused previous violations to slip through undetected
try:
    from .crawl4ai_client import SKIP_PATTERNS, BLOCKED_SUBDOMAINS
except ImportError:
    from crawl4ai_client import SKIP_PATTERNS, BLOCKED_SUBDOMAINS

# Convert glob patterns to regex for validation
def glob_to_regex(pattern: str) -> str:
    """Convert glob pattern (with *) to regex pattern"""
    # Escape special regex chars except *
    pattern = pattern.replace(".", r"\.")
    pattern = pattern.replace("*", ".*")
    return pattern

# Build forbidden patterns from SKIP_PATTERNS
FORBIDDEN_PATTERNS = [glob_to_regex(p) for p in SKIP_PATTERNS if not p.startswith("*.")]

# Use BLOCKED_SUBDOMAINS directly from crawl4ai_client
FORBIDDEN_SUBDOMAINS = BLOCKED_SUBDOMAINS


def check_url_against_patterns(url: str, patterns: List[str]) -> List[str]:
    """
    Check if URL matches any forbidden patterns.
    
    Args:
        url: URL to check
        patterns: List of regex patterns
        
    Returns:
        List of matched pattern strings
    """
    matches = []
    for pattern in patterns:
        if re.search(pattern, url, re.IGNORECASE):
            matches.append(pattern)
    return matches


def check_url_subdomain(url: str) -> Optional[str]:
    """
    Check if URL is on a forbidden subdomain.
    
    Args:
        url: URL to check
        
    Returns:
        Forbidden subdomain if matched, None otherwise
    """
    from urllib.parse import urlparse
    hostname = urlparse(url).hostname
    
    if hostname in FORBIDDEN_SUBDOMAINS:
        return hostname
    
    return None


def verify_manifest() -> Tuple[int, List[Dict]]:
    """
    Verify manifest for forbidden URLs.
    
    Returns:
        Tuple of (total_urls, violations)
    """
    manifest_path = Path(__file__).parent.parent / "kb_raw" / "crawl_manifest.json"
    
    if not manifest_path.exists():
        print(f"❌ Manifest not found: {manifest_path}")
        return 0, []
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    violations = []
    
    # Check crawled pages
    for page in manifest.get("crawled_pages", []):
        url = page["url"]
        matches = check_url_against_patterns(url, FORBIDDEN_PATTERNS)
        subdomain = check_url_subdomain(url)
        
        if matches or subdomain:
            violation = {
                "url": url,
                "file": page["file"],
                "matched_patterns": matches,
            }
            if subdomain:
                violation["forbidden_subdomain"] = subdomain
            violations.append(violation)
    
    # Check failed URLs (should be okay, but note if auth pages are there)
    for failure in manifest.get("failed_urls", []):
        url = failure["url"]
        matches = check_url_against_patterns(url, FORBIDDEN_PATTERNS)
        subdomain = check_url_subdomain(url)
        
        if matches or subdomain:
            violation = {
                "url": url,
                "status": "FAILED",
                "matched_patterns": matches,
            }
            if subdomain:
                violation["forbidden_subdomain"] = subdomain
            violations.append(violation)
    
    total_urls = manifest.get("pages_crawled", 0) + manifest.get("pages_failed", 0)
    
    return total_urls, violations


def verify_json_files() -> List[Dict]:
    """
    Verify individual JSON files for forbidden URLs.
    
    Returns:
        List of violations
    """
    kb_raw_dir = Path(__file__).parent.parent / "kb_raw"
    
    if not kb_raw_dir.exists():
        print(f"❌ kb_raw directory not found: {kb_raw_dir}")
        return []
    
    violations = []
    json_files = list(kb_raw_dir.glob("*.json"))
    
    # Exclude manifest
    json_files = [f for f in json_files if f.name != "crawl_manifest.json"]
    
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            url = data.get("url", "")
            matches = check_url_against_patterns(url, FORBIDDEN_PATTERNS)
            subdomain = check_url_subdomain(url)
            
            if matches or subdomain:
                violation = {
                    "url": url,
                    "file": json_file.name,
                    "matched_patterns": matches,
                }
                if subdomain:
                    violation["forbidden_subdomain"] = subdomain
                violations.append(violation)
        except Exception as e:
            print(f"⚠️  Error reading {json_file.name}: {e}")
    
    return violations


def main():
    """Run verification checks"""
    print("\n" + "="*70)
    print(" EXCLUSION PATTERN VERIFICATION")
    print("="*70)
    
    print("\n🔍 Checking manifest...")
    total_urls, manifest_violations = verify_manifest()
    
    print(f"   Total URLs in manifest: {total_urls}")
    print(f"   Violations found: {len(manifest_violations)}")
    
    print("\n🔍 Checking individual JSON files...")
    json_violations = verify_json_files()
    print(f"   Violations found: {len(json_violations)}")
    
    # Combine violations
    all_violations = manifest_violations + json_violations
    
    # Deduplicate by URL
    seen_urls = set()
    unique_violations = []
    for v in all_violations:
        if v["url"] not in seen_urls:
            seen_urls.add(v["url"])
            unique_violations.append(v)
    
    # Check if there's any data to verify
    manifest_path = Path(__file__).parent.parent / "kb_raw" / "crawl_manifest.json"
    kb_raw_dir = Path(__file__).parent.parent / "kb_raw"
    
    has_data = manifest_path.exists() or (kb_raw_dir.exists() and any(kb_raw_dir.glob("*.json")))
    
    # Report results
    print("\n" + "="*70)
    print(" RESULTS")
    print("="*70)
    
    if not has_data:
        print("\n⚠️  NOTHING TO VERIFY")
        print("   Crawler has not been run yet.")
        print("   No crawl data found in app/kb_raw/")
        print("\n   Run the crawler first:")
        print("   python -m app.crawler.crawl4ai_client --max-pages 50")
        print("\n" + "="*70)
        return None  # Distinct from success/failure
    
    if not unique_violations:
        print("\n✅ ALL CHECKS PASSED!")
        print("   No forbidden URLs found in crawl output.")
        print("   Exclusion patterns are working correctly.")
        print(f"\n   Verified {total_urls} URLs from crawl data.")
    else:
        print(f"\n❌ VIOLATIONS FOUND: {len(unique_violations)}")
        print("\n⚠️  The following forbidden URLs were crawled:")
        
        for i, violation in enumerate(unique_violations, 1):
            print(f"\n{i}. {violation['url']}")
            if violation.get("matched_patterns"):
                print(f"   Matched patterns: {', '.join(violation['matched_patterns'])}")
            if violation.get("forbidden_subdomain"):
                print(f"   ⚠️  FORBIDDEN SUBDOMAIN: {violation['forbidden_subdomain']}")
            if "file" in violation:
                print(f"   File: {violation['file']}")
            if "status" in violation:
                print(f"   Status: {violation['status']}")
        
        print("\n⚠️  ACTION REQUIRED:")
        print("   - Review URLPatternFilter configuration in crawl4ai_client.py")
        print("   - Verify SKIP_PATTERNS includes these patterns")
        print("   - Check that reverse=True is set on URLPatternFilter")
        print("   - Do NOT proceed with full crawl until this is fixed")
    
    print("\n" + "="*70)
    
    return len(unique_violations) == 0


if __name__ == "__main__":
    success = main()
    # Exit codes: 0=verified clean, 1=violations found, 2=no data to verify
    if success is None:
        exit(2)
    exit(0 if success else 1)
