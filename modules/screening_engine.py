"""
Screening Engine Module - AI-Driven Screening & Shortlisting
Scores candidates against job descriptions using semantic similarity and skill matching
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import json
import uuid
from database import execute_query, insert_record, get_db_cursor

logger = logging.getLogger(__name__)


class ScreeningEngine:
    """AI-driven candidate screening and shortlisting"""
    
    def __init__(self):
        # Load embedding model
        logger.info("Loading sentence transformer model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Model loaded")
    
    def get_job_description(self, jd_id: int) -> Optional[Dict]:
        """Get job description from database"""
        jd = execute_query(
            "SELECT * FROM job_descriptions WHERE id = %s",
            (jd_id,),
            fetch_one=True
        )
        return jd
    
    def get_candidates_for_screening(self, exclude_duplicates: bool = True) -> List[Dict]:
        """Get all candidates available for screening"""
        query = """
            SELECT 
                id, name, email, phone, skills, text_content,
                experience_years, summary, education, experience
            FROM candidates
        """
        
        if exclude_duplicates:
            query += " WHERE is_duplicate = FALSE"
        
        query += " ORDER BY created_at DESC"
        
        candidates = execute_query(query, fetch_all=True)
        return candidates or []
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from text (simple keyword extraction)"""
        if not text:
            return []
        
        text_lower = text.lower()
        
        # Common skill keywords
        skill_keywords = [
            "python", "java", "javascript", "typescript", "c++", "c#", "sql",
            "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
            "machine learning", "deep learning", "data science", "ai",
            "project management", "agile", "scrum", "communication",
            "leadership", "teamwork", "problem solving",
            "excel", "tableau", "power bi", "git", "ci/cd"
        ]
        
        found_skills = []
        for skill in skill_keywords:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        return list(set(found_skills))
    
    def parse_jd_skills(self, jd: Dict) -> List[str]:
        """Parse required skills from job description"""
        skills = []
        
        # From required_skills field
        if jd.get('required_skills'):
            skills_text = jd['required_skills']
            # Handle both comma-separated and newline-separated
            skills.extend([s.strip() for s in skills_text.replace('\n', ',').split(',') if s.strip()])
        
        # Also extract from description
        if jd.get('description'):
            skills.extend(self.extract_skills_from_text(jd['description']))
        
        return list(set(skills))
    
    def compute_semantic_score(self, jd_text: str, cv_text: str) -> float:
        """Compute semantic similarity between JD and CV"""
        if not jd_text or not cv_text:
            return 0.0
        
        # Limit text length for efficiency
        jd_text = jd_text[:2000]
        cv_text = cv_text[:2000]
        
        # Generate embeddings
        embeddings = self.embedder.encode([jd_text, cv_text])
        
        # Compute cosine similarity
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        
        # Convert to 0-100 scale
        return float(similarity * 100)
    
    def compute_skill_match_score(self, jd_skills: List[str], candidate_skills: str) -> Tuple[float, List[str], List[str]]:
        """Compute skill match score"""
        if not jd_skills:
            return 0.0, [], []
        
        # Parse candidate skills
        if isinstance(candidate_skills, str):
            candidate_skills_list = [
                s.strip() for s in candidate_skills.replace('\n', ',').split(',') if s.strip()
            ]
        else:
            candidate_skills_list = []
        
        # Convert to sets for comparison (case-insensitive)
        jd_skills_set = set(s.lower() for s in jd_skills)
        cand_skills_set = set(s.lower() for s in candidate_skills_list)
        
        # Find matched and missing skills
        matched = jd_skills_set.intersection(cand_skills_set)
        missing = jd_skills_set - cand_skills_set
        
        # Calculate match percentage
        if len(jd_skills_set) > 0:
            score = (len(matched) / len(jd_skills_set)) * 100
        else:
            score = 0.0
        
        # Get original case for display
        matched_display = [s for s in jd_skills if s.lower() in matched]
        missing_display = [s for s in jd_skills if s.lower() in missing]
        
        return score, matched_display, missing_display
    
    def compute_experience_score(self, required_min: int, required_max: Optional[int], 
                                 candidate_years: int) -> Tuple[float, int]:
        """Compute experience match score"""
        if required_min is None:
            return 0.0, 0
        
        # Gap calculation
        if candidate_years < required_min:
            gap = required_min - candidate_years
            # Penalize based on gap
            score = max(0, 100 - (gap * 20))  # -20% per year below minimum
        elif required_max and candidate_years > required_max:
            gap = candidate_years - required_max
            # Slight penalty for overqualification
            score = max(0, 100 - (gap * 5))  # -5% per year above maximum
        else:
            gap = 0
            score = 100.0
        
        return score, gap
    
    def calculate_final_score(self, semantic_score: float, skill_score: float, 
                             experience_score: float, config: Dict) -> float:
        """Calculate weighted final score"""
        # Get weights from config
        semantic_weight = config.get('semantic_weight', 0.7)
        skill_weight = config.get('skill_weight', 0.3)
        experience_weight = config.get('experience_weight', 0.0)
        
        # Normalize weights
        total_weight = semantic_weight + skill_weight + experience_weight
        
        if total_weight == 0:
            return 0.0
        
        # Calculate weighted score
        final_score = (
            (semantic_score * semantic_weight) +
            (skill_score * skill_weight) +
            (experience_score * experience_weight)
        ) / total_weight
        
        return round(final_score, 2)
    
    def screen_candidates(self, jd_id: int, rescreen: bool = False) -> Dict:
        """
        Main screening function
        Screens all candidates against a job description
        
        Args:
            jd_id: Job description ID
            rescreen: If True, re-screen even if results already exist
        
        Returns:
            Summary dict with screening results
        """
        logger.info(f"🔍 Starting screening for JD ID: {jd_id}")
        
        summary = {
            "success": False,
            "jd_id": jd_id,
            "total_candidates": 0,
            "screened_count": 0,
            "longlist_count": 0,
            "shortlist_count": 0,
            "avg_score": 0,
            "max_score": 0,
            "batch_id": None,
            "errors": []
        }
        
        try:
            # Get job description
            jd = self.get_job_description(jd_id)
            
            if not jd:
                summary["errors"].append(f"Job description {jd_id} not found")
                return summary
            
            # Get matching configuration
            config = jd.get('matching_config', {})
            if isinstance(config, str):
                config = json.loads(config)
            
            # Extract JD skills
            jd_skills = self.parse_jd_skills(jd)
            jd_text = jd.get('description', '')
            required_exp_min = jd.get('required_experience_min', 0)
            required_exp_max = jd.get('required_experience_max')
            
            # Get candidates
            candidates = self.get_candidates_for_screening()
            summary["total_candidates"] = len(candidates)
            
            if not candidates:
                summary["errors"].append("No candidates available for screening")
                return summary
            
            logger.info(f"📊 Screening {len(candidates)} candidates...")
            
            # Delete existing results if rescreening
            if rescreen:
                with get_db_cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM screening_results WHERE job_description_id = %s",
                        (jd_id,)
                    )
            
            # Generate batch ID
            batch_id = str(uuid.uuid4())[:8]
            summary["batch_id"] = batch_id
            
            # Screen each candidate
            all_scores = []
            
            for candidate in candidates:
                try:
                    # Compute scores
                    semantic_score = self.compute_semantic_score(
                        jd_text,
                        candidate.get('text_content', '') or candidate.get('summary', '') or ''
                    )
                    
                    skill_score, matched_skills, missing_skills = self.compute_skill_match_score(
                        jd_skills,
                        candidate.get('skills', '')
                    )
                    
                    experience_score, exp_gap = self.compute_experience_score(
                        required_exp_min,
                        required_exp_max,
                        candidate.get('experience_years', 0)
                    )
                    
                    # Calculate final score
                    final_score = self.calculate_final_score(
                        semantic_score,
                        skill_score,
                        experience_score,
                        config
                    )
                    
                    all_scores.append(final_score)
                    
                    # Store result
                    result_data = {
                        "job_description_id": jd_id,
                        "candidate_id": candidate['id'],
                        "final_score": final_score,
                        "semantic_score": semantic_score,
                        "skill_match_score": skill_score,
                        "experience_score": experience_score,
                        "matched_skills": ", ".join(matched_skills) if matched_skills else None,
                        "missing_skills": ", ".join(missing_skills) if missing_skills else None,
                        "experience_gap": exp_gap,
                        "in_longlist": False,  # Will update later
                        "in_shortlist": False,
                        "status": "pending"
                    }
                    
                    insert_record("screening_results", result_data)
                    summary["screened_count"] += 1
                    
                except Exception as e:
                    logger.error(f"Error screening candidate {candidate.get('id')}: {e}")
                    summary["errors"].append(f"Candidate {candidate.get('name')}: {str(e)}")
            
            # Calculate statistics
            if all_scores:
                summary["avg_score"] = round(np.mean(all_scores), 2)
                summary["max_score"] = round(max(all_scores), 2)
            
            # Determine longlist and shortlist cutoffs
            longlist_pct = config.get('longlist_percentage', 0.5)
            shortlist_pct = config.get('shortlist_percentage', 0.2)
            min_threshold = config.get('min_score_threshold', 50)
            
            # Get sorted results
            with get_db_cursor() as cursor:
                # Update rankings
                cursor.execute("""
                    UPDATE screening_results sr
                    SET rank_position = subquery.rank
                    FROM (
                        SELECT id, ROW_NUMBER() OVER (ORDER BY final_score DESC) as rank
                        FROM screening_results
                        WHERE job_description_id = %s
                    ) AS subquery
                    WHERE sr.id = subquery.id
                """, (jd_id,))
                
                # Calculate cutoffs
                total_count = len(all_scores)
                longlist_count = int(total_count * longlist_pct)
                shortlist_count = int(total_count * shortlist_pct)
                
                # Mark longlist
                cursor.execute("""
                    UPDATE screening_results
                    SET in_longlist = TRUE
                    WHERE job_description_id = %s
                      AND rank_position <= %s
                      AND final_score >= %s
                """, (jd_id, longlist_count, min_threshold))
                
                summary["longlist_count"] = cursor.rowcount
                
                # Mark shortlist
                cursor.execute("""
                    UPDATE screening_results
                    SET in_shortlist = TRUE
                    WHERE job_description_id = %s
                      AND rank_position <= %s
                      AND final_score >= %s
                """, (jd_id, shortlist_count, min_threshold))
                
                summary["shortlist_count"] = cursor.rowcount
            
            # Record screening history
            history_data = {
                "job_description_id": jd_id,
                "batch_id": batch_id,
                "total_candidates": summary["total_candidates"],
                "longlist_count": summary["longlist_count"],
                "shortlist_count": summary["shortlist_count"],
                "avg_score": summary["avg_score"],
                "max_score": summary["max_score"],
                "min_score": round(min(all_scores), 2) if all_scores else 0,
                "config_snapshot": json.dumps(config),
                "executed_at": datetime.now()
            }
            
            insert_record("screening_history", history_data)
            
            summary["success"] = True
            logger.info(f"✅ Screening complete: {summary['screened_count']} candidates scored")
            logger.info(f"   Longlist: {summary['longlist_count']}, Shortlist: {summary['shortlist_count']}")
            
        except Exception as e:
            logger.error(f"❌ Screening failed: {e}")
            summary["errors"].append(str(e))
        
        return summary
    
    def get_screening_results(self, jd_id: int, list_type: str = "all") -> List[Dict]:
        """Get screening results for a job description"""
        query = """
            SELECT 
                sr.*,
                c.name, c.email, c.phone, c.experience_years,
                c.source_file, c.created_at as candidate_created_at
            FROM screening_results sr
            JOIN candidates c ON sr.candidate_id = c.id
            WHERE sr.job_description_id = %s
        """
        
        if list_type == "shortlist":
            query += " AND sr.in_shortlist = TRUE"
        elif list_type == "longlist":
            query += " AND sr.in_longlist = TRUE"
        
        query += " ORDER BY sr.final_score DESC"
        
        results = execute_query(query, (jd_id,), fetch_all=True)
        return results or []


if __name__ == "__main__":
    # Test the screening engine
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 Testing Screening Engine\n")
    
    engine = ScreeningEngine()
    
    # Check if there are any job descriptions
    jds = execute_query("SELECT id, title FROM job_descriptions LIMIT 1", fetch_all=True)
    
    if jds:
        jd_id = jds[0]['id']
        print(f"Testing with JD: {jds[0]['title']} (ID: {jd_id})\n")
        
        result = engine.screen_candidates(jd_id, rescreen=True)
        
        print("=" * 60)
        print("SCREENING RESULTS")
        print("=" * 60)
        print(f"Success: {result['success']}")
        print(f"Total Candidates: {result['total_candidates']}")
        print(f"Screened: {result['screened_count']}")
        print(f"Longlist: {result['longlist_count']}")
        print(f"Shortlist: {result['shortlist_count']}")
        print(f"Average Score: {result['avg_score']}")
        print(f"Max Score: {result['max_score']}")
        print(f"Batch ID: {result['batch_id']}")
        
        if result['errors']:
            print(f"\nErrors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - {error}")
    else:
        print("❌ No job descriptions found in database")
        print("Please create a job description first")
