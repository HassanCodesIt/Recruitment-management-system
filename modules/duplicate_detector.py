"""
Duplicate Detector Module - Advanced Fuzzy Matching
Detects duplicate candidates using multiple strategies
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from thefuzz import fuzz
import re
import logging
from typing import Dict, List, Tuple, Optional
from database import execute_query, update_record

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Detects duplicate candidates using fuzzy matching"""
    
    def __init__(self, name_threshold: int = 85, phone_threshold: int = 90):
        self.name_threshold = name_threshold
        self.phone_threshold = phone_threshold
    
    def normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        """Normalize phone number to digits only"""
        if not phone:
            return None
        
        # Extract only digits
        digits = re.sub(r'\D', '', phone)
        
        # Return last 10 digits (strip country code)
        if len(digits) >= 10:
            return digits[-10:]
        
        return digits if digits else None
    
    def check_exact_email(self, candidate: Dict, database: List[Dict]) -> Tuple[bool, Optional[Dict]]:
        """Check for exact email match"""
        if not candidate.get('email'):
            return False, None
        
        candidate_email = candidate['email'].lower().strip()
        
        for record in database:
            if record.get('email'):
                if candidate_email == record['email'].lower().strip():
                    logger.info(f"🔍 Exact email match found: {candidate_email}")
                    return True, record
        
        return False, None
    
    def check_phone_similarity(self, candidate: Dict, database: List[Dict]) -> Tuple[bool, Optional[Dict]]:
        """Check for phone number similarity"""
        candidate_phone = self.normalize_phone(candidate.get('phone'))
        
        if not candidate_phone:
            return False, None
        
        for record in database:
            record_phone = self.normalize_phone(record.get('phone'))
            
            if not record_phone:
                continue
            
            # Exact match on normalized phones
            if candidate_phone == record_phone:
                logger.info(f"🔍 Phone match found: {candidate_phone}")
                return True, record
        
        return False, None
    
    def check_name_similarity(self, candidate: Dict, database: List[Dict]) -> Tuple[bool, Optional[Dict], int]:
        """Check for name similarity using fuzzy matching"""
        if not candidate.get('name'):
            return False, None, 0
        
        candidate_name = candidate['name'].lower().strip()
        
        best_match = None
        best_score = 0
        
        for record in database:
            if not record.get('name'):
                continue
            
            record_name = record['name'].lower().strip()
            
            # Use token_set_ratio (handles "John Doe" vs "Doe, John")
            score = fuzz.token_set_ratio(candidate_name, record_name)
            
            if score > best_score:
                best_score = score
                best_match = record
        
        if best_score >= self.name_threshold:
            logger.info(f"🔍 Name similarity match: {candidate_name} ~ {best_match['name']} ({best_score}%)")
            return True, best_match, best_score
        
        return False, None, best_score
    
    def detect_duplicate(self, candidate: Dict, return_match: bool = True) -> Tuple[bool, Optional[str], Optional[Dict], Optional[float]]:
        """
        Main method to detect if a candidate is a duplicate
        
        Returns:
            (is_duplicate, reason, matching_record, confidence)
        """
        
        # Get all non-duplicate candidates from database
        database = execute_query("""
            SELECT id, name, email, phone 
            FROM candidates 
            WHERE is_duplicate = FALSE
        """, fetch_all=True) or []
        
        if not database:
            return False, "Unique (first candidate)", None, None
        
        # Strategy 1: Exact email match (highest priority)
        is_dup, match = self.check_exact_email(candidate, database)
        if is_dup:
            reason = f"Exact Email Match ({match['email']})"
            return True, reason, match if return_match else None, 1.0
        
        # Strategy 2: Phone number match
        is_dup, match = self.check_phone_similarity(candidate, database)
        if is_dup:
            reason = f"Phone Match ({match.get('name', 'Unknown')})"
            return True, reason, match if return_match else None, 0.95
        
        # Strategy 3: Name similarity (fuzzy matching)
        is_dup, match, score = self.check_name_similarity(candidate, database)
        if is_dup:
            confidence = score / 100.0
            reason = f"Name Similarity {score}% ({match['name']})"
            return True, reason, match if return_match else None, confidence
        
        # No duplicate found
        return False, "Unique", None, None
    
    def mark_as_duplicate(self, candidate_id: int, original_id: int, confidence: float) -> bool:
        """Mark a candidate as duplicate in the database"""
        try:
            update_data = {
                "is_duplicate": True,
                "duplicate_of": original_id,
                "duplicate_confidence": confidence
            }
            
            success = update_record("candidates", candidate_id, update_data)
            
            if success:
                logger.info(f"✅ Marked candidate {candidate_id} as duplicate of {original_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error marking duplicate: {e}")
            return False
    
    def find_all_duplicates(self) -> List[Dict]:
        """Find all duplicate candidates in the database"""
        try:
            duplicates = execute_query("""
                SELECT 
                    c1.id as duplicate_id,
                    c1.name as duplicate_name,
                    c1.email as duplicate_email,
                    c2.id as original_id,
                    c2.name as original_name,
                    c2.email as original_email,
                    c1.duplicate_confidence,
                    c1.created_at as duplicate_created_at
                FROM candidates c1
                JOIN candidates c2 ON c1.duplicate_of = c2.id
                WHERE c1.is_duplicate = TRUE
                ORDER BY c1.created_at DESC
            """, fetch_all=True)
            
            return duplicates or []
            
        except Exception as e:
            logger.error(f"❌ Error finding duplicates: {e}")
            return []
    
    def merge_candidates(self, duplicate_id: int, original_id: int) -> bool:
        """
        Merge duplicate candidate data into original
        (Optional advanced feature)
        """
        # This is a placeholder for future implementation
        # Could merge additional information from duplicate into original
        logger.warning("Merge functionality not yet implemented")
        return False


def detect_duplicate_candidate(candidate: Dict, name_threshold: int = 85) -> Tuple[bool, str, Optional[Dict], Optional[float]]:
    """Convenience function to detect duplicates"""
    detector = DuplicateDetector(name_threshold=name_threshold)
    return detector.detect_duplicate(candidate)


if __name__ == "__main__":
    # Test the duplicate detector
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 Testing Duplicate Detector\n")
    
    # Test candidate
    test_candidate = {
        "name": "John Smith",
        "email": "john.smith@example.com",
        "phone": "+1-555-123-4567"
    }
    
    detector = DuplicateDetector(name_threshold=85)
    
    is_dup, reason, match, confidence = detector.detect_duplicate(test_candidate)
    
    print("=" * 60)
    print("DUPLICATE CHECK RESULT")
    print("=" * 60)
    print(f"Candidate: {test_candidate['name']}")
    print(f"Email: {test_candidate['email']}")
    print(f"Phone: {test_candidate['phone']}")
    print(f"\nIs Duplicate: {is_dup}")
    print(f"Reason: {reason}")
    if match:
        print(f"Matched With: {match.get('name')} (ID: {match.get('id')})")
    if confidence:
        print(f"Confidence: {confidence:.2%}")
    
    # Find all existing duplicates
    print("\n" + "=" * 60)
    print("EXISTING DUPLICATES IN DATABASE")
    print("=" * 60)
    
    all_duplicates = detector.find_all_duplicates()
    
    if all_duplicates:
        for dup in all_duplicates:
            print(f"\n❌ {dup['duplicate_name']} (ID: {dup['duplicate_id']})")
            print(f"   Original: {dup['original_name']} (ID: {dup['original_id']})")
            print(f"   Confidence: {dup['duplicate_confidence']:.2%}")
    else:
        print("✅ No duplicates found in database")
