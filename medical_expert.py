#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import os
import logging
from datetime import datetime
from typing import Dict, List, Union, Any, Optional
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeBase:
    """Enhanced knowledge base management with validation and caching"""
    def __init__(self, knowledge_file: str = "medical_knowledge.json"):
        self.knowledge_file = knowledge_file
        self.diseases: Dict[str, Dict] = {}
        self.rules: List[Dict] = []
        self.symptom_mapping: Dict[str, str] = {}
        self.symptom_cache: Dict[str, str] = {}  # Cache for normalized symptoms
        self.last_modified: Optional[float] = None
        self.metadata: Dict[str, Any] = {}
        self.load_knowledge()
    
    def load_knowledge(self) -> None:
        """Load and validate knowledge from JSON file"""
        try:
            if not os.path.exists(self.knowledge_file):
                logger.warning(f"Knowledge file {self.knowledge_file} not found. Creating default knowledge...")
                self._create_default_knowledge()
                return
                
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate and load knowledge
            self.diseases = data.get("diseases", {})
            self.rules = data.get("rules", [])
            self.symptom_mapping = data.get("symptom_mapping", {})
            self.metadata = data.get("metadata", {})
            
            # Validate knowledge structure
            self._validate_knowledge()
            
            self.last_modified = os.path.getmtime(self.knowledge_file)
            self.symptom_cache.clear()  # Clear cache on reload
            
            logger.info(f"Successfully loaded knowledge from {self.knowledge_file}")
            logger.info(f"Loaded {len(self.diseases)} diseases, {len(self.rules)} rules, {len(self.symptom_mapping)} symptom mappings")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in {self.knowledge_file}: {str(e)}")
            self._create_default_knowledge()
        except Exception as e:
            logger.error(f"Error loading knowledge: {str(e)}")
            self._create_default_knowledge()
    
    def _validate_knowledge(self) -> None:
        """Validate knowledge structure and data integrity"""
        if not self.diseases:
            logger.warning("No diseases found in knowledge base")
        
        # Validate disease structure
        for disease_name, disease_data in self.diseases.items():
            if not isinstance(disease_data, dict):
                logger.warning(f"Invalid disease data for {disease_name}")
                continue
                
            symptom_weights = disease_data.get("symptom_weights", {})
            if not symptom_weights:
                logger.warning(f"No symptom weights for disease {disease_name}")
        
        # Validate rules
        for rule in self.rules:
            if not all(key in rule for key in ["conditions", "conclusion", "weight"]):
                logger.warning(f"Invalid rule structure: {rule}")
    
    def check_for_updates(self) -> bool:
        """Check for knowledge file updates with improved error handling"""
        if not os.path.exists(self.knowledge_file):
            return False
            
        try:
            current_modified = os.path.getmtime(self.knowledge_file)
            if current_modified != self.last_modified:
                logger.info("Knowledge file updated. Reloading...")
                self.load_knowledge()
                return True
        except OSError as e:
            logger.error(f"Error checking file modification time: {str(e)}")
        
        return False
    
    def _create_default_knowledge(self) -> None:
        """Create default knowledge structure"""
        logger.info("Creating default knowledge structure...")
        self.diseases = {}
        self.rules = []
        self.symptom_mapping = {}
        self.metadata = {
            "version": "1.0",
            "description": "Default knowledge base",
            "last_updated": datetime.now().isoformat()
        }
    
    def get_all_diseases(self) -> List[str]:
        """Get list of all diseases"""
        return list(self.diseases.keys())
    
    def get_symptom_weight(self, disease: str, symptom: str) -> int:
        """Get symptom weight for disease with validation"""
        if disease not in self.diseases:
            return 0
            
        disease_data = self.diseases.get(disease, {})
        weights = disease_data.get("symptom_weights", {})
        return weights.get(symptom, 0)
    
    def get_disease_info(self, disease: str) -> Dict[str, Any]:
        """Get comprehensive disease information"""
        return self.diseases.get(disease, {})
    
    def get_all_symptoms(self) -> List[str]:
        """Get all unique symptoms from the knowledge base"""
        symptoms = set()
        for disease_data in self.diseases.values():
            symptom_weights = disease_data.get("symptom_weights", {})
            symptoms.update(symptom_weights.keys())
        return list(symptoms)


