import re
import json
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Tuple
from sqlalchemy import text
from app.core.database import db, MiningSignal

# ISO 18245 MCC Code Classification (subset)
MCC_CATEGORIES = {
    # Essential
    5411: "essential",  # Grocery Stores, Supermarkets
    5541: "essential",  # Service Stations (Gas)
    4900: "essential",  # Utilities - Electric, Gas, Water
    6300: "essential",  # Insurance Sales
    8011: "essential",  # Doctors, Physicians
    
    # Discretionary
    5812: "discretionary",  # Restaurants
    5814: "discretionary",  # Fast Food Restaurants
    7832: "discretionary",  # Motion Picture Theaters
    5943: "discretionary",  # Stationery, Office Supplies
    5941: "discretionary",  # Sporting Goods Stores
    5651: "discretionary",  # Family Clothing Stores
    
    # Luxury
    5944: "luxury",  # Jewelry Stores, Watches
    7011: "luxury",  # Hotels, Motels, Resorts
    4511: "luxury",  # Airlines
    7999: "luxury",  # Recreation Services
    
    # Investment/Savings
    6211: "investment",  # Securities Brokers/Dealers
    6012: "investment",  # Financial Institutions
}

# Merchant Keyword Patterns (for UPI transactions without MCC)
MERCHANT_PATTERNS = {
    "essential": [
        r"(?i)(electricity|water|gas|utility|bill)",
        r"(?i)(rent|landlord|housing)",
        r"(?i)(medical|pharmacy|hospital|doctor)",
        r"(?i)(grocery|supermarket|dmart|bigbasket)",
    ],
    "discretionary": [
        r"(?i)(zomato|swiggy|ubereats|foodpanda)",
        r"(?i)(amazon|flipkart|myntra|ajio)",
        r"(?i)(netflix|spotify|prime|hotstar)",
        r"(?i)(uber|ola|rapido)",
    ],
    "luxury": [
        r"(?i)(taj|oberoi|marriott|radisson)",
        r"(?i)(louis vuitton|gucci|prada|armani)",
        r"(?i)(bmw|mercedes|audi|porsche)",
    ],
}

# Life-event detection configuration (named constants, not magic numbers)
LIFE_EVENT_CONFIG = {
    'large_credit_multiplier': 3.0,  # Credit > 3× avg monthly expenses
    'major_withdrawal_threshold': 0.4,  # Withdrawal > 40% of current balance
    'salary_variance_tolerance': 0.10,  # ±10% variance for salary detection
    'emi_detection_min_months': 2,  # Minimum months to confirm EMI pattern
}

def categorize_transaction(transaction: dict) -> Tuple[str, str]:
    """
    Categorize a single transaction with audit trail.
    
    Returns: (category, reason)
    """
    # Try MCC code first (most reliable)
    mcc = transaction.get('mcc_code')
    if mcc:
        try:
            mcc = int(mcc)
            if mcc in MCC_CATEGORIES:
                category = MCC_CATEGORIES[mcc]
                reason = f"MCC code {mcc} = {category}"
                return category, reason
        except (ValueError, TypeError):
            pass
    
    # Fallback to merchant name pattern matching
    merchant = transaction.get('description', '')
    for category, patterns in MERCHANT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, merchant):
                reason = f"Merchant pattern match: {pattern}"
                return category, reason
    
    return 'unknown', "No matching MCC or merchant pattern"

def detect_recurring_transactions(transactions: List[dict], tolerance: float = 0.15) -> List[dict]:
    """
    Detect recurring transactions (subscriptions, EMIs, rent).
    
    Args:
        transactions: List of transaction dicts
        tolerance: Amount variance tolerance (15% default)
    
    Returns:
        List of recurring transaction groups
    """
    # Group by (merchant, ~amount)
    groups = defaultdict(list)
    
    for txn in transactions:
        merchant = txn.get('description', '').lower().strip()
        amount = abs(txn.get('amount', 0))
        
        # Round amount to nearest 100 for grouping
        amount_bucket = round(amount / 100) * 100
        key = (merchant, amount_bucket)
        groups[key].append(txn)
    
    # Identify recurring patterns (appears in >=2 consecutive months)
    recurring = []
    
    for (merchant, amount_bucket), txns in groups.items():
        if len(txns) < 2:
            continue
            
        # Sort by date
        sorted_txns = sorted(txns, key=lambda t: t.get('date', ''))
        dates = []
        for t in sorted_txns:
            try:
                dates.append(datetime.fromisoformat(t['date'].replace('Z', '+00:00')))
            except Exception:
                pass
        
        if len(dates) < 2:
            continue
            
        # Check for consecutive months
        for i in range(len(dates) - 1):
            month_delta = (dates[i+1].year - dates[i].year) * 12 + (dates[i+1].month - dates[i].month)
            if month_delta == 1:
                recurring.append({
                    'merchant': merchant,
                    'amount': amount_bucket,
                    'frequency': 'monthly',
                    'count': len(txns),
                    'category': categorize_transaction(txns[0])[0],
                    'first_seen': dates[0].isoformat(),
                    'last_seen': dates[-1].isoformat()
                })
                break
    
    return recurring

