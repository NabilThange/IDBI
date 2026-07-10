from datetime import datetime
from typing import List, Dict
import math

SUITABILITY_CONFIG = {
    'safety_buffer_ratio': 0.20,  # 20% of essential expenses
    'min_emergency_fund_months': 6,  # 6 months of expenses for emergency fund
}

# Assumed annual returns by risk category
RISK_RETURNS = {
    'Conservative': 0.065,  # 6.5% annual return
    'Moderate': 0.10,       # 10.0% annual return
    'Aggressive': 0.13,     # 13.0% annual return
}

# Product categories mapping to regulatory tiers
PRODUCT_TIERS = {
    # Tier A - Direct execution (unregulated or vanilla banking)
    'Savings Account': 'A',
    'Fixed Deposit': 'A',
    'Recurring Deposit': 'A',
    'Vanilla Home Loan': 'A',
    'Personal Loan': 'A',
    
    # Tier B - Lead-Gen / Regulated advisory (SEBI/IRDA/PFRDA/RBI)
    'Equity Mutual Fund': 'B',
    'Hybrid Mutual Fund': 'B',
    'Debt Mutual Fund': 'B',
    'National Pension Scheme (NPS)': 'B',
    'Life Insurance': 'B',
    'Health Insurance': 'B',
    'Sovereign Gold Bond': 'B',
    'Corporate Bond': 'B',
}

def calculate_disposable_income(profile: dict, spend_analysis: dict) -> dict:
    """
    Calculate disposable income using transaction-derived essential expenses and declared income.
    
    Returns: {
        'disposable_income': int,
        'breakdown': {
            'monthly_income': int,
            'essential_expenses': int,
            'safety_buffer': int
        },
        'trail': List[str]
    }
    """
    trail = []
    
    # Monthly income (declared)
    monthly_income = profile.get('financial_summary', {}).get('monthly_income', 0)
    trail.append(f"Income: Declared monthly income is ₹{monthly_income:,}")
    
    # Essential expenses:
    # Use analyzed essential expenses if available, otherwise fall back to declared monthly expenses
    essential_total = spend_analysis.get('category_breakdown', {}).get('essential', {}).get('total', 0)
    if essential_total > 0:
        essential_expenses = essential_total
        trail.append(f"Expenses: Mined essential expenses (rent, bills, groceries) are ₹{essential_expenses:,} from transaction logs")
    else:
        essential_expenses = profile.get('financial_summary', {}).get('monthly_expenses', 0)
        trail.append(f"Expenses: Falling back to declared monthly expenses ₹{essential_expenses:,}")
        
    # Safety buffer
    safety_buffer = int(essential_expenses * SUITABILITY_CONFIG['safety_buffer_ratio'])
    trail.append(f"Safety Buffer: Set at {int(SUITABILITY_CONFIG['safety_buffer_ratio']*100)}% of essential expenses (₹{safety_buffer:,})")
    
    # Disposable income
    disposable_income = max(0, monthly_income - essential_expenses - safety_buffer)
    trail.append(f"Disposable Income: ₹{monthly_income:,} (income) - ₹{essential_expenses:,} (essentials) - ₹{safety_buffer:,} (buffer) = ₹{disposable_income:,}")
    
    return {
        'disposable_income': disposable_income,
        'breakdown': {
            'monthly_income': monthly_income,
            'essential_expenses': essential_expenses,
            'safety_buffer': safety_buffer
        },
        'trail': trail
    }

