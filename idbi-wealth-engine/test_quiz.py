"""
Test script for Goal Discovery Quiz system
Tests all quiz endpoints with sample data
"""

import requests
import json
from pprint import pprint

BASE_URL = "http://localhost:8000/api"

def test_quiz_flow():
    """Test complete quiz flow"""
    
    print("\n" + "="*60)
    print("GOAL DISCOVERY QUIZ - TEST FLOW")
    print("="*60)
    
    # Step 1: Get quiz questions
    print("\n1. Getting quiz questions structure...")
    response = requests.get(f"{BASE_URL}/quiz/questions")
    if response.status_code == 200:
        print("✓ Quiz questions retrieved successfully")
        questions = response.json()
        print(f"  Quiz version: {questions['version']}")
        print(f"  Number of steps: {len(questions['steps'])}")
    else:
        print(f"✗ Error: {response.status_code}")
        return
    
    # Step 2: Check quiz status for a customer
    print("\n2. Checking quiz status for rahul_001...")
    session_id = "test_session_rahul"
    
    # First, create a session
    session_response = requests.post(
        f"{BASE_URL}/session/select",
        json={"profile_id": "rahul_001"}
    )
    
    if session_response.status_code == 200:
        session_data = session_response.json()
        session_id = session_data['session_id']
        print(f"✓ Session created: {session_id}")
    
    status_response = requests.get(
        f"{BASE_URL}/quiz/status",
        params={"session_id": session_id}
    )
    
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"✓ Quiz status retrieved")
        print(f"  Quiz completed: {status['quiz_completed']}")
        print(f"  Needs refresh: {status['needs_refresh']}")
    else:
        print(f"✗ Error: {status_response.status_code}")
    
    # Step 3: Submit a complete quiz
    print("\n3. Submitting quiz for rahul_001...")
    
    quiz_submission = {
        "customer_id": "rahul_001",
        "step1": {
            "life_stage": "building_wealth",
            "priorities": ["home_purchase", "children_education", "emergency_fund"],
            "dependents": "kids",
            "income_stability": "fixed",
            "health_insurance": "employer_only",
            "emergency_source": "savings"
        },
        "step2": {
            "goals": [
                {
                    "goal_type": "home_purchase",
                    "timeline": "3_5_years",
                    "target_amount": 2500000,
                    "current_savings": 300000,
                    "priority": 1
                },
                {
                    "goal_type": "children_education",
                    "timeline": "5_10_years",
                    "target_amount": 1000000,
                    "current_savings": 0,
                    "priority": 2
                },
                {
                    "goal_type": "emergency_fund",
                    "timeline": "1_3_years",
                    "target_amount": 500000,
                    "current_savings": 150000,
                    "priority": 3
                }
            ]
        },
        "step3": {
            "investment_preference": "balanced_mf",
            "volatility_tolerance": "stay_calm",
            "prior_experience": "little",
            "capacity_loss_tolerance": "manage"
        }
    }
    
    submit_response = requests.post(
        f"{BASE_URL}/quiz/submit",
        json=quiz_submission
    )
    
    if submit_response.status_code == 200:
        print("✓ Quiz submitted successfully")
        quiz_data = submit_response.json()
        
        print("\n  QUIZ RESULTS:")
        print(f"  Life Stage: {quiz_data['life_stage']}")
        print(f"  Priorities: {', '.join(quiz_data['priorities'])}")
        
        print("\n  RISK PROFILE:")
        risk = quiz_data['risk_profile']
        print(f"  Category: {risk['risk_category']}")
        print(f"  Risk Score: {risk['risk_score']}/100")
        print(f"  Explanation: {risk['explanation']}")
        
        print("\n  GOALS:")
        for idx, goal in enumerate(quiz_data['goals'], 1):
            print(f"\n  Goal {idx}: {goal['goal_name']}")
            print(f"    Target: ₹{goal['target_amount']:,}" if goal['target_amount'] else "    Target: TBD")
            print(f"    Target Date: {goal['target_date']}")
            print(f"    Current Savings: ₹{goal['current_savings']:,}")
            print(f"    Recommended Monthly: ₹{goal['monthly_contribution']:,}")
            print(f"    Priority: {goal['priority']}")
        
        print("\n  NEW STATISTICS:")
        stats = quiz_data['new_stats']
        print(f"    Total Target Amount: ₹{stats['total_target_amount']:,}")
        print(f"    Total Current Savings: ₹{stats['total_current_savings']:,}")
        print(f"    Total Monthly Needed: ₹{stats['total_monthly_contribution_needed']:,}")
        print(f"    Goal Coverage Ratio: {stats['goal_coverage_ratio']}%")
        print(f"    Savings Velocity: {stats['savings_velocity']}%")
        print(f"    Multi-Goal Conflict Index: {stats['multi_goal_conflict_index']}%")
        print(f"    Risk-Goal Mismatch: {stats['risk_goal_mismatch_alert']}")
        print(f"    Monthly Surplus/Deficit: ₹{stats['monthly_savings_surplus_deficit']:,}")
        
        print("\n    Goal Urgency Scores:")
        for goal_id, score in stats['goal_urgency_scores'].items():
            print(f"      {goal_id}: {score}/100")
        
    else:
        print(f"✗ Error submitting quiz: {submit_response.status_code}")
        print(submit_response.text)
        return
    
    # Step 4: Retrieve stored quiz response
    print("\n4. Retrieving stored quiz response...")
    
    get_response = requests.get(
        f"{BASE_URL}/quiz/response",
        params={"session_id": session_id}
    )
    
    if get_response.status_code == 200:
        print("✓ Quiz response retrieved successfully")
        stored_data = get_response.json()
        print(f"  Customer: {stored_data['customer_id']}")
        print(f"  Completed at: {stored_data['quiz_completed_at']}")
        print(f"  Number of goals: {len(stored_data['goals'])}")
    else:
        print(f"✗ Error: {get_response.status_code}")
    
    # Step 5: Update a goal
    print("\n5. Updating a goal...")
    
    # Get first goal ID from quiz_data
    first_goal_id = quiz_data['goals'][0]['goal_id']
    
    goal_update = {
        "current_savings": 400000,
        "monthly_contribution": 18000
    }
    
    update_response = requests.put(
        f"{BASE_URL}/goals/{first_goal_id}",
        params={"session_id": session_id},
        json=goal_update
    )
    
    if update_response.status_code == 200:
        print(f"✓ Goal {first_goal_id} updated successfully")
        update_data = update_response.json()
        print(f"  New current savings: ₹{update_data['updated_goal']['current_savings']:,}")
        print(f"  New monthly contribution: ₹{update_data['updated_goal']['monthly_contribution']:,}")
    else:
        print(f"✗ Error updating goal: {update_response.status_code}")
    
    # Step 6: Check quiz status again
    print("\n6. Checking quiz status after completion...")
    
    status_response2 = requests.get(
        f"{BASE_URL}/quiz/status",
        params={"session_id": session_id}
    )
    
    if status_response2.status_code == 200:
        status = status_response2.json()
        print(f"✓ Quiz status retrieved")
        print(f"  Quiz completed: {status['quiz_completed']}")
        print(f"  Completed at: {status['quiz_completed_at']}")
        print(f"  Days since completion: {status['days_since_completion']}")
        print(f"  Needs refresh: {status['needs_refresh']}")
    
    print("\n" + "="*60)
    print("TEST COMPLETED SUCCESSFULLY ✓")
    print("="*60)


if __name__ == "__main__":
    try:
        test_quiz_flow()
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Cannot connect to API server")
        print("  Make sure the FastAPI server is running on http://localhost:8000")
        print("  Run: python -m uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