class RuleEngine:
    """Enhanced rule engine with fuzzy matching and improved scoring"""
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.early_stop_threshold = 8  # Increased for more confidence
        self.min_threshold = 4  # Increased minimum threshold
        self.fuzzy_match_threshold = 0.8  # Threshold for fuzzy matching
        self.max_suspected_diseases = 5  # Maximum number of suspected diseases to return
    
    def normalize_symptom(self, symptom: str) -> str:
        """Enhanced symptom normalization with fuzzy matching"""
        if not symptom:
            return ""
            
        # Check cache first
        if symptom in self.kb.symptom_cache:
            return self.kb.symptom_cache[symptom]
        
        symptom = symptom.strip().lower()
        symptom = re.sub(r'[^\w\s]', '', symptom)
        
        # Direct mapping check
        if symptom in self.kb.symptom_mapping:
            normalized = self.kb.symptom_mapping[symptom]
            self.kb.symptom_cache[symptom] = normalized
            return normalized
        
        # Fuzzy matching with symptom mapping
        best_match = self._fuzzy_match_symptom(symptom)
        if best_match:
            self.kb.symptom_cache[symptom] = best_match
            return best_match
        
        # Partial matching
        for key, value in self.kb.symptom_mapping.items():
            if key in symptom or symptom in key:
                self.kb.symptom_cache[symptom] = value
                return value
        
        # Return original if no match found
        self.kb.symptom_cache[symptom] = symptom
        return symptom
    
    def _fuzzy_match_symptom(self, symptom: str) -> Optional[str]:
        """Find best fuzzy match for symptom"""
        best_match = None
        best_ratio = 0
        
        for key, value in self.kb.symptom_mapping.items():
            ratio = SequenceMatcher(None, symptom, key).ratio()
            if ratio > best_ratio and ratio >= self.fuzzy_match_threshold:
                best_ratio = ratio
                best_match = value
        
        return best_match
    
    def calculate_scores(self, symptoms: List[str]) -> Dict[str, int]:
        """Calculate disease scores with enhanced weighting"""
        scores = {disease: 0 for disease in self.kb.get_all_diseases()}
        matched_symptoms = {disease: [] for disease in scores.keys()}
        
        for symptom in symptoms:
            normalized_symptom = self.normalize_symptom(symptom)
            for disease in scores.keys():
                weight = self.kb.get_symptom_weight(disease, normalized_symptom)
                if weight > 0:
                    scores[disease] += weight
                    matched_symptoms[disease].append((symptom, normalized_symptom, weight))
        
        # Add bonus for multiple matching symptoms
        for disease, matched_list in matched_symptoms.items():
            if len(matched_list) >= 3:
                scores[disease] += 2  # Bonus for multiple symptoms
        
        return scores
    
    def apply_rules(self, symptoms: List[str]) -> Dict[str, int]:
        """Apply IF-THEN rules with enhanced matching"""
        additional_scores = {disease: 0 for disease in self.kb.get_all_diseases()}
        normalized_symptoms = [self.normalize_symptom(s) for s in symptoms]
        
        for rule in self.kb.rules:
            conditions = [self.normalize_symptom(cond) for cond in rule["conditions"]]
            if all(cond in normalized_symptoms for cond in conditions):
                disease = rule["conclusion"]
                if disease in additional_scores:
                    additional_scores[disease] += rule["weight"]
                    logger.debug(f"Applied rule {rule.get('id', 'unknown')} for {disease}")
        
        return additional_scores
    
    def apply_stopping_conditions(self, scores: Dict[str, int]) -> Dict[str, Any]:
        """Apply stopping conditions with enhanced confidence calculation"""
        if not scores:
            return {
                "status": "unknown",
                "message": "Unable to determine diagnosis - no matching symptoms found",
                "confidence": 0,
                "all_scores": scores
            }
        
        # Filter out zero scores
        non_zero_scores = {k: v for k, v in scores.items() if v > 0}
        
        if not non_zero_scores:
            return {
                "status": "unknown",
                "message": "No symptoms match any known diseases",
                "confidence": 0,
                "all_scores": scores
            }
        
        max_score = max(non_zero_scores.values())
        best_disease = max(non_zero_scores, key=non_zero_scores.get)
        
        # Calculate confidence percentage
        total_possible_score = self._calculate_max_possible_score(best_disease)
        confidence_percentage = min(100, (max_score / total_possible_score) * 100) if total_possible_score > 0 else 0
        
        if max_score >= self.early_stop_threshold:
            return {
                "status": "diagnosis",
                "diagnosis": best_disease,
                "confidence": max_score,
                "confidence_percentage": confidence_percentage,
                "all_scores": scores,
                "matched_symptoms": self._get_matched_symptoms(best_disease, scores)
            }
        
        if max_score >= self.min_threshold:
            sorted_diseases = sorted(non_zero_scores.items(), key=lambda x: x[1], reverse=True)
            top_diseases = sorted_diseases[:self.max_suspected_diseases]
            
            return {
                "status": "suspected",
                "top_diseases": top_diseases,
                "all_scores": scores,
                "confidence_percentage": confidence_percentage,
                "matched_symptoms": {disease: self._get_matched_symptoms(disease, scores) 
                                   for disease, _ in top_diseases}
            }
        
        return {
            "status": "unknown",
            "message": "Insufficient data for diagnosis - more symptoms needed",
            "confidence": max_score,
            "confidence_percentage": confidence_percentage,
            "all_scores": scores
        }
    
    def _calculate_max_possible_score(self, disease: str) -> int:
        """Calculate maximum possible score for a disease"""
        disease_info = self.kb.get_disease_info(disease)
        symptom_weights = disease_info.get("symptom_weights", {})
        return sum(symptom_weights.values())
    
    def _get_matched_symptoms(self, disease: str, scores: Dict[str, int]) -> List[str]:
        """Get list of symptoms that matched for a disease"""
        # This would need to be implemented based on the actual symptom matching
        # For now, return empty list
        return []


