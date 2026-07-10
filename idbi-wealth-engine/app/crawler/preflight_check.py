"""
Pre-flight check before running the crawler.
Verifies dependencies and configuration.

Usage:
    python -m app.crawler.preflight_check
"""

import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check Python version (3.8+ required)"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required (found {version.major}.{version.minor})")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_crawl4ai():
    """Check if crawl4ai is installed"""
    try:
        import crawl4ai
        
        # Try multiple ways to get version
        version = "unknown"
        try:
            # Try __version__ attribute (string)
            if hasattr(crawl4ai, '__version__') and isinstance(crawl4ai.__version__, str):
                version = crawl4ai.__version__
            # Try __version__.__version__ (submodule)
            elif hasattr(crawl4ai, '__version__') and hasattr(crawl4ai.__version__, '__version__'):
                version = crawl4ai.__version__.__version__
            # Try importlib.metadata
            else:
                import importlib.metadata
                version = importlib.metadata.version("crawl4ai")
        except:
            pass
        
        print(f"✅ crawl4ai installed (version: {version})")
        return True
    except ImportError:
        print("❌ crawl4ai not installed")
        print("   Install: pip install crawl4ai>=0.9.0")
        return False


def check_playwright():
    """Check if Playwright browsers are installed"""
    try:
        # Try to import playwright and check if browsers are available
        from playwright.sync_api import sync_playwright
        
        # Try to get the browser executable path
        with sync_playwright() as p:
            # If this succeeds, chromium is installed
            p.chromium
        
        print("✅ Playwright browsers installed")
        return True
    except ImportError:
        print("❌ Playwright not installed")
        print("   Install: pip install playwright")
        return False
    except Exception as e:
        # If we can import but browsers aren't installed, suggest installation
        if "executable doesn't exist" in str(e).lower() or "browser" in str(e).lower():
            print("❌ Playwright chromium browser not installed")
            print("   Install: playwright install chromium")
            return False
        print(f"⚠️  Could not verify Playwright: {e}")
        return True  # Don't block on this


def check_output_dir():
    """Check if output directory is ready"""
    kb_raw_dir = Path(__file__).parent.parent / "kb_raw"
    
    if kb_raw_dir.exists():
        json_files = list(kb_raw_dir.glob("*.json"))
        if json_files:
            print(f"⚠️  kb_raw/ directory contains {len(json_files)} existing files")
            print("   Previous crawl data will be overwritten")
        else:
            print("✅ kb_raw/ directory exists (empty)")
    else:
        print("✅ kb_raw/ directory will be created")
    
    return True


def check_api_classes():
    """Check that required Crawl4AI classes are importable"""
    try:
        from crawl4ai import AsyncWebCrawler, AsyncUrlSeeder, SeedingConfig
        from crawl4ai import CrawlerRunConfig, BrowserConfig, CacheMode
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
        from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter, URLPatternFilter
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        
        print("✅ All required Crawl4AI classes importable")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Your crawl4ai version may be incompatible")
        return False


def main():
    """Run all pre-flight checks"""
    print("\n" + "="*70)
    print(" PRE-FLIGHT CHECK")
    print("="*70 + "\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Crawl4AI Package", check_crawl4ai),
        ("Crawl4AI API Classes", check_api_classes),
        ("Playwright Browsers", check_playwright),
        ("Output Directory", check_output_dir),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n🔍 Checking {name}...")
        results.append(check_func())
    
    print("\n" + "="*70)
    print(" RESULTS")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"\n✅ All checks passed ({passed}/{total})")
        print("\n🚀 Ready to run crawler!")
        print("\n   Next steps:")
        print("   1. Run API tests: python -m app.crawler.test_crawl4ai_api")
        print("   2. Run dry run: python -m app.crawler.crawl4ai_client --max-pages 50")
        print("   3. Verify output: python -m app.crawler.verify_exclusions")
    else:
        print(f"\n❌ {total - passed} check(s) failed")
        print("\n   Fix the issues above before running the crawler.")
    
    print("\n" + "="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