def analyze_spending_pattern(customer_id: str, transactions: List[dict]) -> Dict:
    """
    Complete spending analysis for a customer.
    
    Returns: Structured spending breakdown with audit trail
    """
    categories = {
        'essential': [],
        'discretionary': [],
        'luxury': [],
        'investment': [],
        'unknown': []
    }
    
    total_debit = 0
    
    # Categorize each transaction
    for txn in transactions:
        if txn.get('type') == 'debit':
            amount = abs(txn.get('amount', 0))
            total_debit += amount
            
            category, reason = categorize_transaction(txn)
            categories[category].append({
                'date': txn.get('date'),
                'description': txn.get('description'),
                'amount': amount,
                'reason': reason
            })
    
    # Calculate percentages
    summary = {}
    for cat, txns in categories.items():
        cat_total = sum(t['amount'] for t in txns)
        summary[cat] = {
            'total': cat_total,
            'percentage': (cat_total / total_debit * 100) if total_debit > 0 else 0,
            'count': len(txns)
        }
    
    # Detect recurring transactions
    recurring = detect_recurring_transactions(transactions)
    
    return {
        'customer_id': customer_id,
        'total_spending': total_debit,
        'category_breakdown': summary,
        'recurring_transactions': recurring,
        'computed_at': datetime.utcnow().isoformat()
    }

def detect_life_events(
    customer_id: str,
    transactions: List[dict],
    profile: dict
) -> List[dict]:
    """
    Detect significant life events from transaction patterns.
    
    All thresholds are relative to customer's own baseline metrics.
    
    Returns: List of detected events with full explanations
    """
    events = []
    
    # Extract baseline metrics
    monthly_income = profile.get('financial_summary', {}).get('monthly_income', 0)
    monthly_expenses = profile.get('financial_summary', {}).get('monthly_expenses', 0)
    current_balance = profile.get('financial_summary', {}).get('current_balance', 0)
    
    # 1. Salary Credit Detection
    recurring_credits = detect_recurring_transactions(
        [t for t in transactions if t.get('type') == 'credit']
    )
    
    for rec in recurring_credits:
        variance = abs(rec['amount'] - monthly_income) / monthly_income if monthly_income > 0 else 1
        if variance < LIFE_EVENT_CONFIG['salary_variance_tolerance']:
            events.append({
                'type': 'salary_credit',
                'amount': rec['amount'],
                'explanation': f"Recurring monthly credit ₹{rec['amount']:,} matches declared salary (±{int(variance*100)}% variance)",
                'confidence': 'high',
                'merchant': rec['merchant'],
                'frequency': rec['frequency']
            })
            
            # Detect salary increase
            if rec['amount'] > monthly_income * 1.1:  # >10% increase
                events.append({
                    'type': 'salary_increase',
                    'old_amount': monthly_income,
                    'new_amount': rec['amount'],
                    'increase_pct': ((rec['amount'] - monthly_income) / monthly_income * 100),
                    'explanation': f"Salary increased from ₹{monthly_income:,} to ₹{rec['amount']:,} ({((rec['amount'] - monthly_income) / monthly_income * 100):.1f}% increase)",
                    'confidence': 'high'
                })
    
    # 2. Large Lump-Sum Credit
    threshold = monthly_expenses * LIFE_EVENT_CONFIG['large_credit_multiplier']
    
    for txn in transactions:
        if txn.get('type') == 'credit':
            amount = abs(txn.get('amount', 0))
            if amount > threshold:
                events.append({
                    'type': 'large_credit',
                    'amount': amount,
                    'explanation': f"Credit ₹{amount:,} exceeds {LIFE_EVENT_CONFIG['large_credit_multiplier']}× monthly expenses (₹{monthly_expenses:,})",
                    'confidence': 'medium',
                    'date': txn.get('date'),
                    'description': txn.get('description')
                })
    
    # 3. New Loan/EMI Pattern
    current_emis = detect_recurring_transactions(
        [t for t in transactions if 'loan' in t.get('category', '').lower() or 'emi' in t.get('description', '').lower() or t.get('category') == 'emi']
    )
    
    declared_loans = profile.get('loans', [])
    declared_emi_amounts = set(loan.get('emi_amount', 0) for loan in declared_loans)
    
    for emi in current_emis:
        # Round for comparison (tolerance for small differences)
        emi_amount_rounded = round(emi['amount'] / 100) * 100
        
        if emi_amount_rounded not in declared_emi_amounts:
            events.append({
                'type': 'new_loan',
                'amount': emi['amount'],
                'explanation': f"New recurring EMI ₹{emi['amount']:,}/month detected, not in existing loan profile",
                'confidence': 'high',
                'merchant': emi['merchant'],
                'first_seen': emi['first_seen']
            })
    
    # 4. Major Withdrawal
    withdrawal_threshold = current_balance * LIFE_EVENT_CONFIG['major_withdrawal_threshold']
    
    for txn in transactions:
        if txn.get('type') == 'debit':
            amount = abs(txn.get('amount', 0))
            if amount > withdrawal_threshold:
                pct = (amount / current_balance * 100) if current_balance > 0 else 0
                events.append({
                    'type': 'major_withdrawal',
                    'amount': amount,
                    'explanation': f"Withdrawal ₹{amount:,} is {pct:.1f}% of current balance (₹{current_balance:,}), exceeds {int(LIFE_EVENT_CONFIG['major_withdrawal_threshold']*100)}% threshold",
                    'confidence': 'high',
                    'date': txn.get('date'),
                    'description': txn.get('description')
                })
    
    # 5. Credit Card Detection (new account)
    for txn in transactions:
        desc = txn.get('description', '').lower()
        if 'credit card' in desc and txn.get('type') == 'debit':
            events.append({
                'type': 'credit_card_detected',
                'explanation': f"Credit card payment detected: {txn.get('description')}",
                'confidence': 'medium',
                'date': txn.get('date')
            })
    
    return events