class MedicalExpertSystem:
    """Enhanced medical expert system with improved diagnosis capabilities"""
    def __init__(self, knowledge_file: str = "medical_knowledge.json"):
        self.kb = KnowledgeBase(knowledge_file)
        self.rule_engine = RuleEngine(self.kb)
        self.diagnosis_history: List[Dict] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def diagnose(self, user_symptoms: List[str]) -> Dict[str, Any]:
        """Enhanced diagnosis with detailed analysis"""
        # Check for knowledge updates
        self.kb.check_for_updates()
        
        if not user_symptoms:
            return {
                "status": "error",
                "message": "No symptoms provided",
                "timestamp": datetime.now().isoformat()
            }
        
        # Calculate scores from symptoms
        symptom_scores = self.rule_engine.calculate_scores(user_symptoms)
        
        # Apply rules for additional scoring
        rule_scores = self.rule_engine.apply_rules(user_symptoms)
        
        # Combine scores
        for disease, score in rule_scores.items():
            symptom_scores[disease] = symptom_scores.get(disease, 0) + score
        
        # Apply stopping conditions
        result = self.rule_engine.apply_stopping_conditions(symptom_scores)
        
        # Add metadata
        result["timestamp"] = datetime.now().isoformat()
        result["session_id"] = self.session_id
        result["input_symptoms"] = user_symptoms
        result["total_symptoms"] = len(user_symptoms)
        
        # Save diagnosis history
        diagnosis_record = {
            "timestamp": result["timestamp"],
            "session_id": self.session_id,
            "symptoms": user_symptoms,
            "result": result
        }
        self.diagnosis_history.append(diagnosis_record)
        
        logger.info(f"Diagnosis completed: {result['status']} - {result.get('diagnosis', 'N/A')}")
        
        return result
    
    def get_diagnosis_history(self, limit: int = 10) -> List[Dict]:
        """Get recent diagnosis history"""
        return self.diagnosis_history[-limit:] if self.diagnosis_history else []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            "total_diseases": len(self.kb.get_all_diseases()),
            "total_rules": len(self.kb.rules),
            "total_symptoms": len(self.kb.get_all_symptoms()),
            "diagnosis_count": len(self.diagnosis_history),
            "knowledge_version": self.kb.metadata.get("version", "1.0"),
            "last_updated": self.kb.metadata.get("last_updated", "Unknown")
        }


