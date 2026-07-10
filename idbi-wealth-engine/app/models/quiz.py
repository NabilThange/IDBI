"""
Pydantic models for Goal Discovery Quiz
Defines request/response schemas for the quiz system
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class QuizAnswerStep1(BaseModel):
    """Step 1: Life Stage & Priorities"""
    life_stage: str = Field(..., description="Customer's current life stage")
    priorities: List[str] = Field(..., description="Top 3 financial priorities", min_items=1, max_items=3)
    dependents: str = Field('nobody', description="Who depends on you financially: nobody, spouse, kids, parents, multiple")
    income_stability: str = Field('fixed', description="Income steadiness: fixed, commission, business, mixed")
    health_insurance: str = Field('employer_only', description="Health insurance coverage: own_cover, employer_only, no_cover, not_sure")
    emergency_source: str = Field('savings', description="Emergency fund source: savings, sell_investments, borrow")


class GoalDetail(BaseModel):
    """Individual goal details from Step 2"""
    goal_type: str = Field(..., description="Type of goal (e.g., home_purchase, children_education)")
    timeline: str = Field(..., description="When to achieve: within_1_year, 1_3_years, 3_5_years, 5_10_years, 10_plus_years, ongoing")
    target_amount: Optional[int] = Field(None, description="Target amount in INR", ge=0)
    current_savings: int = Field(0, description="Rupees saved so far toward this goal", ge=0)
    priority: int = Field(..., description="Priority order (1=highest)", ge=1, le=3)
    
    @validator('target_amount')
    def validate_target_amount(cls, v, values):
        """Target amount is required unless timeline is ongoing"""
        if values.get('timeline') != 'ongoing' and v is None:
            raise ValueError('Target amount is required for goals with fixed timeline')
        return v


class QuizAnswerStep2(BaseModel):
    """Step 2: Specific Goals"""
    goals: List[GoalDetail] = Field(..., description="List of customer goals", min_items=1, max_items=3)


class QuizAnswerStep3(BaseModel):
    """Step 3: Risk Profile"""
    investment_preference: str = Field(..., description="Investment preference from scenario")
    volatility_tolerance: str = Field(..., description="Response to market volatility")
    prior_experience: str = Field('never', description="Prior investment experience: never, little, regular")
    capacity_loss_tolerance: str = Field('manage', description="Reaction if goal fund drops when needed: manage, setback")


class QuizSubmission(BaseModel):
    """Complete quiz submission combining all steps"""
    customer_id: str = Field(..., description="Customer/profile ID")
    step1: QuizAnswerStep1
    step2: QuizAnswerStep2
    step3: QuizAnswerStep3


class ComputedGoal(BaseModel):
    """Goal with computed fields after quiz processing"""
    goal_id: str
    goal_type: str
    goal_name: str
    name: Optional[str] = None
    target_amount: Optional[int]
    target_date: Optional[str]  # YYYY-MM-DD format
    current_savings: int
    monthly_contribution: int
    priority: int
    timeline_category: str
    status: str = "active"

    @validator('name', always=True)
    def populate_name(cls, v, values):
        if v is None and 'goal_name' in values:
            return values['goal_name']
        return v


class RiskProfileComputed(BaseModel):
    """Computed risk profile from quiz answers"""
    risk_category: str  # Conservative, Moderate, Aggressive
    risk_score: int  # 0-100
    investment_preference: str
    volatility_tolerance: str
    explanation: str


class QuizResponseData(BaseModel):
    """Complete processed quiz response"""
    customer_id: str
    quiz_version: str = "v1.0"
    life_stage: str
    priorities: List[str]
    dependents: str = 'nobody'
    income_stability: str = 'fixed'
    health_insurance: str = 'employer_only'
    emergency_source: str = 'savings'
    prior_experience: str = 'never'
    capacity_loss_tolerance: str = 'manage'
    goals: List[ComputedGoal]
    risk_profile: RiskProfileComputed
    quiz_completed_at: str
    new_stats: Dict[str, Any]  # Additional computed statistics


class QuizStatusResponse(BaseModel):
    """Quiz status check response"""
    customer_id: str
    quiz_completed: bool
    quiz_completed_at: Optional[str]
    needs_refresh: bool
    days_since_completion: Optional[int]


class QuizQuestionsResponse(BaseModel):
    """Quiz questions structure for frontend"""
    version: str
    steps: Dict[str, Any]


class GoalUpdateRequest(BaseModel):
    """Request to update a single goal"""
    target_amount: Optional[int] = Field(None, ge=0)
    target_date: Optional[str] = None
    current_savings: Optional[int] = Field(None, ge=0)
    monthly_contribution: Optional[int] = Field(None, ge=0)
    priority: Optional[int] = Field(None, ge=1, le=3)
    status: Optional[str] = None


# Goal type to display name mapping
GOAL_TYPE_NAMES = {
    "emergency_fund": "Emergency Fund",
    "home_purchase": "Buy a Home",
    "home_loan_repayment": "Pay Off Home Loan",
    "children_education": "Children's Education",
    "retirement": "Retirement Planning",
    "marriage_self": "Marriage (Self)",
    "marriage_children": "Marriage (Children)",
    "vehicle_purchase": "Buy a Vehicle",
    "business_startup": "Start/Grow Business",
    "wealth_growth": "Wealth Growth",
    "travel_lifestyle": "Travel & Lifestyle",
    "tax_saving": "Tax Saving",
    "debt_repayment": "Debt Repayment"
}

# Timeline to months mapping
TIMELINE_TO_MONTHS = {
    "within_1_year": 12,
    "1_3_years": 24,  # midpoint
    "3_5_years": 48,  # midpoint
    "5_10_years": 90,  # midpoint
    "10_plus_years": 180,  # 15 years
    "ongoing": None
}

# Life stage descriptions
LIFE_STAGES = {
    "starting_career": "Starting my career (first job, building savings)",
    "building_wealth": "Building wealth (established income, growing family/assets)",
    "major_milestones": "Preparing for major milestones (home, marriage, children's education)",
    "nearing_retirement": "Nearing retirement (preserving wealth, planning exit from work)",
    "retired": "Retired (managing existing wealth, legacy planning)"
}

# Investment preference to risk score mapping
INVESTMENT_RISK_SCORES = {
    "bank_fd": 20,  # Conservative
    "balanced_mf": 50,  # Moderate
    "equity_mf": 80,  # Aggressive
    "keep_as_savings": 10,  # Very conservative
    "need_advice": 40  # Default moderate
}

# Volatility tolerance to risk score mapping
VOLATILITY_RISK_SCORES = {
    "panic_withdraw": 10,  # Very conservative
    "uncomfortable_wait": 30,  # Conservative
    "stay_calm": 60,  # Moderate
    "buying_opportunity": 90,  # Aggressive
    "wont_invest": 5  # Extremely conservative
}
