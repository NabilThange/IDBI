"""
Test script to validate Crawl4AI API and configuration
Run this before the full crawl to ensure everything is set up correctly.

Usage:
    python -m app.crawler.test_crawl4ai_api
"""

import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


async def test_basic_crawl():
    """Test basic crawl functionality"""
    print("\n" + "="*60)
    print("TEST 1: Basic Crawl (Single Page)")
    print("="*60)
    
    try:
        browser_config = BrowserConfig(headless=True, verbose=True)
        config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun("https://www.idbibank.in/index.aspx", config=config)
            
            if result.success:
                print("✅ Basic crawl successful")
                print(f"   URL: {result.url}")
                print(f"   Title: {result.metadata.get('title', 'N/A')}")
                print(f"   Raw Markdown Length: {len(result.markdown.raw_markdown)}")
                print(f"   Internal Links: {len(result.links.get('internal', []))}")
                print(f"   External Links: {len(result.links.get('external', []))}")
                return True
            else:
                print(f"❌ Basic crawl failed: {result.error_message}")
                return False
    
    except Exception as e:
        print(f"❌ Exception during basic crawl: {e}")
        return False


async def test_pruning_filter():
    """Test PruningContentFilter for cleaned markdown"""
    print("\n" + "="*60)
    print("TEST 2: PruningContentFilter (Cleaned Markdown)")
    print("="*60)
    
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        
        # Configure content filter
        content_filter = PruningContentFilter(
            threshold=0.45,
            threshold_type="dynamic",
            min_word_threshold=10,
        )
        
        markdown_generator = DefaultMarkdownGenerator(content_filter=content_filter)
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=markdown_generator,
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun("https://www.idbibank.in/index.aspx", config=config)
            
            if result.success:
                raw_len = len(result.markdown.raw_markdown)
                fit_len = len(result.markdown.fit_markdown)
                reduction = ((raw_len - fit_len) / raw_len * 100) if raw_len > 0 else 0
                
                print("✅ PruningContentFilter working")
                print(f"   Raw Markdown: {raw_len} chars")
                print(f"   Fit Markdown: {fit_len} chars")
                print(f"   Reduction: {reduction:.1f}%")
                print(f"\n   First 200 chars of fit_markdown:")
                print(f"   {result.markdown.fit_markdown[:200]}...")
                return True
            else:
                print(f"❌ Pruning filter test failed: {result.error_message}")
                return False
    
    except Exception as e:
        print(f"❌ Exception during pruning test: {e}")
        return False


async def test_link_extraction():
    """Test link extraction and categorization"""
    print("\n" + "="*60)
    print("TEST 3: Link Extraction & CTA Detection")
    print("="*60)
    
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Test on a product page with CTAs
            result = await crawler.arun("https://www.idbibank.in/index.aspx", config=config)
            
            if result.success:
                internal_links = result.links.get("internal", [])
                
                print("✅ Link extraction working")
                print(f"   Found {len(internal_links)} internal links")
                
                # Look for CTA-like links
                cta_keywords = ["apply", "open", "calculate", "register", "login"]
                potential_ctas = [
                    link for link in internal_links[:10]
                    if any(kw in link.get("text", "").lower() for kw in cta_keywords)
                ]
                
                print(f"   Potential CTAs found: {len(potential_ctas)}")
                
                if potential_ctas:
                    print(f"\n   Sample CTAs:")
                    for cta in potential_ctas[:3]:
                        print(f"   - \"{cta.get('text', 'N/A')}\" → {cta.get('href', 'N/A')}")
                
                return True
            else:
                print(f"❌ Link extraction test failed: {result.error_message}")
                return False
    
    except Exception as e:
        print(f"❌ Exception during link extraction test: {e}")
        return False


async def test_batch_crawl():
    """Test arun_many for batch crawling"""
    print("\n" + "="*60)
    print("TEST 4: Batch Crawl (arun_many)")
    print("="*60)
    
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            stream=True,  # Stream results
        )
        
        test_urls = [
            "https://www.idbibank.in/index.aspx",
            "https://www.idbibank.in/about-us.aspx",
        ]
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print(f"   Crawling {len(test_urls)} URLs...")
            
            success_count = 0
            async for result in await crawler.arun_many(test_urls, config=config):
                if result.success:
                    success_count += 1
                    print(f"   ✅ {result.url} ({len(result.markdown.raw_markdown)} chars)")
                else:
                    print(f"   ❌ {result.url} - {result.error_message}")
            
            print(f"\n✅ Batch crawl complete: {success_count}/{len(test_urls)} successful")
            return success_count == len(test_urls)
    
    except Exception as e:
        print(f"❌ Exception during batch crawl test: {e}")
        return False


async def test_sitemap_discovery():
    """Test sitemap URL discovery (if available)"""
    print("\n" + "="*60)
    print("TEST 5: Sitemap URL Discovery")
    print("="*60)
    
    try:
        from crawl4ai import AsyncUrlSeeder, SeedingConfig
        
        async with AsyncUrlSeeder() as seeder:
            config = SeedingConfig(source="sitemap")
            results = await seeder.urls("www.idbibank.in", config)
            
            urls = [r["url"] for r in results if r.get("status") == "found"]
            
            print(f"✅ Sitemap discovery working")
            print(f"   Found {len(urls)} URLs from sitemap")
            
            if urls:
                print(f"\n   Sample URLs:")
                for url in urls[:5]:
                    print(f"   - {url}")
            
            return len(urls) > 0
    
    except Exception as e:
        print(f"❌ Exception during sitemap discovery: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" CRAWL4AI API VALIDATION TESTS")
    print("="*70)
    
    tests = [
        ("Basic Crawl", test_basic_crawl),
        ("PruningContentFilter", test_pruning_filter),
        ("Link Extraction", test_link_extraction),
        ("Batch Crawl (arun_many)", test_batch_crawl),
        ("Sitemap Discovery", test_sitemap_discovery),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print("="*70)
    print(f"  Result: {passed}/{total} tests passed")
    print("="*70)
    
    if passed == total:
        print("\n🎉 All tests passed! Ready to run full crawl.")
        print("   Next step: python -m app.crawler.crawl4ai_client --max-pages 50")
    else:
        print("\n⚠️  Some tests failed. Please fix issues before running full crawl.")


if __name__ == "__main__":
    asyncio.run(main())