def main():
    """Enhanced main function with better user interface"""
    print("=" * 60)
    print("🏥 ENHANCED MEDICAL EXPERT SYSTEM - DIAGNOSIS ENGINE")
    print("=" * 60)
    
    # Show system stats
    expert_system = MedicalExpertSystem()
    stats = expert_system.get_system_stats()
    print(f"📊 Knowledge Base: {stats['total_diseases']} diseases, {stats['total_rules']} rules")
    print(f"📈 Total Symptoms: {stats['total_symptoms']}")
    print(f"🔄 Version: {stats['knowledge_version']}")
    print("=" * 60)
    
    print("💬 Interactive Diagnosis Mode")
    print("Enter symptoms separated by commas (e.g., sốt cao, ho khan, mệt mỏi)")
    print("Type 'exit' to quit, 'help' for available symptoms")
    
    while True:
        print("\n" + "-" * 40)
        symptoms_input = input("🔍 Enter symptoms: ").strip()
        
        if symptoms_input.lower() in ['exit', 'quit', 'q']:
            print("👋 Goodbye!")
            break
        
        if symptoms_input.lower() == 'help':
            all_symptoms = expert_system.kb.get_all_symptoms()
            print(f"\n📋 Available symptoms ({len(all_symptoms)}):")
            for i, symptom in enumerate(all_symptoms, 1):
                print(f"  {i:2d}. {symptom}")
            continue
        
        if symptoms_input.lower() == 'stats':
            stats = expert_system.get_system_stats()
            print(f"\n📊 System Statistics:")
            for key, value in stats.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
            continue
        
        symptoms = [s.strip() for s in symptoms_input.split(",") if s.strip()]
        
        if symptoms:
            print(f"\n🔬 Analyzing {len(symptoms)} symptoms...")
            result = expert_system.diagnose(symptoms)
            
            print("\n" + "=" * 50)
            print("🏥 DIAGNOSIS RESULTS")
            print("=" * 50)
            
            if result["status"] == "diagnosis":
                print(f"✅ DIAGNOSIS: {result['diagnosis']}")
                print(f"📊 Confidence: {result['confidence']} points ({result.get('confidence_percentage', 0):.1f}%)")
                print(f"⏰ Timestamp: {result['timestamp']}")
            
            elif result["status"] == "suspected":
                print("🤔 SUSPECTED DISEASES:")
                for i, (disease, score) in enumerate(result["top_diseases"], 1):
                    print(f"  {i}. {disease} ({score} points)")
                print(f"📊 Overall Confidence: {result.get('confidence_percentage', 0):.1f}%")
            
            else:
                print(f"❓ {result['message']}")
                print(f"📊 Score: {result.get('confidence', 0)} points")
            
            print("=" * 50)
        else:
            print("⚠️  No symptoms entered. Please provide at least one symptom.")


if __name__ == "__main__":
    main()