"""
Recommendation Engine Module - Future Vacancy Recommendations
Suggests past candidates for new job openings using ML-based matching
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from database import execute_query, insert_record

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """ML-based candidate recommendation for new vacancies"""
    
    def __init__(self):
        # Load embedding model
        logger.info("Loading sentence transformer model for recommendations...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Model loaded")
    
    def get_candidate_profiles(self, min_experience: int = 0, 
                              exclude_rejected: bool = True) -> List[Dict]:
        """Get candidate profiles from database"""
        query = """
            SELECT 
                id, name, email, phone, skills, text_content,
                experience_years, summary, education, experience,
                created_at
            FROM candidates
            WHERE is_duplicate = FALSE
        """
        
        if min_experience > 0:
            query += f" AND experience_years >= {min_experience}"
        
        if exclude_rejected:
            # Exclude candidates who were rejected in past screenings
            query += """
                AND id NOT IN (
                    SELECT candidate_id FROM screening_results
                    WHERE status = 'rejected'
                )
            """
        
        query += " ORDER BY created_at DESC"
        
        candidates = execute_query(query, fetch_all=True)
        return candidates or []
    
    def compute_candidate_jd_similarity(self, candidate_text: str, jd_text: str) -> float:
        """Compute similarity between candidate profile and JD"""
        if not candidate_text or not jd_text:
            return 0.0
        
        # Limit text length
        candidate_text = candidate_text[:2000]
        jd_text = jd_text[:2000]
        
        # Generate embeddings
        embeddings = self.embedder.encode([candidate_text, jd_text])
        
        # Compute cosine similarity
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        
        # Convert to 0-100 scale
        return float(similarity * 100)
    
    def generate_match_reasoning(self, candidate: Dict, jd: Dict, score: float) -> str:
        """Generate human-readable reasoning for the match"""
        reasons = []
        
        # Experience match
        if jd.get('required_experience_min'):
            req_exp = jd['required_experience_min']
            cand_exp = candidate.get('experience_years', 0)
            
            if cand_exp >= req_exp:
                reasons.append(f"Has {cand_exp} years of experience (required: {req_exp}+)")
            else:
                gap = req_exp - cand_exp
                reasons.append(f"Experience gap of {gap} years")
        
        # Skills match (simple keyword matching)
        if jd.get('required_skills') and candidate.get('skills'):
            jd_skills = set(s.strip().lower() for s in str(jd['required_skills']).replace('\n', ',').split(',') if s.strip())
            cand_skills = set(s.strip().lower() for s in str(candidate['skills']).replace('\n', ',').split(',') if s.strip())
            
            matched = jd_skills.intersection(cand_skills)
            
            if matched:
                reasons.append(f"Matching skills: {', '.join(list(matched)[:3])}")
        
        # Overall score
        if score >= 80:
            reasons.append("Excellent semantic profile match")
        elif score >= 60:
            reasons.append("Good profile alignment")
        else:
            reasons.append("Partial profile match")
        
        return "; ".join(reasons) if reasons else "Based on profile similarity"
    
    def recommend_candidates(self, jd_id: int, top_n: int = 10, 
                           min_score: float = 50.0) -> Dict:
        """
        Recommend candidates for a job description
        
        Args:
            jd_id: Job description ID
            top_n: Number of top recommendations to return
            min_score: Minimum similarity score threshold
        
        Returns:
            Summary dict with recommendations
        """
        logger.info(f"🔍 Generating recommendations for JD ID: {jd_id}")
        
        summary = {
            "success": False,
            "jd_id": jd_id,
            "total_candidates_evaluated": 0,
            "recommendations_count": 0,
            "recommendations": [],
            "errors": []
        }
        
        try:
            # Get job description
            jd = execute_query(
                "SELECT * FROM job_descriptions WHERE id = %s",
                (jd_id,),
                fetch_one=True
            )
            
            if not jd:
                summary["errors"].append(f"Job description {jd_id} not found")
                return summary
            
            # Get JD text
            jd_text = jd.get('description', '')
            
            if not jd_text:
                summary["errors"].append("Job description has no content")
                return summary
            
            # Get candidate profiles
            min_exp = jd.get('required_experience_min', 0)
            candidates = self.get_candidate_profiles(min_experience=min_exp)
            
            summary["total_candidates_evaluated"] = len(candidates)
            
            if not candidates:
                summary["errors"].append("No suitable candidates found in database")
                return summary
            
            logger.info(f"📊 Evaluating {len(candidates)} candidates...")
            
            # Calculate similarity scores for all candidates
            candidate_scores = []
            
            for candidate in candidates:
                # Build candidate text from available fields
                cand_text_parts = [
                    candidate.get('text_content', ''),
                    candidate.get('summary', ''),
                    candidate.get('experience', ''),
                    candidate.get('skills', '')
                ]
                cand_text = ' '.join(filter(None, cand_text_parts))
                
                if not cand_text.strip():
                    continue
                
                # Compute similarity
                score = self.compute_candidate_jd_similarity(cand_text, jd_text)
                
                if score >= min_score:
                    # Generate reasoning
                    reasoning = self.generate_match_reasoning(candidate, jd, score)
                    
                    candidate_scores.append({
                        "candidate": candidate,
                        "score": score,
                        "reasoning": reasoning
                    })
            
            # Sort by score descending
            candidate_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # Take top N
            top_recommendations = candidate_scores[:top_n]
            
            summary["recommendations_count"] = len(top_recommendations)
            
            # Store recommendations in database
            for rec in top_recommendations:
                candidate = rec['candidate']
                
                # Check if recommendation already exists
                existing = execute_query("""
                    SELECT id FROM vacancy_recommendations
                    WHERE job_description_id = %s AND candidate_id = %s
                """, (jd_id, candidate['id']), fetch_one=True)
                
                if not existing:
                    rec_data = {
                        "job_description_id": jd_id,
                        "candidate_id": candidate['id'],
                        "recommendation_score": rec['score'],
                        "match_reasoning": rec['reasoning'],
                        "recommended_at": datetime.now()
                    }
                    
                    insert_record("vacancy_recommendations", rec_data)
                
                # Add to summary
                summary["recommendations"].append({
                    "candidate_id": candidate['id'],
                    "name": candidate['name'],
                    "email": candidate['email'],
                    "phone": candidate['phone'],
                    "experience_years": candidate.get('experience_years', 0),
                    "score": round(rec['score'], 2),
                    "reasoning": rec['reasoning']
                })
            
            summary["success"] = True
            logger.info(f"✅ Generated {len(top_recommendations)} recommendations")
            
        except Exception as e:
            logger.error(f"❌ Recommendation generation failed: {e}")
            summary["errors"].append(str(e))
        
        return summary
    
    def get_recommendations(self, jd_id: int) -> List[Dict]:
        """Get stored recommendations for a job description"""
        recommendations = execute_query("""
            SELECT 
                vr.*,
                c.name, c.email, c.phone, c.experience_years,
                c.skills, c.source_file
            FROM vacancy_recommendations vr
            JOIN candidates c ON vr.candidate_id = c.id
            WHERE vr.job_description_id = %s
            ORDER BY vr.recommendation_score DESC
        """, (jd_id,), fetch_all=True)
        
        return recommendations or []


def recommend_for_vacancy(jd_id: int, top_n: int = 10) -> Dict:
    """Convenience function to generate recommendations"""
    engine = RecommendationEngine()
    return engine.recommend_candidates(jd_id, top_n=top_n)


if __name__ == "__main__":
    # Test the recommendation engine
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 Testing Recommendation Engine\n")
    
    # Check if there are any job descriptions
    jds = execute_query("SELECT id, title FROM job_descriptions LIMIT 1", fetch_all=True)
    
    if jds:
        jd_id = jds[0]['id']
        print(f"Testing with JD: {jds[0]['title']} (ID: {jd_id})\n")
        
        result = recommend_for_vacancy(jd_id, top_n=5)
        
        print("=" * 60)
        print("RECOMMENDATION RESULTS")
        print("=" * 60)
        print(f"Success: {result['success']}")
        print(f"Candidates Evaluated: {result['total_candidates_evaluated']}")
        print(f"Recommendations: {result['recommendations_count']}")
        
        if result['recommendations']:
            print("\nTop Recommendations:")
            for i, rec in enumerate(result['recommendations'], 1):
                print(f"\n{i}. {rec['name']} (Score: {rec['score']})")
                print(f"   Email: {rec['email']}")
                print(f"   Experience: {rec['experience_years']} years")
                print(f"   Reasoning: {rec['reasoning']}")
        
        if result['errors']:
            print(f"\nErrors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - {error}")
    else:
        print("❌ No job descriptions found in database")
        print("Please create a job description first")