def calculate_goal_required_contribution(goal: dict, risk_category: str) -> dict:
    """
    Calculate the monthly contribution required to hit a goal using Time-Value-of-Money (TVM) math.
    
    Formula: Monthly = (Target - Current) * r / ((1 + r)^N - 1)
    """
    trail = []
    goal_name = goal.get('goal_name')
    target_amount = goal.get('target_amount', 0)
    current_savings = goal.get('current_savings', 0)
    target_date_str = goal.get('target_date', '')
    
    trail.append(f"Goal: '{goal_name}' has a target of ₹{target_amount:,} with current savings of ₹{current_savings:,}")
    
    # Parse target date and find months remaining
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        now = datetime.utcnow()
        months_left = (target_date.year - now.year) * 12 + (target_date.month - now.month)
        if months_left <= 0:
            months_left = 1
    except Exception:
        months_left = 120  # Fallback to 10 years
        
    trail.append(f"Timeline: {months_left} months remaining until target date ({target_date_str})")
    
    net_needed = max(0, target_amount - current_savings)
    
    # Return rate based on risk profile
    annual_rate = RISK_RETURNS.get(risk_category, 0.08)
    monthly_rate = annual_rate / 12
    trail.append(f"Risk Return assumption: Risk category '{risk_category}' assumes annual return of {annual_rate*100:.1f}% ({monthly_rate*100:.3f}% monthly)")
    
    if net_needed <= 0:
        trail.append("Contribution: Already achieved! No additional monthly savings needed.")
        return {
            'required_contribution': 0,
            'months_left': months_left,
            'net_needed': 0,
            'trail': trail
        }
        
    # TVM Math
    # Future Value of Annuity formula: PMT = FV * r / ((1 + r)^N - 1)
    if monthly_rate > 0:
        factor = math.pow(1 + monthly_rate, months_left) - 1
        required_contribution = int((net_needed * monthly_rate) / factor)
    else:
        required_contribution = int(net_needed / months_left)
        
    trail.append(f"Contribution Math: PMT = ₹{net_needed:,} * {monthly_rate:.4f} / ((1 + {monthly_rate:.4f})^{months_left} - 1) = ₹{required_contribution:,}/month")
    
    return {
        'required_contribution': required_contribution,
        'months_left': months_left,
        'net_needed': net_needed,
        'trail': trail
    }

