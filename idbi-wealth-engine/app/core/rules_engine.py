"""
Rules Engine for Financial Health Scoring
Loads and applies configurable business rules from JSON files.
"""

import json
from pathlib import Path
from typing import Dict, Any

from app.config import BASE_DIR


class RulesEngine:
    """Loads and applies business rules from configuration files"""
    
    def __init__(self, rules_file: str = "financial_health_rules.json"):
        """
        Initialize rules engine with configuration file.
        
        Args:
            rules_file: Name of rules JSON file in app/config/
        """
        self.rules_path = BASE_DIR / "config" / rules_file
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict[str, Any]:
        """Load rules from JSON file"""
        if not self.rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {self.rules_path}")
        
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def reload_rules(self):
        """Reload rules from file (useful if rules change)"""
        self.rules = self._load_rules()
    
    def calculate_component_score(self, component_name: str, value: float) -> int:
        """
        Calculate score for a single component based on rules.
        
        Args:
            component_name: Name of scoring component
            value: Calculated value for the component
            
        Returns:
            Points earned for this component
        """
        # Find component in rules
        component = None
        for comp in self.rules['scoring']['components']:
            if comp['name'] == component_name:
                component = comp
                break
        
        if not component:
            raise ValueError(f"Unknown component: {component_name}")
        
        # Apply rules
        for rule in component['rules']:
            min_val = rule.get('min', 0)
            max_val = rule.get('max')
            
            # Check if value falls in this range
            in_range = value >= min_val
            if max_val is not None:
                in_range = in_range and value < max_val
            
            if in_range:
                if rule['points'] == "linear":
                    # Evaluate formula
                    formula = rule['formula'].replace('value', str(value))
                    points = eval(formula)
                    return max(0, int(points))
                else:
                    return rule['points']
        
        # Default to 0 if no rule matched
        return 0
    
    def calculate_total_score(self, metrics: Dict[str, float]) -> int:
        """
        Calculate total financial health score.
        
        Args:
            metrics: Dictionary with component values
            
        Returns:
            Total score (0-100)
        """
        total_score = 0
        
        for component in self.rules['scoring']['components']:
            component_name = component['name']
            if component_name in metrics:
                value = metrics[component_name]
                points = self.calculate_component_score(component_name, value)
                total_score += points
        
        return min(total_score, self.rules['scoring']['max_score'])
    
    def get_grade(self, score: int) -> str:
        """
        Convert score to letter grade.
        
        Args:
            score: Numeric score (0-100)
            
        Returns:
            Letter grade (A+, A, B+, etc.)
        """
        for grade_range in self.rules['grading']['ranges']:
            if grade_range['min'] <= score < grade_range['max']:
                return grade_range['grade']
        
        # Default to lowest grade
        return self.rules['grading']['ranges'][-1]['grade']
    
    def get_grade_label(self, score: int) -> str:
        """Get descriptive label for score"""
        for grade_range in self.rules['grading']['ranges']:
            if grade_range['min'] <= score < grade_range['max']:
                return grade_range['label']
        
        return self.rules['grading']['ranges'][-1]['label']
    
    def get_thresholds(self) -> Dict[str, Any]:
        """Get all configured thresholds"""
        return self.rules.get('thresholds', {})
    
    def get_ai_guidelines(self) -> Dict[str, Any]:
        """Get AI generation guidelines"""
        return self.rules.get('ai_guidelines', {})
    
    def get_rules_version(self) -> str:
        """Get version of loaded rules"""
        return self.rules.get('version', 'unknown')
    
    def get_rules_info(self) -> Dict[str, Any]:
        """Get metadata about loaded rules"""
        return {
            "version": self.rules.get('version'),
            "last_updated": self.rules.get('last_updated'),
            "description": self.rules.get('description'),
            "rules_file": str(self.rules_path),
            "components": len(self.rules['scoring']['components'])
        }


# Global rules engine instance
rules_engine = RulesEngine()
