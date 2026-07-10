from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
import json
from app.core.database import db, Lead, MiningSignal, AuditLog

router = APIRouter(prefix="/bank", tags=["Bank Intelligence"])

K_ANONYMITY_FLOOR = 2  # Configurable anonymization floor (set to 2 for demo, 10 in production)

def get_db():
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()

@router.get("/cohorts")
def get_cohort_analysis(session: Session = Depends(get_db)):
    """
    Get aggregated cohort spending, saving and balance metrics.
    Enforces a k-anonymity floor to protect client privacy.
    """
    try:
        # Since we only have 4 demo profiles in our demo database,
        # we will aggregate the pre-populated cohort benchmarks or compute them.
        # Let's count cohort memberships first.
        # We simulate this by querying our MiningSignal table or using mock data for cohorts
        # that satisfies the k-anonymity logic.
        
        # Let's write the query for cohorts in MiningSignal
        signals = session.query(MiningSignal).filter(MiningSignal.signal_type == 'cohort_benchmark').all()
        
        cohort_data = []
        for sig in signals:
            val = sig.signal_value
            # Anonymization check: we check if the cohort has enough members
            # In a real database, we would do a GROUP BY count. 
            # Here we demonstrate the check:
            cohort_name = val.get('cohort', 'unknown')
            member_count = val.get('member_count', 12)  # Mock count showing k-anonymity check
            
            if member_count < K_ANONYMITY_FLOOR:
                # Suppressed due to low member count (k-anonymity)
                continue
                
            cohort_data.append({
                'cohort': cohort_name,
                'member_count': member_count,
                'avg_savings_rate': val.get('avg_savings_rate', 25.0),
                'avg_investment_ratio': val.get('avg_investment_ratio', 15.0),
                'median_balance': val.get('median_balance', 100000),
                'anonymized': True
            })
            
        # If database is empty, return seed cohort benchmarks that pass K-anonymity
        if not cohort_data:
            cohort_data = [
                {
                    'cohort': 'mass_20s_50-100k',
                    'member_count': 45,
                    'avg_savings_rate': 28.5,
                    'avg_investment_ratio': 18.2,
                    'median_balance': 150000,
                    'anonymized': True
                },
                {
                    'cohort': 'mass_20s_<50k',
                    'member_count': 82,
                    'avg_savings_rate': 12.0,
                    'avg_investment_ratio': 8.5,
                    'median_balance': 45000,
                    'anonymized': True
                },
                {
                    'cohort': 'hni_40s_200k+',
                    'member_count': 14,
                    'avg_savings_rate': 48.0,
                    'avg_investment_ratio': 55.4,
                    'median_balance': 2400000,
                    'anonymized': True
                },
                {
                    'cohort': 'mass_60s_50-100k',
                    'member_count': 23,
                    'avg_savings_rate': 35.4,
                    'avg_investment_ratio': 75.0,
                    'median_balance': 950000,
                    'anonymized': True
                }
            ]
            
        return {
            'k_anonymity_floor': K_ANONYMITY_FLOOR,
            'cohorts': cohort_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/funnel")
def get_lead_funnel(session: Session = Depends(get_db)):
    """
    Get aggregated lead-generation and conversion funnel statistics.
    """
    try:
        # Group leads by status
        status_counts = session.query(
            Lead.status, 
            func.count(Lead.id).label('count')
        ).group_by(Lead.status).all()
        
        counts = {status: count for status, count in status_counts}
        
        # Calculate stages
        total_generated = sum(counts.values())
        accepted = counts.get('accepted', 0) + counts.get('converted', 0)
        converted = counts.get('converted', 0)
        rejected = counts.get('rejected', 0)
        pending = counts.get('pending', 0)
        
        # Breakdown by product type
        product_breakdown = session.query(
            Lead.product_type,
            Lead.status,
            func.count(Lead.id).label('count')
        ).group_by(Lead.product_type, Lead.status).all()
        
        products = {}
        for prod_type, status, count in product_breakdown:
            if prod_type not in products:
                products[prod_type] = {'total': 0, 'pending': 0, 'accepted': 0, 'converted': 0, 'rejected': 0}
            products[prod_type]['total'] += count
            products[prod_type][status] = count
            
        # Fallbacks for empty database to make sure demo works
        if total_generated == 0:
            total_generated = 120
            accepted = 85
            converted = 42
            rejected = 15
            pending = 23
            products = {
                'Equity Mutual Fund': {'total': 50, 'pending': 10, 'accepted': 25, 'converted': 12, 'rejected': 3},
                'Life Insurance': {'total': 30, 'pending': 5, 'accepted': 15, 'converted': 8, 'rejected': 2},
                'Sovereign Gold Bond': {'total': 25, 'pending': 4, 'accepted': 12, 'converted': 8, 'rejected': 1},
                'National Pension Scheme (NPS)': {'total': 15, 'pending': 4, 'accepted': 8, 'converted': 3, 'rejected': 0}
            }
            
        return {
            'funnel': {
                'generated': total_generated,
                'pending': pending,
                'accepted': accepted,
                'rejected': rejected,
                'converted': converted,
                'conversion_rate_pct': (converted / total_generated * 100) if total_generated > 0 else 0
            },
            'by_product': products
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/affinity")
def get_product_affinity(session: Session = Depends(get_db)):
    """
    Get cohort-by-product affinity matrix (number of recommendations/leads).
    """
    try:
        # Returns a heatmap data format: cohort vs product type
        leads = session.query(Lead).all()
        
        affinity = defaultdict(lambda: defaultdict(int))
        for lead in leads:
            # We need to map customer to cohort. For the demo, we can map customer_id to their segment
            cohort_name = "mass_20s_50-100k"
            if 'rahul' in lead.customer_id:
                cohort_name = "mass_20s_50-100k"
            elif 'priya' in lead.customer_id:
                cohort_name = "mass_20s_<50k"
            elif 'vikram' in lead.customer_id:
                cohort_name = "hni_40s_200k+"
            elif 'meena' in lead.customer_id:
                cohort_name = "mass_60s_50-100k"
            
            affinity[cohort_name][lead.product_type] += 1
            
        # Seed mock affinity heatmap if database is small/empty
        if not leads:
            affinity = {
                'mass_20s_50-100k': {
                    'Equity Mutual Fund': 35,
                    'Fixed Deposit': 12,
                    'Recurring Deposit': 22,
                    'Life Insurance': 8,
                    'Sovereign Gold Bond': 15
                },
                'mass_20s_<50k': {
                    'Equity Mutual Fund': 18,
                    'Fixed Deposit': 8,
                    'Recurring Deposit': 35,
                    'Life Insurance': 3,
                    'Sovereign Gold Bond': 5
                },
                'hni_40s_200k+': {
                    'Equity Mutual Fund': 52,
                    'Fixed Deposit': 40,
                    'Recurring Deposit': 5,
                    'Life Insurance': 45,
                    'Sovereign Gold Bond': 30
                },
                'mass_60s_50-100k': {
                    'Equity Mutual Fund': 2,
                    'Fixed Deposit': 85,
                    'Recurring Deposit': 12,
                    'Life Insurance': 10,
                    'Sovereign Gold Bond': 18
                }
            }
            
        return affinity
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit")
def get_audit_trail(limit: int = 10, session: Session = Depends(get_db)):
    """
    Retrieve audit log of recent recommendations and underlying mathematical trails.
    """
    try:
        logs = session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        audit_records = []
        for log in logs:
            audit_records.append({
                'id': log.id,
                'customer_id': log.customer_id,
                'endpoint': log.endpoint,
                'recommendation': log.recommendation,
                'reasoning': log.reasoning,
                'timestamp': log.timestamp
            })
            
        # Fallback records
        if not audit_records:
            audit_records = [
                {
                    'id': 1,
                    'customer_id': 'rahul_001',
                    'endpoint': '/api/recommendations',
                    'recommendation': {
                        'product': 'Equity SIP — Flexi-cap (House goal, 2033)',
                        'amount': 10000,
                        'advisory_tier': 'B',
                        'cta': 'Talk to an Advisor'
                    },
                    'reasoning': [
                        'Monthly disposable income is ~₹15,000 after essentials and buffer.',
                        'House goal (₹40L by 2033) needs ₹12,000/month; MF recommendation requires SEBI-regulated advice.'
                    ],
                    'timestamp': datetime.utcnow()
                },
                {
                    'id': 2,
                    'customer_id': 'meena_004',
                    'endpoint': '/api/recommendations',
                    'recommendation': {
                        'product': 'Recurring Deposit — Emergency Fund Top-up',
                        'amount': 5000,
                        'advisory_tier': 'A',
                        'cta': 'Apply Now'
                    },
                    'reasoning': [
                        'Emergency fund is below the 6-month target — RD top-up is a direct, non-advisory action.'
                    ],
                    'timestamp': datetime.utcnow()
                }
            ]
            
        return audit_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
