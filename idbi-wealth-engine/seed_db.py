import json
import os
import sys
from datetime import datetime

# Adjust path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import db, Lead, MiningSignal, AuditLog, CustomerGoal, RiskProfile
from app.core.mining import analyze_spending_pattern, detect_life_events, assign_cohort
from app.core.suitability import check_suitability

def seed():
    print("Initializing Database...")
    db.init_db()
    session = db.get_session()
    
    # Clear existing tables to ensure a clean slate
    session.query(Lead).delete()
    session.query(MiningSignal).delete()
    session.query(AuditLog).delete()
    session.query(CustomerGoal).delete()
    session.query(RiskProfile).delete()
    session.commit()
    
    profiles_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'profiles')
    profile_files = ['rahul_salaried.json', 'young_investor.json', 'business_owner.json', 'retired_person.json']
    
    print("Processing and seeding profiles...")
    for filename in profile_files:
        filepath = os.path.join(profiles_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: {filename} not found, skipping.")
            continue
            
        with open(filepath, 'r') as f:
            profile = json.load(f)
            
        customer_id = profile['profile_id']
        print(f"Seeding customer: {profile['name']} ({customer_id})")
        
        # 1. Seed RiskProfile
        rp = RiskProfile(
            customer_id=customer_id,
            risk_category=profile.get('risk_profile', {}).get('risk_category', 'Moderate'),
            questionnaire_answers=profile.get('risk_profile', {}).get('questionnaire_answers', {}),
            language_preference=profile.get('language_preference', 'English'),
            profile_updated_at=datetime.utcnow()
        )
        session.add(rp)
        
        # 2. Seed CustomerGoals
        for goal in profile.get('goals', []):
            cg = CustomerGoal(
                customer_id=customer_id,
                goal_name=goal.get('name'),
                target_amount=goal.get('target_amount'),
                target_date=goal.get('target_date'),
                current_savings=goal.get('current_savings', 0),
                monthly_contribution=goal.get('monthly_contribution', 0),
                priority=goal.get('priority', 'medium'),
                status='active'
            )
            session.add(cg)
            
        # 3. Compute and Seed MiningSignals
        transactions = profile.get('transactions', [])
        spend_analysis = analyze_spending_pattern(customer_id, transactions)
        
        # Spend analysis signal
        session.add(MiningSignal(
            customer_id=customer_id,
            signal_type='spend_analysis',
            signal_value=spend_analysis,
            computed_at=datetime.utcnow()
        ))
        
        # Life events signal
        life_events = detect_life_events(customer_id, transactions, profile)
        session.add(MiningSignal(
            customer_id=customer_id,
            signal_type='life_events',
            signal_value=life_events,
            computed_at=datetime.utcnow()
        ))
        
        # Cohort signal
        cohort = assign_cohort(profile)
        session.add(MiningSignal(
            customer_id=customer_id,
            signal_type='cohort_assignment',
            signal_value={'cohort': cohort, 'assigned_at': datetime.utcnow().isoformat()},
            computed_at=datetime.utcnow()
        ))
        
        # Product suitability signals (pre-computes for popular options)
        # Let's seed pre-computed leads for demo personas
        if customer_id == 'rahul_001':
            # Create a pending Mutual Fund lead
            suit_res = check_suitability("Equity SIP — Flexi-cap", profile, spend_analysis, profile.get('goals', [None])[0])
            session.add(Lead(
                customer_id=customer_id,
                product_name="Equity SIP — Flexi-cap",
                product_type="Equity Mutual Fund",
                tier='B',
                recommended_amount=10000,
                suitability_trail=suit_res['suitability_trail'],
                status='pending',
                priority_score=75,
                assigned_rm=None,
                rm_notes=None
            ))
            
            # Create a converted Life Insurance lead
            suit_res_ins = check_suitability("Life Insurance Plan", profile, spend_analysis, None)
            session.add(Lead(
                customer_id=customer_id,
                product_name="Life Insurance Plan",
                product_type="Life Insurance",
                tier='B',
                recommended_amount=5000,
                suitability_trail=suit_res_ins['suitability_trail'],
                status='converted',
                priority_score=60,
                assigned_rm="RM Sharma",
                rm_notes="Closed successfully. Policy issued."
            ))
            
        elif customer_id == 'priya_002':
            # Create a pending Gold Bond lead
            suit_res = check_suitability("Sovereign Gold Bond", profile, spend_analysis, profile.get('goals', [None])[0])
            session.add(Lead(
                customer_id=customer_id,
                product_name="Sovereign Gold Bond",
                product_type="Sovereign Gold Bond",
                tier='B',
                recommended_amount=7000,
                suitability_trail=suit_res['suitability_trail'],
                status='pending',
                priority_score=65,
                assigned_rm=None,
                rm_notes=None
            ))
            
        elif customer_id == 'vikram_003':
            # High priority lead for HNI
            suit_res = check_suitability("Corporate Bond Fund", profile, spend_analysis, profile.get('goals', [None])[0])
            session.add(Lead(
                customer_id=customer_id,
                product_name="Corporate Bond Fund",
                product_type="Corporate Bond",
                tier='B',
                recommended_amount=30000,
                suitability_trail=suit_res['suitability_trail'],
                status='pending',
                priority_score=90,
                assigned_rm=None,
                rm_notes=None
            ))
            
        elif customer_id == 'meena_004':
            # Pension scheme lead
            suit_res = check_suitability("National Pension Scheme", profile, spend_analysis, profile.get('goals', [None])[0])
            session.add(Lead(
                customer_id=customer_id,
                product_name="National Pension Scheme",
                product_type="National Pension Scheme (NPS)",
                tier='B',
                recommended_amount=8000,
                suitability_trail=suit_res['suitability_trail'],
                status='pending',
                priority_score=80,
                assigned_rm=None,
                rm_notes=None
            ))
            
    # Seed a cohort benchmark signal
    session.add(MiningSignal(
        customer_id='system',
        signal_type='cohort_benchmark',
        signal_value={
            'cohort': 'mass_20s_50-100k',
            'member_count': 45,
            'avg_savings_rate': 28.5,
            'avg_investment_ratio': 18.2,
            'median_balance': 150000
        },
        computed_at=datetime.utcnow()
    ))
    session.add(MiningSignal(
        customer_id='system',
        signal_type='cohort_benchmark',
        signal_value={
            'cohort': 'mass_20s_<50k',
            'member_count': 82,
            'avg_savings_rate': 12.0,
            'avg_investment_ratio': 8.5,
            'median_balance': 45000
        },
        computed_at=datetime.utcnow()
    ))
    session.add(MiningSignal(
        customer_id='system',
        signal_type='cohort_benchmark',
        signal_value={
            'cohort': 'hni_40s_200k+',
            'member_count': 14,
            'avg_savings_rate': 48.0,
            'avg_investment_ratio': 55.4,
            'median_balance': 2400000
        },
        computed_at=datetime.utcnow()
    ))
    session.add(MiningSignal(
        customer_id='system',
        signal_type='cohort_benchmark',
        signal_value={
            'cohort': 'mass_60s_50-100k',
            'member_count': 23,
            'avg_savings_rate': 35.4,
            'avg_investment_ratio': 75.0,
            'median_balance': 950000
        },
        computed_at=datetime.utcnow()
    ))

    session.commit()
    print("Database successfully seeded! Seed records created for leads, goals, and signals.")
    session.close()

if __name__ == '__main__':
    seed()
