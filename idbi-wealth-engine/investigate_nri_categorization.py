"""Investigate why nri-banking.aspx got miscategorized"""
import json
from pathlib import Path

# Load the 4 NRI pages directly from kb_raw
nri_files = [
    'apply-now-nri-aspx',
    'nri-banking-aspx', 
    'nri-interest-rates-aspx',
    'nri-newsletter-aspx'
]

kb_raw = Path('app/kb_raw')

print("="*70)
print("NRI PAGE CATEGORIZATION ANALYSIS")
print("="*70)

for filename_base in nri_files:
    # Find the actual file (has hash suffix)
    matching_files = list(kb_raw.glob(f"{filename_base}_*.json"))
    
    if not matching_files:
        print(f"\n❌ File not found: {filename_base}")
        continue
    
    filepath = matching_files[0]
    
    with open(filepath, 'r', encoding='utf-8') as f:
        page_data = json.load(f)
    
    url = page_data.get('url', '')
    title = page_data.get('title', '')
    category = page_data.get('category', '')
    
    print(f"\n{'─'*70}")
    print(f"File: {filepath.name}")
    print(f"URL: {url}")
    print(f"Title: {title[:80]}...")
    print(f"Assigned Category: {category}")
    
    # Test category matching logic
    text = f"{url} {title}".lower()
    
    # Check which patterns match
    category_patterns = {
        "deposits": [r"deposit", r"\bfd\b", r"savings", r"recurring"],
        "loans": [r"loan", r"lending", r"credit"],
        "cards": [r"credit\s+card", r"debit\s+card"],
        "insurance": [r"insurance", r"policy"],
        "investments": [r"mutual\s+fund", r"investment", r"sip", r"gold"],
        "digital_banking": [r"internet\s+banking", r"mobile\s+banking", r"online"],
        "nri": [r"\bnri\b", r"non[-\s]resident"],
        "corporate": [r"corporate", r"business", r"msme"],
        "about": [r"about\s+us", r"company", r"history"],
    }
    
    import re
    matched_categories = []
    for cat, patterns in category_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matched_categories.append(f"{cat} (pattern: {pattern})")
                break
    
    print(f"Pattern Matches: {matched_categories if matched_categories else ['None']}")
    
    # Check if "nri" appears in text
    if "nri" in text:
        print(f"✅ 'nri' DOES appear in: {text[:100]}...")
    else:
        print(f"❌ 'nri' NOT in text")

print("\n" + "="*70)
print("CATEGORY ASSIGNMENT ORDER IN infer_category()")
print("="*70)
print("""
The dict iteration order matters! First match wins:
1. deposits
2. loans
3. cards
4. insurance
5. investments
6. digital_banking
7. nri  <-- Checked 7th!
8. corporate
9. about
""")
