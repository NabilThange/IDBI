import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.mining import categorize_transaction, assign_cohort
from app.core.suitability import calculate_disposable_income, calculate_goal_required_contribution, check_suitability
from app.core.translator import translator

def test_mcc_categorization():
    print("Testing MCC categorization...")
    # Grocery Store MCC
    cat, reason = categorize_transaction({'mcc_code': 5411})
    assert cat == 'essential', f"Expected essential, got {cat}"
    assert 'MCC code 5411' in reason
    
    # Restaurant MCC
    cat, reason = categorize_transaction({'mcc_code': 5812})
    assert cat == 'discretionary', f"Expected discretionary, got {cat}"
    
    # Airline MCC
    cat, reason = categorize_transaction({'mcc_code': 4511})
    assert cat == 'luxury', f"Expected luxury, got {cat}"
    
    # Keyword fallback
    cat, reason = categorize_transaction({'description': 'Swiggy order 48329'})
    assert cat == 'discretionary', f"Expected discretionary, got {cat}"
    
    print("SUCCESS: MCC categorization works!")

def test_disposable_income():
    print("Testing disposable income math...")
    profile = {
        'financial_summary': {
            'monthly_income': 100000,
            'monthly_expenses': 40000,
            'current_balance': 300000
        }
    }
    # No analyzed essential total, falls back to profile monthly expenses
    res = calculate_disposable_income(profile, {})
    assert res['disposable_income'] == 52000, f"Expected 52000, got {res['disposable_income']}"
    # Income (100,000) - Expenses (40,000) - Buffer (20% of 40,000 = 8,000) = 52,000
    
    print("SUCCESS: Disposable income calculation is correct!")

def test_goal_projection_math():
    print("Testing TVM math...")
    # Goal: target 1,200,000 in 120 months (10 years)
    goal = {
        'goal_name': 'New House',
        'target_amount': 1200000,
        'current_savings': 200000,
        'target_date': '2036-07-02'
    }
    # Risk Profile: Moderate (10% annual return)
    res = calculate_goal_required_contribution(goal, 'Moderate')
    
    # Validate months left is around 120
    assert res['months_left'] > 0
    assert res['required_contribution'] > 0
    print(f"Goal required contribution: {res['required_contribution']} per month")
    print("SUCCESS: TVM goal progress calculation works!")

def test_suitability_tiering():
    print("Testing regulatory tiering...")
    profile = {
        'financial_summary': {
            'monthly_income': 90000,
            'monthly_expenses': 55000,
            'current_balance': 280000,
            'total_investments': 450000
        },
        'risk_profile': {'risk_category': 'Moderate'}
    }
    # 1. FD should be Tier A (Direct, requires_rm_handoff = False)
    res_fd = check_suitability("Fixed Deposit", profile, {})
    assert res_fd['tier'] == 'A', f"Expected Tier A for FD, got {res_fd['tier']}"
    assert res_fd['requires_rm_handoff'] is False
    
    # 2. Equity Mutual Fund should be Tier B (Lead-Gen, requires_rm_handoff = True)
    res_mf = check_suitability("Equity Mutual Fund", profile, {})
    assert res_mf['tier'] == 'B', f"Expected Tier B for Mutual Fund, got {res_mf['tier']}"
    assert res_mf['requires_rm_handoff'] is True
    
    print("SUCCESS: Regulatory tiering rules are enforced!")

def test_localization():
    print("Testing multi-language translation...")
    # Test dictionary-based Hindi translation
    res_hindi = translator.translate_text('essential', 'Hindi')
    assert res_hindi == 'आवश्यक', f"Expected आवश्यक, got {res_hindi}"
    
    # Test dictionary-based Marathi translation
    res_marathi = translator.translate_text('Invest Now', 'Marathi')
    assert res_marathi == 'आत्ताच गुंतवणूक करा', f"Expected आत्ताच गुंतवणूक करा, got {res_marathi}"
    
    print("SUCCESS: Localization translation is correct!")

if __name__ == '__main__':
    print("Running backend tests...")
    test_mcc_categorization()
    test_disposable_income()
    test_goal_projection_math()
    test_suitability_tiering()
    test_localization()
    print("ALL TESTS PASSED SUCCESSFULLY!")
