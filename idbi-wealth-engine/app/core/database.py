# SQLAlchemy models for persistence layer

from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, Text, CheckConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Lead(Base):
    __tablename__ = 'leads'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(String(50), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    product_type = Column(String(50), nullable=False)
    tier = Column(String(1), CheckConstraint("tier IN ('A', 'B')"), nullable=False)
    recommended_amount = Column(Integer, nullable=False)
    suitability_trail = Column(JSON, nullable=False)
    status = Column(String(20), default='pending')
    priority_score = Column(Integer, default=50)
    assigned_rm = Column(String(100))
    rm_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MiningSignal(Base):
    __tablename__ = 'mining_signals'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(String(50), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False, index=True)
    signal_value = Column(JSON, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(String(50), nullable=False, index=True)
    endpoint = Column(String(100), nullable=False)
    recommendation = Column(JSON)
    reasoning = Column(JSON)
    model_version = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)

class CustomerGoal(Base):
    __tablename__ = 'customer_goals'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(String(50), nullable=False, index=True)
    goal_name = Column(String(200), nullable=False)
    target_amount = Column(Integer, nullable=False)
    target_date = Column(String(10), nullable=False)
    current_savings = Column(Integer, default=0)
    monthly_contribution = Column(Integer, default=0)
    priority = Column(String(10))
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class RiskProfile(Base):
    __tablename__ = 'risk_profiles'
    
    customer_id = Column(String(50), primary_key=True)
    risk_category = Column(String(20), nullable=False)
    questionnaire_answers = Column(JSON, nullable=False)
    language_preference = Column(String(20), default='English')
    profile_updated_at = Column(DateTime, default=datetime.utcnow)

class QuizResponse(Base):
    __tablename__ = 'quiz_responses'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(String(50), nullable=False, index=True, unique=True)
    quiz_version = Column(String(10), nullable=False, default='v1.0')
    life_stage = Column(String(50), nullable=False)
    priorities = Column(JSON, nullable=False)
    goals = Column(JSON, nullable=False)
    risk_profile = Column(JSON, nullable=False)
    computed_stats = Column(JSON)
    completed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database connection manager
class Database:
    def __init__(self, db_url=None):
        import os
        # Use DATABASE_URL if provided (e.g. Render Postgres), else fall back to local SQLite.
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "sqlite:///./idbi_wealth.db")
        # Render's Postgres URLs use the "postgres://" scheme, which SQLAlchemy cannot
        # parse. Convert it to the "postgresql://" scheme SQLAlchemy expects.
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def init_db(self):
        Base.metadata.create_all(self.engine)
        
    def get_session(self):
        return self.SessionLocal()

db = Database()
