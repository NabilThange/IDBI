# IDBI Bank Crawler - Crawl4AI Implementation

## Overview

This module uses **Crawl4AI** (one of the best web crawlers optimized for LLMs) to crawl the IDBI Bank website and generate a clean, structured knowledge base for the RAG system.

## Features

- **Smart URL Discovery**: Sitemap-first approach with BFS deep crawl fallback
- **Intelligent Filtering**: Excludes auth pages, login portals, and non-HTML files
- **Clean Content Extraction**: Uses `PruningContentFilter` for noise-free markdown
- **CTA Detection**: Automatically extracts Call-To-Action links (Apply Now, Open Account, etc.)
- **Page Classification**: Auto-categorizes pages by type (FAQ, rates, product info, etc.)
- **Polite Crawling**: Conservative concurrency (5 concurrent requests) with rate limiting
- **Structured Output**: One JSON file per page with rich metadata

## Installation

```bash
# Install Crawl4AI (already added to requirements.txt)
pip install crawl4ai>=0.9.0

# Install Playwright browsers (required by Crawl4AI)
playwright install
```

## Usage

### Dry Run (50 pages)
Test the crawler on a small subset before running the full crawl:

```bash
python -m app.crawler.crawl4ai_client --max-pages 50
```

### Full Crawl
Crawl the entire IDBI Bank website:

```bash
python -m app.crawler.crawl4ai_client
```

### BFS-Only Mode (Skip Sitemap)
Force BFS deep crawl without trying sitemap first:

```bash
python -m app.crawler.crawl4ai_client --no-sitemap --max-pages 500
```

### Quiet Mode
Suppress progress messages:

```bash
python -m app.crawler.crawl4ai_client --quiet
```

## Output Structure

### Directory: `app/kb_raw/`

Each crawled page is saved as a JSON file with this structure:

```json
{
  "url": "https://www.idbibank.in/fixed-deposit.aspx",
  "title": "Fixed Deposit - IDBI Bank",
  "content": "<cleaned fit_markdown content>",
  "category": "deposits",
  "page_type": "product_info",
  "cta_label": "Apply Now",
  "cta_url": "https://www.idbibank.in/fixed-deposit-apply.aspx",
  "content_hash": "a3f5e8...",
  "crawled_at": "2024-01-15T10:30:45.123Z",
  "metadata": {
    "description": "IDBI Bank Fixed Deposit offers...",
    "keywords": "fixed deposit, FD, interest rates",
    "word_count": 1250,
    "internal_links_count": 15,
    "external_links_count": 2
  }
}
```

### Manifest: `app/kb_raw/crawl_manifest.json`

Summary of the crawl session:

```json
{
  "crawl_timestamp": "2024-01-15T10:30:45.123Z",
  "domain": "www.idbibank.in",
  "discovery_method": "sitemap+bfs",
  "urls_discovered": 450,
  "pages_crawled": 425,
  "pages_failed": 15,
  "pages_skipped": 10,
  "crawled_pages": [
    {
      "url": "https://www.idbibank.in/fixed-deposit.aspx",
      "file": "fixed-deposit-aspx_a3f5e8.json",
      "category": "deposits",
      "page_type": "product_info"
    }
  ],
  "failed_urls": [],
  "skipped_urls": []
}
```

## Configuration

Edit `crawl4ai_client.py` to adjust:

- `CONCURRENCY`: Number of concurrent requests (default: 5)
- `MAX_DEPTH_BFS`: BFS crawl depth (default: 3)
- `SITEMAP_THRESHOLD`: Minimum URLs from sitemap before BFS fallback (default: 100)
- `SKIP_PATTERNS`: URLs to exclude (login, auth, PDFs, etc.)
- `CTA_PATTERNS`: Patterns for detecting Call-To-Action links

## URL Discovery Strategy

1. **Sitemap-First** (default):
   - Tries to discover URLs from `https://www.idbibank.in/sitemap.aspx`
   - Fast: discovers hundreds of URLs in seconds
   - If sitemap yields < 100 URLs, falls back to BFS

2. **BFS Fallback**:
   - Bounded Breadth-First Search crawl
   - `max_depth=3`: Crawls 3 levels deep from homepage
   - `max_pages=1500`: Hard cap to prevent infinite crawl
   - Domain-locked to `www.idbibank.in`

## Exclusion Rules

The crawler **never** accesses:

- Login/authentication pages (`*/login/*`, `*/netbanking/*`, `*/otp/*`)
- Account dashboards (`*/account/*`, `*/dashboard/*`)
- External banking portals (`ebanking.*`, `corp.*`, `secureonline*`)
- Non-HTML files (`.pdf`, `.zip`, `.doc`, `.xls`, etc.)

These are **hard exclusions** enforced by `FilterChain`, not post-crawl filters.

## Content Filtering

Uses `PruningContentFilter` from Crawl4AI:

- **Dynamic threshold** (0.45): Adapts to page structure
- **Min word threshold** (10): Skips nodes with < 10 words
- Removes navigation, footers, cookie banners automatically
- Output: Clean `fit_markdown` ready for RAG ingestion

## Page Classification

### Categories (URL/title-based)
- `deposits`: FD, savings, recurring deposits
- `loans`: Home loan, personal loan, vehicle loan
- `cards`: Credit cards, debit cards
- `insurance`: Insurance products, policies
- `investments`: Mutual funds, SIP, gold
- `digital_banking`: Internet banking, mobile banking
- `nri`: NRI banking services
- `corporate`: Corporate/business banking
- `general`: Catch-all for unclassified pages

### Page Types (Content-based)
- `faq`: FAQ pages
- `rates`: Interest rates, charges, fees
- `product_info`: Product pages with "Apply Now" CTAs
- `calculator`: EMI calculators, financial tools
- `forms`: Download forms, application forms
- `contact`: Contact us, branch locator
- `general`: Other content

## Performance Characteristics

- **Concurrency**: 5 parallel requests (polite, bank-friendly)
- **Rate Limiting**: 0.5-1.0 second delay between requests
- **Speed**: ~100-150 pages in 5-10 minutes (depends on page complexity)
- **Resource Usage**: Moderate (Playwright browser instances)

## Next Steps

After running the crawler:

1. **Review Sample Output**:
   ```bash
   # Check manifest
   cat app/kb_raw/crawl_manifest.json
   
   # View 2-3 sample JSON files
   ls app/kb_raw/*.json | head -3 | xargs -I {} cat {}
   ```

2. **Validate Content Quality**:
   - Verify `fit_markdown` is clean (no nav/footer noise)
   - Check CTA detection accuracy
   - Confirm page_type classification makes sense

3. **Build Ingestion Pipeline**:
   - Create new `app/rag/ingest_crawl4ai.py`
   - Consume `app/kb_raw/*.json` files
   - Replace current markdown-based ingestion
   - Build BM25 index from structured JSON

## Troubleshooting

### Playwright Installation Issues
```bash
# Reinstall Playwright browsers
playwright install --force chromium
```

### Rate Limiting / 429 Errors
- Reduce `CONCURRENCY` from 5 to 3
- Increase `REQUEST_DELAY` from (0.5, 1.0) to (1.0, 2.0)

### Empty fit_markdown
- Lower PruningContentFilter threshold from 0.45 to 0.35
- Check if page is JavaScript-heavy (Crawl4AI uses Playwright, should handle JS)

### Authentication Blocks
- Verify exclusion patterns are working
- Check `failed_urls` in manifest for auth-related failures
- Add new patterns to `SKIP_PATTERNS` if needed

## Comparison: Old Scraper vs Crawl4AI

| Feature | Old (BeautifulSoup) | New (Crawl4AI) |
|---------|---------------------|----------------|
| JavaScript Support | ❌ No | ✅ Yes (Playwright) |
| Content Cleaning | Manual regex | ✅ PruningContentFilter |
| Link Extraction | Manual parsing | ✅ Auto-categorized |
| CTA Detection | ❌ None | ✅ Pattern-based |
| Page Classification | ❌ None | ✅ Auto-categorized |
| Rate Limiting | Manual delays | ✅ Built-in |
| Concurrency | Sequential | ✅ Parallel (arun_many) |
| Structured Output | Markdown files | ✅ Rich JSON |
| Incremental Updates | ❌ No | 🔄 Future (content_hash) |

## Future Enhancements

1. **Incremental Crawling**: Use `content_hash` to detect changed pages
2. **Scheduled Crawls**: Cron job to refresh knowledge base weekly
3. **PDF Extraction**: Integrate Crawl4AI's PDF parsing for bank documents
4. **LLM-Based Classification**: Use LLM for more accurate page_type classification
5. **Link Scoring**: Leverage `LinkPreviewConfig` for better CTA detection
6. **Content Versioning**: Track changes over time for compliance/audit

## License

Part of IDBI AI Wealth Engine project.