def assign_cohort(profile: dict) -> str:
    """
    Assign customer to a cohort using explicit business rules.
    
    Cohort format: {segment}_{age_decade}_{income_bracket}
    Example: "mass_20s_50-100k"
    """
    # Segment determination
    aum = profile['financial_summary'].get('total_investments', 0) + profile['financial_summary'].get('current_balance', 0)
    is_nri = profile.get('metadata', {}).get('nri_status', False)
    
    if is_nri:
        segment = "nri"
    elif aum >= 1000000:  # ₹10L+ = HNI threshold (tunable constant)
        segment = "hni"
    else:
        segment = "mass"
    
    # Age decade
    age = profile.get('age', 30)
    age_decade = f"{(age // 10) * 10}s"  # "20s", "30s", etc.
    
    # Income bracket
    income = profile['financial_summary'].get('monthly_income', 0)
    if income < 50000:
        income_bracket = "<50k"
    elif income < 100000:
        income_bracket = "50-100k"
    elif income < 200000:
        income_bracket = "100-200k"
    else:
        income_bracket = "200k+"
    
    return f"{segment}_{age_decade}_{income_bracket}"

def get_cohort_benchmarks(cohort: str) -> dict:
    """
    Retrieve aggregate benchmarks for a cohort from SQLite mining_signals.
    
    Returns: {avg_savings_rate, avg_investment_ratio, median_balance}
    """
    session = db.get_session()
    try:
        # Query pre-computed aggregates from mining_signals table
        result = session.query(MiningSignal).filter(
            MiningSignal.signal_type == 'cohort_benchmark',
            text("json_extract(signal_value, '$.cohort') = :cohort")
        ).params(cohort=cohort).order_by(MiningSignal.computed_at.desc()).first()
        
        if result:
            return result.signal_value
    except Exception:
        pass
    finally:
        session.close()
    
    # Default fallbacks per segment
    if cohort.startswith("hni"):
        return {
            'cohort': cohort,
            'avg_savings_rate': 45.0,
            'avg_investment_ratio': 60.0,
            'median_balance': 1500000
        }
    elif cohort.startswith("nri"):
        return {
            'cohort': cohort,
            'avg_savings_rate': 35.0,
            'avg_investment_ratio': 40.0,
            'median_balance': 800000
        }
    else:
        return {
            'cohort': cohort,
            'avg_savings_rate': 25.0,
            'avg_investment_ratio': 15.0,
            'median_balance': 120000
        }

def analyze_geolocation(transactions: List[dict]) -> dict:
    """
    Analyze transaction geography from merchant location (card/POS only).
    
    CAVEAT: This assumes merchant_city field exists on card transactions.
    UPI/NEFT transactions do NOT have geolocation in real banking data.
    """
    # Filter to card/POS transactions only
    card_txns = [t for t in transactions if t.get('transaction_type') in ['card', 'pos']]
    
    if not card_txns:
        return {'available': False, 'reason': 'No card/POS transactions with location data'}
    
    # Count transactions by city
    city_counts = defaultdict(int)
    for txn in card_txns:
        city = txn.get('merchant_city', 'Unknown')
        city_counts[city] += 1
    
    total = sum(city_counts.values())
    
    return {
        'available': True,
        'primary_city': max(city_counts.items(), key=lambda x: x[1])[0],
        'city_distribution': {city: count/total for city, count in city_counts.items()},
        'cross_city_transactions': len(city_counts) > 1
    }