def check_suitability(
    product_name: str,
    profile: dict,
    spend_analysis: dict,
    selected_goal: dict = None
) -> dict:
    """
    Run suitability matching for a product against a customer's financial situation.
    
    Checks:
    1. Disposable income check.
    2. Regulatory tier assignment (Tier A vs Tier B).
    3. Emergency fund adequacy.
    4. CIBIL/Credit bureau holdings validation.
    
    Returns: {
        'product_name': str,
        'product_type': str,
        'tier': str,  # 'A' or 'B'
        'requires_rm_handoff': bool,
        'recommended_amount': int,
        'is_suitable': bool,
        'suitability_trail': List[str]
    }
    """
    trail = []
    
    # 1. Get product type
    product_type = 'unknown'
    for k, v in PRODUCT_TIERS.items():
        if k.lower() in product_name.lower():
            product_type = k
            break
            
    tier = PRODUCT_TIERS.get(product_type, 'B')  # Default to Tier B (regulated) if unknown
    requires_rm_handoff = (tier == 'B')
    
    trail.append(f"Product verification: '{product_name}' maps to type '{product_type}' under Regulatory Tier {tier}")
    if requires_rm_handoff:
        trail.append("Regulatory Constraint: This is a regulated investment/advisory product. Legal compliance requires RM handoff.")
    else:
        trail.append("Regulatory Constraint: Vanilla banking product. AI is permitted to recommend direct execution.")

    # 2. Disposable income calculations
    disposable_res = calculate_disposable_income(profile, spend_analysis)
    disposable_income = disposable_res['disposable_income']
    trail.extend(disposable_res['trail'])
    
    # 3. Emergency fund check
    current_balance = profile.get('financial_summary', {}).get('current_balance', 0)
    monthly_expenses = profile.get('financial_summary', {}).get('monthly_expenses', 0)
    emergency_target = monthly_expenses * SUITABILITY_CONFIG['min_emergency_fund_months']
    
    trail.append(f"Emergency Check: Current balance is ₹{current_balance:,} vs 6-month target of ₹{emergency_target:,}")
    
    emergency_adequate = current_balance >= emergency_target
    if not emergency_adequate and product_type in ['Equity Mutual Fund', 'Hybrid Mutual Fund', 'Debt Mutual Fund']:
        trail.append("Warning: Emergency fund is inadequate. Advising customer to prioritize liquidity (FD/RD) before market assets.")
    
    # 4. Goal Fit (if any selected)
    risk_category = profile.get('risk_profile', {}).get('risk_category', 'Moderate')
    recommended_amount = 5000  # Default baseline
    
    is_deposit = (
        'fixed deposit' in product_name.lower() or 
        'recurring deposit' in product_name.lower() or 
        'deposit' in product_name.lower() or 
        product_type in ['Fixed Deposit', 'Recurring Deposit']
    )
    
    if is_deposit:
        # Emergency/safety net top-up (FD/RD lump sum)
        expenses = profile.get('financial_summary', {}).get('monthly_expenses', 0)
        emergency_fund = profile.get('financial_summary', {}).get('emergency_fund', 0)
        coverage = round(emergency_fund / expenses, 1) if expenses > 0 else 0
        shortfall_months = max(0.0, 6.0 - coverage)
        shortfall_amount = int(shortfall_months * expenses)
        
        current_balance = profile.get('financial_summary', {}).get('current_balance', 0)
        if shortfall_amount > 0:
            # We suggest half the shortfall to keep some liquid cash in savings
            suggested = int(shortfall_amount * 0.5)
            # Cap at 50% of current balance
            suggested = min(suggested, int(current_balance * 0.5))
            # Round to nearest 5,000
            recommended_amount = max(10000, (suggested // 5000) * 5000)
        else:
            recommended_amount = 25000  # Default FD lump sum
            
        trail.append(f"Safety Net Check: Current emergency coverage is {coverage} months (Goal: 6 months). Shortfall is {shortfall_months} months or ₹{shortfall_amount:,}.")
        trail.append(f"Suitability fit: Recommending a lump sum Fixed Deposit of ₹{recommended_amount:,} to bridge the gap without depleting liquid savings.")

    elif 'mutual fund' in product_name.lower() or 'sip' in product_name.lower() or 'systematic investment plan' in product_name.lower() or 'equity' in product_name.lower() or 'debt' in product_name.lower() or product_type in ['Equity Mutual Fund', 'Hybrid Mutual Fund', 'Debt Mutual Fund']:
        # SIP / Mutual Fund monthly allocation
        monthly_savings = profile.get('financial_summary', {}).get('monthly_savings', 0)
        current_sips = sum(inv.get('monthly_amount', 0) for inv in profile.get('current_investments', []) if inv.get('type') == 'SIP')
        investable_surplus = monthly_savings - current_sips
        
        if selected_goal:
            goal_res = calculate_goal_required_contribution(selected_goal, risk_category)
            required_contribution = selected_goal.get('monthly_contribution') or goal_res['required_contribution']
            trail.extend(goal_res['trail'])
            
            if required_contribution <= investable_surplus:
                recommended_amount = required_contribution
                trail.append(f"Suitability fit: Recommended monthly allocation set to required contribution ₹{recommended_amount:,}/mo")
            else:
                recommended_amount = max(1000, investable_surplus)
                trail.append(f"Suitability fit: Required contribution (₹{required_contribution:,}) exceeds monthly surplus (₹{investable_surplus:,}). Capping recommendation at ₹{recommended_amount:,}/mo.")
        else:
            recommended_amount = max(1000, int(investable_surplus * 0.3))
            trail.append(f"Suitability fit: No specific goal linked. Recommending standard allocation of 30% of investable surplus (₹{recommended_amount:,}/mo)")
    else:
        # Default fallback
        if selected_goal:
            goal_res = calculate_goal_required_contribution(selected_goal, risk_category)
            recommended_amount = goal_res['required_contribution']
            trail.extend(goal_res['trail'])
        else:
            recommended_amount = 5000
        trail.append(f"Suitability fit: Recommended allocation set to ₹{recommended_amount:,}")

    # 5. CIBIL/Credit Bureau Holdings conflict check
    credit_bureau_data = profile.get('credit_bureau_data', {})
    external_debt = credit_bureau_data.get('total_external_debt', 0)
    if external_debt > 200000 and product_type in ['Equity Mutual Fund', 'Hybrid Mutual Fund']:
        trail.append(f"CIBIL Alert: Customer has ₹{external_debt:,} in external liabilities. Recommending high debt repayment priority over equity exposure.")
        
    is_suitable = True  # In a demo, we explain the score but let them see it
    
    return {
        'product_name': product_name,
        'product_type': product_type,
        'tier': tier,
        'requires_rm_handoff': requires_rm_handoff,
        'recommended_amount': recommended_amount,
        'is_suitable': is_suitable,
        'suitability_trail': trail
    }
