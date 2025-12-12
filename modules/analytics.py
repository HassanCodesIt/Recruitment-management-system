"""
Analytics Module - Reporting & KPI Calculation
Generates recruitment metrics and dashboard data
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
from database import execute_query, insert_record

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Calculate and track recruitment KPIs and metrics"""
    
    def get_total_candidates(self, exclude_duplicates: bool = True) -> int:
        """Get total number of candidates"""
        query = "SELECT COUNT(*) as count FROM candidates"
        
        if exclude_duplicates:
            query += " WHERE is_duplicate = FALSE"
        
        result = execute_query(query, fetch_one=True)
        return result['count'] if result else 0
    
    def get_candidates_by_period(self, days: int = 30, exclude_duplicates: bool = True) -> int:
        """Get candidates added in the last N days"""
        query = """
            SELECT COUNT(*) as count 
            FROM candidates 
            WHERE created_at >= NOW() - INTERVAL '%s days'
        """ % days
        
        if exclude_duplicates:
            query += " AND is_duplicate = FALSE"
        
        result = execute_query(query, fetch_one=True)
        return result['count'] if result else 0
    
    def get_candidates_by_source(self) -> List[Dict]:
        """Get candidate distribution by source"""
        results = execute_query("""
            SELECT 
                source_type,
                COUNT(*) as count
            FROM candidates
            WHERE is_duplicate = FALSE
            GROUP BY source_type
            ORDER BY count DESC
        """, fetch_all=True)
        
        return results or []
    
    def get_duplicate_rate(self) -> float:
        """Calculate duplicate detection rate"""
        total = execute_query("SELECT COUNT(*) as count FROM candidates", fetch_one=True)
        duplicates = execute_query(
            "SELECT COUNT(*) as count FROM candidates WHERE is_duplicate = TRUE", 
            fetch_one=True
        )
        
        if total and total['count'] > 0:
            return (duplicates['count'] / total['count']) * 100
        
        return 0.0
    
    def get_screening_stats(self) -> Dict:
        """Get screening statistics"""
        stats = {
            "total_screenings": 0,
            "total_candidates_screened": 0,
            "avg_score": 0.0,
            "avg_time_to_shortlist": 0.0,
            "shortlisted_count": 0
        }
        
        # Total screenings
        result = execute_query(
            "SELECT COUNT(*) as count FROM screening_history",
            fetch_one=True
        )
        stats["total_screenings"] = result['count'] if result else 0
        
        # Candidates screened
        result = execute_query(
            "SELECT COUNT(DISTINCT candidate_id) as count FROM screening_results",
            fetch_one=True
        )
        stats["total_candidates_screened"] = result['count'] if result else 0
        
        # Average score
        result = execute_query(
            "SELECT AVG(final_score) as avg_score FROM screening_results",
            fetch_one=True
        )
        stats["avg_score"] = round(result['avg_score'], 2) if result and result['avg_score'] else 0.0
        
        # Shortlisted count
        result = execute_query(
            "SELECT COUNT(*) as count FROM screening_results WHERE in_shortlist = TRUE",
            fetch_one=True
        )
        stats["shortlisted_count"] = result['count'] if result else 0
        
        # Time to shortlist (placeholder - would need timestamp tracking)
        stats["avg_time_to_shortlist"] = 0.0
        
        return stats
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """Get recent system activity"""
        activities = []
        
        # Recent candidates
        recent_candidates = execute_query("""
            SELECT 
                'candidate_added' as activity_type,
                name as title,
                created_at as timestamp,
                source_type as details
            FROM candidates
            WHERE is_duplicate = FALSE
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,), fetch_all=True)
        
        if recent_candidates:
            activities.extend(recent_candidates)
        
        # Recent screenings
        recent_screenings = execute_query("""
            SELECT 
                'screening_completed' as activity_type,
                jd.title as title,
                sh.executed_at as timestamp,
                CONCAT(sh.shortlist_count, ' shortlisted') as details
            FROM screening_history sh
            JOIN job_descriptions jd ON sh.job_description_id = jd.id
            ORDER BY sh.executed_at DESC
            LIMIT %s
        """, (limit,), fetch_all=True)
        
        if recent_screenings:
            activities.extend(recent_screenings)
        
        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return activities[:limit]
    
    def get_funnel_data(self, jd_id: Optional[int] = None) -> Dict:
        """Get recruitment funnel data"""
        funnel = {
            "total_cvs": 0,
            "screened": 0,
            "longlisted": 0,
            "shortlisted": 0,
            "reviewed": 0,
            "hired": 0
        }
        
        if jd_id:
            # Funnel for specific JD
            query_filter = f"WHERE job_description_id = {jd_id}"
        else:
            # Overall funnel
            query_filter = ""
        
        # Total CVs (overall candidates)
        funnel["total_cvs"] = self.get_total_candidates()
        
        # Screened
        result = execute_query(
            f"SELECT COUNT(DISTINCT candidate_id) as count FROM screening_results {query_filter}",
            fetch_one=True
        )
        funnel["screened"] = result['count'] if result else 0
        
        # Longlisted
        result = execute_query(
            f"SELECT COUNT(*) as count FROM screening_results {query_filter} AND in_longlist = TRUE" if query_filter else
            "SELECT COUNT(*) as count FROM screening_results WHERE in_longlist = TRUE",
            fetch_one=True
        )
        funnel["longlisted"] = result['count'] if result else 0
        
        # Shortlisted
        result = execute_query(
            f"SELECT COUNT(*) as count FROM screening_results {query_filter} AND in_shortlist = TRUE" if query_filter else
            "SELECT COUNT(*) as count FROM screening_results WHERE in_shortlist = TRUE",
            fetch_one=True
        )
        funnel["shortlisted"] = result['count'] if result else 0
        
        # Reviewed
        result = execute_query(
            f"SELECT COUNT(*) as count FROM screening_results {query_filter} AND status IN ('reviewed', 'rejected', 'hired')" if query_filter else
            "SELECT COUNT(*) as count FROM screening_results WHERE status IN ('reviewed', 'rejected', 'hired')",
            fetch_one=True
        )
        funnel["reviewed"] = result['count'] if result else 0
        
        # Hired
        result = execute_query(
            f"SELECT COUNT(*) as count FROM screening_results {query_filter} AND status = 'hired'" if query_filter else
            "SELECT COUNT(*) as count FROM screening_results WHERE status = 'hired'",
            fetch_one=True
        )
        funnel["hired"] = result['count'] if result else 0
        
        return funnel
    
    def get_dashboard_kpis(self) -> Dict:
        """Get all KPIs for dashboard display"""
        kpis = {
            "total_candidates": self.get_total_candidates(),
            "candidates_this_month": self.get_candidates_by_period(30),
            "candidates_this_week": self.get_candidates_by_period(7),
            "duplicate_rate": round(self.get_duplicate_rate(), 2),
            "candidates_by_source": self.get_candidates_by_source(),
            "screening_stats": self.get_screening_stats(),
            "recent_activity": self.get_recent_activity(10),
            "funnel_data": self.get_funnel_data()
        }
        
        return kpis
    
    def get_trends_data(self, days: int = 30) -> Dict:
        """Get trend data for charts"""
        trends = {
            "daily_candidates": [],
            "daily_screenings": []
        }
        
        # Daily candidates
        daily_candidates = execute_query("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM candidates
            WHERE created_at >= NOW() - INTERVAL '%s days'
              AND is_duplicate = FALSE
            GROUP BY DATE(created_at)
            ORDER BY date
        """ % days, fetch_all=True)
        
        trends["daily_candidates"] = daily_candidates or []
        
        # Daily screenings
        daily_screenings = execute_query("""
            SELECT 
                DATE(executed_at) as date,
                COUNT(*) as count,
                AVG(avg_score) as avg_score
            FROM screening_history
            WHERE executed_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(executed_at)
            ORDER BY date
        """ % days, fetch_all=True)
        
        trends["daily_screenings"] = daily_screenings or []
        
        return trends
    
    def record_metric(self, metric_name: str, metric_value: float, 
                     category: str = "general", metadata: Dict = None):
        """Record a custom metric to the database"""
        try:
            metric_data = {
                "metric_name": metric_name,
                "metric_category": category,
                "metric_value": metric_value,
                "metric_data": metadata,
                "calculated_at": datetime.now()
            }
            
            insert_record("analytics_metrics", metric_data)
            logger.info(f"✅ Recorded metric: {metric_name} = {metric_value}")
            
        except Exception as e:
            logger.error(f"❌ Error recording metric: {e}")


def get_dashboard_data() -> Dict:
    """Convenience function to get all dashboard data"""
    analytics = AnalyticsEngine()
    return analytics.get_dashboard_kpis()


if __name__ == "__main__":
    # Test the analytics engine
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 Testing Analytics Engine\n")
    
    analytics = AnalyticsEngine()
    kpis = analytics.get_dashboard_kpis()
    
    print("=" * 60)
    print("DASHBOARD KPIs")
    print("=" * 60)
    print(f"Total Candidates: {kpis['total_candidates']}")
    print(f"Candidates This Month: {kpis['candidates_this_month']}")
    print(f"Candidates This Week: {kpis['candidates_this_week']}")
    print(f"Duplicate Rate: {kpis['duplicate_rate']}%")
    
    print("\nCandidates by Source:")
    for source in kpis['candidates_by_source']:
        print(f"  - {source['source_type']}: {source['count']}")
    
    print("\nScreening Stats:")
    stats = kpis['screening_stats']
    print(f"  Total Screenings: {stats['total_screenings']}")
    print(f"  Candidates Screened: {stats['total_candidates_screened']}")
    print(f"  Average Score: {stats['avg_score']}")
    print(f"  Shortlisted: {stats['shortlisted_count']}")
    
    print("\nFunnel Data:")
    funnel = kpis['funnel_data']
    print(f"  Total CVs: {funnel['total_cvs']}")
    print(f"  Screened: {funnel['screened']}")
    print(f"  Longlisted: {funnel['longlisted']}")
    print(f"  Shortlisted: {funnel['shortlisted']}")
    print(f"  Reviewed: {funnel['reviewed']}")
    print(f"  Hired: {funnel['hired']}")
    
    print("\nRecent Activity:")
    for activity in kpis['recent_activity'][:5]:
        print(f"  - [{activity['activity_type']}] {activity['title']}")
