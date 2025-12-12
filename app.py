"""
Recruitment Management System - Main Streamlit Application
Complete AI-powered recruitment platform
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
import logging
from pathlib import Path

# Module imports
from modules.email_handler import EmailHandler, fetch_resumes_from_email
from modules.cv_parser import CVParser, parse_cv_file
from modules.duplicate_detector import DuplicateDetector, detect_duplicate_candidate
from modules.screening_engine import ScreeningEngine
from modules.recommendation_engine import RecommendationEngine, recommend_for_vacancy
from modules.analytics import AnalyticsEngine, get_dashboard_data
from database import (
    execute_query, insert_record, update_record, delete_record,
    get_all_records, get_record_by_id, test_connection
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Recruitment Management System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
   .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .success-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.selected_jd = None
    st.session_state.selected_candidate = None

# Sidebar navigation
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/4A90E2/FFFFFF?text=RMS+Logo", use_column_width=True)
    st.title("🎯 RMS Navigation")
    
    page = st.radio(
        "Select Page",
        [
            "📊 Dashboard",
            "📧 CV Collection",
            "📋 Job Descriptions",
            "🔍 Screening & Shortlisting",
            "👥 Candidate Database",
            "💡 Vacancy Recommendations",
            "📈 Analytics & Reports",
            "⚙️ Settings"
        ]
    )
    
    st.divider()
    
    # Quick stats in sidebar
    st.subheader("Quick Stats")
    try:
        total_candidates = execute_query(
            "SELECT COUNT(*) as count FROM candidates WHERE is_duplicate = FALSE",
            fetch_one=True
        )
        total_jds = execute_query(
            "SELECT COUNT(*) as count FROM job_descriptions WHERE status = 'active'",
            fetch_one=True
        )
        
        st.metric("Total Candidates", total_candidates['count'] if total_candidates else 0)
        st.metric("Active Jobs", total_jds['count'] if total_jds else 0)
    except Exception as e:
        st.warning("Database not initialized")

# ============================================================================
# PAGE 1: DASHBOARD
# ============================================================================
if page == "📊 Dashboard":
    st.markdown('<h1 class="main-header">📊 Recruitment Dashboard</h1>', unsafe_allow_html=True)
    
    try:
        # Get dashboard data
        analytics = AnalyticsEngine()
        kpis = analytics.get_dashboard_kpis()
        
        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Candidates",
                kpis['total_candidates'],
                delta=f"+{kpis['candidates_this_week']} this week"
            )
        
        with col2:
            st.metric(
                "Screened Candidates",
                kpis['screening_stats']['total_candidates_screened']
            )
        
        with col3:
            st.metric(
                "Shortlisted",
                kpis['screening_stats']['shortlisted_count']
            )
        
        with col4:
            st.metric(
                "Duplicate Rate",
                f"{kpis['duplicate_rate']}%",
                delta=None,
                delta_color="inverse"
            )
        
        st.divider()
        
        # Charts row
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Recruitment Funnel")
            funnel_data = kpis['funnel_data']
            
            fig = go.Figure(go.Funnel(
                y=["Total CVs", "Screened", "Longlisted", "Shortlisted", "Reviewed", "Hired"],
                x=[
                    funnel_data['total_cvs'],
                    funnel_data['screened'],
                    funnel_data['longlisted'],
                    funnel_data['shortlisted'],
                    funnel_data['reviewed'],
                    funnel_data['hired']
                ],
                textinfo="value+percent initial"
            ))
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📈 Candidates by Source")
            source_data = kpis['candidates_by_source']
            
            if source_data:
                df_source = pd.DataFrame(source_data)
                fig = px.pie(
                    df_source,
                    values='count',
                    names='source_type',
                    title="Source Distribution",
                    hole=0.3
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No candidate data available yet")
        
        # Recent Activity
        st.divider()
        st.subheader("🕒 Recent Activity")
        
        activities = kpis['recent_activity']
        
        if activities:
            for activity in activities[:10]:
                activity_type = activity['activity_type']
                icon = "📝" if activity_type == "candidate_added" else "🔍"
                
                col1, col2, col3 = st.columns([1, 4, 2])
                with col1:
                    st.write(icon)
                with col2:
                    st.write(f"**{activity['title']}** - {activity.get('details', '')}")
                with col3:
                    st.write(f"{activity['timestamp'].strftime('%Y-%m-%d %H:%M')}")
        else:
            st.info("No recent activity")
    
    except Exception as e:
        st.error(f"❌ Error loading dashboard: {e}")
        st.info("Please ensure the database is initialized. Run: `python init_database.py`")

# ============================================================================
# PAGE 2: CV COLLECTION
# ============================================================================
elif page == "📧 CV Collection":
    st.markdown('<h1 class="main-header">📧 CV Collection</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📥 Email Fetching", "📤 Manual Upload"])
    
    with tab1:
        st.subheader("Fetch Resumes from Email")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("📧 Configure your email credentials in the .env file")
            st.write(f"**Email:** {os.getenv('EMAIL', 'Not configured')}")
        
        with col2:
            if st.button("🔄 Fetch Now", type="primary", use_container_width=True):
                with st.spinner("Fetching resumes from email..."):
                    handler = EmailHandler()
                    result = handler.fetch_resumes()
                    
                    if result['success']:
                        st.success(f"✅ Fetched {result['resumes_found']} resumes from {result['emails_checked']} emails")
                        
                        if result['resumes_saved']:
                            st.subheader("Downloaded Resumes")
                            for resume in result['resumes_saved']:
                                st.write(f"📎 **{resume['filename']}** from {resume['sender']}")
                                
                            # Auto-parse option
                            if st.button("🔍 Parse All Downloaded Resumes"):
                                parser = CVParser()
                                detector = DuplicateDetector()
                                
                                progress_bar = st.progress(0)
                                parsed_count = 0
                                
                                for idx, resume in enumerate(result['resumes_saved']):
                                    # Parse resume
                                    candidate_data = parser.parse_resume(resume['filepath'])
                                    
                                    if candidate_data:
                                        # Check for duplicates
                                        is_dup, reason, match, confidence = detector.detect_duplicate(candidate_data)
                                        
                                        # Prepare for database
                                        candidate_data['source_type'] = 'email'
                                        candidate_data['is_duplicate'] = is_dup
                                        
                                        if is_dup and match:
                                            candidate_data['duplicate_of'] = match['id']
                                            candidate_data['duplicate_confidence'] = confidence
                                        
                                        # Read file bytes for storage
                                        with open(resume['filepath'], 'rb') as f:
                                            candidate_data['resume_file'] = f.read()
                                        
                                        # Insert into database
                                        insert_record("candidates", candidate_data)
                                        parsed_count += 1
                                    
                                    progress_bar.progress((idx + 1) / len(result['resumes_saved']))
                                
                                st.success(f"✅ Parsed and stored {parsed_count} candidates")
                                st.rerun()
                    else:
                        st.error(f"❌ Error fetching resumes: {result['errors']}")
    
    with tab2:
        st.subheader("Upload Resumes Manually")
        
        uploaded_files = st.file_uploader(
            "Upload Resume Files (PDF, DOCX)",
            type=['pdf', 'docx', 'doc'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.write(f"📁 Selected {len(uploaded_files)} files")
            
            if st.button("🚀 Parse & Store Resumes", type="primary"):
                # Create upload directory
                upload_dir = Path("uploads/resumes")
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                parser = CVParser()
                detector = DuplicateDetector()
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                results = {
                    "success": 0,
                    "failed": 0,
                    "duplicates": 0
                }
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_text.write(f"Processing: {uploaded_file.name}")
                    
                    try:
                        # Save file temporarily
                        temp_path = upload_dir / uploaded_file.name
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Parse resume
                        candidate_data = parser.parse_resume(str(temp_path))
                        
                        if candidate_data:
                            # Check duplicates
                            is_dup, reason, match, confidence = detector.detect_duplicate(candidate_data)
                            
                            candidate_data['source_type'] = 'upload'
                            candidate_data['is_duplicate'] = is_dup
                            
                            if is_dup and match:
                                candidate_data['duplicate_of'] = match['id']
                                candidate_data['duplicate_confidence'] = confidence
                                results["duplicates"] += 1
                            
                            # Store file bytes
                            with open(temp_path, 'rb') as f:
                                candidate_data['resume_file'] = f.read()
                            
                            # Insert into database
                            insert_record("candidates", candidate_data)
                            results["success"] += 1
                        else:
                            results["failed"] += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing {uploaded_file.name}: {e}")
                        results["failed"] += 1
                    
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                status_text.empty()
                progress_bar.empty()
                
                # Show summary
                st.success(f"✅ Successfully processed {results['success']} resumes")
                if results["duplicates"] > 0:
                    st.warning(f"⚠️ Found {results['duplicates']} duplicates")
                if results["failed"] > 0:
                    st.error(f"❌ Failed to process {results['failed']} files")
                
                st.rerun()

# ============================================================================
# PAGE 3: JOB DESCRIPTIONS
# ============================================================================
elif page == "📋 Job Descriptions":
    st.markdown('<h1 class="main-header">📋 Job Description Management</h1>', unsafe_allow_html= True)
    
    tab1, tab2 = st.tabs(["📝 Create/Edit JD", "📚 JD Library"])
    
    with tab1:
        st.subheader("Create New Job Description")
        
        with st.form("jd_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Job Title *", placeholder="e.g., Senior Software Engineer")
                department = st.text_input("Department", placeholder="e.g., Engineering")
                location = st.text_input("Location", placeholder="e.g., New York, Remote")
            
            with col2:
                req_exp_min = st.number_input("Minimum Experience (years)", min_value=0, value=0)
                req_exp_max = st.number_input("Maximum Experience (years)", min_value=0, value=10)
                status = st.selectbox("Status", ["active", "closed", "on_hold"])
            
            description = st.text_area(
                "Job Description *",
                height=200,
                placeholder="Enter detailed job description..."
            )
            
            required_skills = st.text_area(
                "Required Skills (comma-separated)",
                placeholder="Python, AWS, Docker, React..."
            )
            
            certifications = st.text_area(
                "Required Certifications (optional)",
                placeholder="AWS Certified, PMP..."
            )
            
            st.subheader("⚙️ Screening Configuration")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                semantic_weight = st.slider("Semantic Weight (%)",0, 100, 70) / 100
            with col2:
                skill_weight = st.slider("Skill Weight (%)", 0, 100, 30) / 100
            with col3:
                exp_weight = st.slider("Experience Weight (%)", 0, 100, 0) / 100
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                min_threshold = st.number_input("Minimum Score Threshold", 0, 100, 50)
            with col2:
                longlist_pct = st.slider("Longlist %", 10, 100, 50) / 100
            with col3:
                shortlist_pct = st.slider("Shortlist %", 5, 50, 20) / 100
            
            submitted = st.form_submit_button("💾 Save Job Description", type="primary")
            
            if submitted:
                if title and description:
                    matching_config = {
                        "semantic_weight": semantic_weight,
                        "skill_weight": skill_weight,
                        "experience_weight": exp_weight,
                        "min_score_threshold": min_threshold,
                        "longlist_percentage": longlist_pct,
                        "shortlist_percentage": shortlist_pct
                    }
                    
                    jd_data = {
                        "title": title,
                        "description": description,
                        "department": department,
                        "location": location,
                        "required_skills": required_skills,
                        "required_experience_min": req_exp_min,
                        "required_experience_max": req_exp_max if req_exp_max > 0 else None,
                        "required_certifications": certifications,
                        "status": status,
                        "matching_config": json.dumps(matching_config),
                        "created_at": datetime.now()
                    }
                    
                    jd_id = insert_record("job_descriptions", jd_data)
                    
                    if jd_id:
                        st.success(f"✅ Job Description created successfully! (ID: {jd_id})")
                        st.rerun()
                    else:
                        st.error("❌ Failed to create job description")
                else:
                    st.error("❌ Please fill in all required fields (marked with *)")
    
    with tab2:
        st.subheader("Job Description Library")
        
        # Filters
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_query = st.text_input("🔍 Search JDs", placeholder="Search by title...")
        with col2:
            status_filter = st.selectbox("Status Filter", ["all", "active", "closed", "on_hold"])
        with col3:
            sort_by = st.selectbox("Sort By", ["created_at DESC", "title ASC"])
        
        # Query JDs
        query = "SELECT * FROM job_descriptions WHERE 1=1"
        params = []
        
        if search_query:
            query += " AND title ILIKE %s"
            params.append(f"%{search_query}%")
        
        if status_filter != "all":
            query += " AND status = %s"
            params.append(status_filter)
        
        query += f" ORDER BY {sort_by}"
        
        jds = execute_query(query, tuple(params) if params else None, fetch_all=True)
        
        if jds:
            st.write(f"Found {len(jds)} job descriptions")
            
            for jd in jds:
                with st.expander(f"📋 {jd['title']} - {jd['department']} ({jd['status']})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Department:** {jd['department']}")
                        st.write(f"**Location:** {jd['location']}")
                        st.write(f"**Experience:** {jd['required_experience_min']}+ years")
                        st.write(f"**Created:** {jd['created_at'].strftime('%Y-%m-%d')}")
                        
                        # Show description in a text area instead of nested expander
                        st.write("**Full Description:**")
                        st.text_area(
                            "Description", 
                            value=jd['description'], 
                            height=150, 
                            disabled=True,
                            label_visibility="collapsed",
                            key=f"desc_{jd['id']}"
                        )
                        
                        if jd['required_skills']:
                            st.write(f"**Required Skills:**")
                            st.code(jd['required_skills'])
                    
                    with col2:
                        if st.button(f"🔍 Screen Candidates", key=f"screen_{jd['id']}"):
                            st.session_state.selected_jd = jd['id']
                            st.rerun()
                        
                        if st.button(f"💡 Get Recommendations", key=f"recommend_{jd['id']}"):
                            st.session_state.selected_jd = jd['id']
                            # Will redirect to recommendations page
                        
                        if st.button(f"🗑️ Delete", key=f"delete_{jd['id']}"):
                            delete_record("job_descriptions", jd['id'])
                            st.success("✅ Deleted successfully")
                            st.rerun()
        else:
            st.info("No job descriptions found. Create one above!")

# Continue in next message due to length...
# CONTINUATION OF APP.PY - ADD THIS TO THE END OF app.py

# ============================================================================
# PAGE 4: SCREENING & SHORTLISTING
# ============================================================================
elif page == "🔍 Screening & Shortlisting":
    st.markdown('<h1 class="main-header">🔍 AI-Powered Screening</h1>', unsafe_allow_html=True)
    
    # Select JD
    jds = get_all_records("job_descriptions", where="status = 'active'", order_by="created_at DESC")
    
    if not jds:
        st.warning("⚠️ No active job descriptions found. Please create one first!")
    else:
        selected_jd_id = st.selectbox(
            "Select Job Description",
            options=[jd['id'] for jd in jds],
            format_func=lambda x: next((jd['title'] for jd in jds if jd['id'] == x), "")
        )
        
        if selected_jd_id:
            jd = get_record_by_id("job_descriptions", selected_jd_id)
            
            # Show JD summary
            with st.expander("📋 View Job Description Details"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Title:** {jd['title']}")
                    st.write(f"**Department:** {jd['department']}")
                    st.write(f"**Location:** {jd['location']}")
                with col2:
                    st.write(f"**Experience:** {jd['required_experience_min']}+ years")
                    if jd['required_skills']:
                        st.write(f"**Required Skills:** {jd['required_skills']}")
            
            col1, col2 = st.columns([3, 1])
            
            with col2:
                if st.button("🚀 Run Screening", type="primary"):
                    with st.spinner("Running AI screening engine..."):
                        engine = ScreeningEngine()
                        result = engine.screen_candidates(selected_jd_id, rescreen=True)
                        
                        if result['success']:
                            st.success(f"✅ Screening complete!")
                            st.metric("Candidates Scored", result['screened_count'])
                            st.metric("Shortlisted", result['shortlist_count'])
                            st.metric("Average Score", f"{result['avg_score']:.1f}")
                            st.rerun()
                        else:
                            st.error(f"❌ Screening failed: {result['errors']}")
            
            # Display results
            st.divider()
            
            tab1, tab2, tab3 = st.tabs(["🎯 Shortlist", "📋 Longlist", "📊 All Results"])
            
            with tab1:
                st.subheader("🎯 Shortlisted Candidates")
                shortlist = execute_query("""
                    SELECT 
                        sr.*,
                        c.name, c.email, c.phone, c.experience_years
                    FROM screening_results sr
                    JOIN candidates c ON sr.candidate_id = c.id
                    WHERE sr.job_description_id = %s AND sr.in_shortlist = TRUE
                    ORDER BY sr.final_score DESC
                """, (selected_jd_id,), fetch_all=True)
                
                if shortlist:
                    df = pd.DataFrame(shortlist)
                    
                    display_df = df[[
                        'rank_position', 'name', 'email', 'experience_years',
                        'final_score', 'semantic_score', 'skill_match_score',
                        'matched_skills', 'missing_skills', 'status'
                    ]]
                    
                    st.dataframe(
                        display_df.style.background_gradient(
                            subset=['final_score'],
                            cmap='Greens'
                        ),
                        use_container_width=True,
                        height=400
                    )
                    
                    # Export button
                    csv = display_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download Shortlist CSV",
                        csv,
                        f"shortlist_{jd['title'].replace(' ', '_')}.csv",
                        "text/csv"
                    )
                else:
                    st.info("No candidates in shortlist. Run screening first.")
            
            with tab2:
                st.subheader("📋 Longlisted Candidates")
                longlist = execute_query("""
                    SELECT 
                        sr.*,
                        c.name, c.email, c.phone, c.experience_years
                    FROM screening_results sr
                    JOIN candidates c ON sr.candidate_id = c.id
                    WHERE sr.job_description_id = %s AND sr.in_longlist = TRUE
                    ORDER BY sr.final_score DESC
                """, (selected_jd_id,), fetch_all=True)
                
                if longlist:
                    df = pd.DataFrame(longlist)
                    
                    display_df = df[[
                        'rank_position', 'name', 'email', 'experience_years',
                        'final_score', 'matched_skills', 'missing_skills'
                    ]]
                    
                    st.dataframe(display_df, use_container_width=True, height=400)
                else:
                    st.info("No candidates in longlist")
            
            with tab3:
                st.subheader("📊 All Screening Results")
                
                all_results = execute_query("""
                    SELECT 
                        sr.*,
                        c.name, c.email, c.phone, c.experience_years
                    FROM screening_results sr
                    JOIN candidates c ON sr.candidate_id = c.id
                    WHERE sr.job_description_id = %s
                    ORDER BY sr.final_score DESC
                """, (selected_jd_id,), fetch_all=True)
                
                if all_results:
                    df = pd.DataFrame(all_results)
                    
                    # Score distribution chart
                    fig = px.histogram(
                        df,
                        x='final_score',
                        nbins=20,
                        title="Score Distribution",
                        labels={'final_score': 'Final Score', 'count': 'Number of Candidates'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Full results table
                    st.dataframe(df, use_container_width=True, height=400)
                else:
                    st.info("No screening results available")

# ============================================================================
# PAGE 5: CANDIDATE DATABASE
# ============================================================================
elif page == "👥 Candidate Database":
    st.markdown('<h1 class="main-header">👥 Candidate Database</h1>', unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_name = st.text_input("🔍 Search by Name")
    with col2:
        search_email = st.text_input("📧 Search by Email")
    with col3:
        source_filter = st.selectbox("Source", ["all", "email", "upload", "manual"])
    with col4:
        show_duplicates = st.checkbox("Show Duplicates", value=False)
    
    # Build query
    query = "SELECT * FROM candidates WHERE 1=1"
    params = []
    
    if search_name:
        query += " AND name ILIKE %s"
        params.append(f"%{search_name}%")
    
    if search_email:
        query += " AND email ILIKE %s"
        params.append(f"%{search_email}%")
    
    if source_filter != "all":
        query += " AND source_type = %s"
        params.append(source_filter)
    
    if not show_duplicates:
        query += " AND is_duplicate = FALSE"
    
    query += " ORDER BY created_at DESC LIMIT 100"
    
    candidates = execute_query(query, tuple(params) if params else None, fetch_all=True)
    
    if candidates:
        st.write(f"Found {len(candidates)} candidates")
        
        # Summary cards
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_exp = sum(c.get('experience_years', 0) for c in candidates) / len(candidates)
            st.metric("Average Experience", f"{avg_exp:.1f} years")
        with col2:
            with_email = sum(1 for c in candidates if c.get('email'))
            st.metric("With Email", f"{with_email}/{len(candidates)}")
        with col3:
            duplicates = sum(1 for c in candidates if c.get('is_duplicate'))
            st.metric("Duplicates Detected", duplicates)
        
        st.divider()
        
        # Candidate cards
        for candidate in candidates:
            with st.expander(
                f"{'❌ [DUP] ' if candidate.get('is_duplicate') else ''}👤 {candidate['name']} - {candidate.get('email', 'No email')}"
            ):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**Email:** {candidate.get('email', 'N/A')}")
                    st.write(f"**Phone:** {candidate.get('phone', 'N/A')}")
                    st.write(f"**Experience:** {candidate.get('experience_years', 0)} years")
                
                with col2:
                    st.write(f"**Source:** {candidate.get('source_type', 'Unknown')}")
                    st.write(f"**Added:** {candidate.get('created_at').strftime('%Y-%m-%d %H:%M') if candidate.get('created_at') else 'N/A'}")
                    st.write(f"**File:** {candidate.get('source_file', 'N/A')}")
                
                with col3:
                    if candidate.get('resume_file'):
                        # Convert memoryview to bytes for Streamlit download button
                        resume_data = bytes(candidate['resume_file']) if isinstance(candidate['resume_file'], memoryview) else candidate['resume_file']
                        st.download_button(
                            "📄 Download CV",
                            resume_data,
                            file_name=candidate.get('source_file', 'resume.pdf'),
                            key=f"download_{candidate['id']}"
                        )
                    
                    if st.button("🗑️ Delete", key=f"del_{candidate['id']}"):
                        delete_record("candidates", candidate['id'])
                        st.success("✅ Deleted")
                        st.rerun()
                
                # Show details
                if candidate.get('summary'):
                    st.write("**Summary:**")
                    st.write(candidate['summary'])
                
                if candidate.get('skills'):
                    st.write("**Skills:**")
                    st.code(candidate['skills'])
                
                if candidate.get('is_duplicate'):
                    st.warning(f"⚠️ Duplicate of candidate ID: {candidate.get('duplicate_of')} (Confidence: {candidate.get('duplicate_confidence', 0):.0%})")
    
    else:
        st.info("No candidates found. Upload some resumes to get started!")

# ============================================================================
# PAGE 6: VACANCY RECOMMENDATIONS
# ============================================================================
elif page == "💡 Vacancy Recommendations":
    st.markdown('<h1 class="main-header">💡 Vacancy Recommendations</h1>', unsafe_allow_html=True)
    
    st.info("🤖 AI recommends past candidates for new job openings")
    
    # Select JD
    jds = get_all_records("job_descriptions", order_by="created_at DESC")
    
    if jds:
        selected_jd_id = st.selectbox(
            "Select Job Description",
            options=[jd['id'] for jd in jds],
            format_func=lambda x: next((jd['title'] for jd in jds if jd['id'] == x), "")
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            top_n = st.number_input("Number of Recommendations", 5, 50, 10)
        
        with col3:
            if st.button("💡 Generate Recommendations", type="primary"):
                with st.spinner("Analyzing candidate database..."):
                    result = recommend_for_vacancy(selected_jd_id, top_n=top_n)
                    
                    if result['success']:
                        st.success(f"✅ Generated {result['recommendations_count']} recommendations!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result['errors']}")
        
        # Display recommendations
        st.divider()
        
        recommendations = execute_query("""
            SELECT 
                vr.*,
                c.name, c.email, c.phone, c.experience_years, c.skills
            FROM vacancy_recommendations vr
            JOIN candidates c ON vr.candidate_id = c.id
            WHERE vr.job_description_id = %s
            ORDER BY vr.recommendation_score DESC
        """, (selected_jd_id,), fetch_all=True)
        
        if recommendations:
            st.subheader(f"🎯 Top {len(recommendations)} Recommended Candidates")
            
            for i, rec in enumerate(recommendations, 1):
                with st.expander(f"#{i} {rec['name']} - Score: {rec['recommendation_score']:.1f}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Email:** {rec['email']}")
                        st.write(f"**Phone:** {rec['phone']}")
                        st.write(f"**Experience:** {rec['experience_years']} years")
                        st.write(f"**Skills:** {rec.get('skills', 'N/A')}")
                        st.write(f"**Match Reasoning:** {rec['match_reasoning']}")
                    
                    with col2:
                        contacted = rec.get('was_contacted', False)
                        
                        if not contacted:
                            if st.button("📧 Mark as Contacted", key=f"contact_{rec['id']}"):
                                update_record("vacancy_recommendations", rec['id'], {
                                    "was_contacted": True,
                                    "contacted_at": datetime.now()
                                })
                                st.success("✅ Marked as contacted")
                                st.rerun()
                        else:
                            st.success("✅ Contacted")
                            
                            response = st.selectbox(
                                "Response",
                                ["interested", "not_interested", "no_response"],
                                key=f"response_{rec['id']}"
                            )
                            
                            if st.button("💾 Save Response", key=f"save_{rec['id']}"):
                                update_record("vacancy_recommendations", rec['id'], {
                                    "candidate_response": response
                                })
                                st.success("✅ Saved")
                                st.rerun()
        
        else:
            st.info("No recommendations yet. Click 'Generate Recommendations' above!")
    
    else:
        st.warning("No job descriptions found. Create one first!")

# ============================================================================
# PAGE 7: ANALYTICS & REPORTS
# ============================================================================
elif page == "📈 Analytics & Reports":
    st.markdown('<h1 class="main-header">📈 Analytics & Reports</h1>', unsafe_allow_html=True)
    
    analytics = AnalyticsEngine()
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        days_range = st.selectbox("Time Period", [7, 14, 30, 60, 90], index=2)
    
    # Get trends
    trends = analytics.get_trends_data(days=days_range)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Daily Candidates Added")
        if trends['daily_candidates']:
            df = pd.DataFrame(trends['daily_candidates'])
            fig = px.bar(df, x='date', y='count', title="Candidates by Day")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")
    
    with col2:
        st.subheader("🔍 Daily Screenings")
        if trends['daily_screenings']:
            df = pd.DataFrame(trends['daily_screenings'])
            fig = px.line(df, x='date', y='count', title="Screenings by Day")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")
    
    st.divider()
    
    # Download reports
    st.subheader("📥 Export Reports")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export All Candidates"):
            candidates = get_all_records("candidates", where="is_duplicate = FALSE")
            if candidates:
                df = pd.DataFrame(candidates)
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "candidates_report.csv",
                    "text/csv"
                )
    
    with col2:
        if st.button("📊 Export Screening Results"):
            results = execute_query("SELECT * FROM screening_results ORDER BY final_score DESC", fetch_all=True)
            if results:
                df = pd.DataFrame(results)
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "screening_results.csv",
                    "text/csv"
                )
    
    with col3:
        if st.button("📊 Export Analytics Summary"):
            kpis = analytics.get_dashboard_kpis()
            summary = {
                "Total Candidates": kpis['total_candidates'],
                "Candidates This Month": kpis['candidates_this_month'],
                "Duplicate Rate": kpis['duplicate_rate'],
                "Screened Candidates": kpis['screening_stats']['total_candidates_screened'],
                "Shortlisted": kpis['screening_stats']['shortlisted_count'],
                "Average Score": kpis['screening_stats']['avg_score']
            }
            df = pd.DataFrame([summary])
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "analytics_summary.csv",
                "text/csv"
            )

# ============================================================================
# PAGE 8: SETTINGS
# ============================================================================
elif page == "⚙️ Settings":
    st.markdown('<h1 class="main-header">⚙️ System Settings</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🔧 Configuration", "🗄️ Database", "ℹ️ System Info"])
    
    with tab1:
        st.subheader("⚙️ System Configuration")
        
        # Get current config
        config = execute_query(
            "SELECT * FROM system_config WHERE config_key = 'duplicate_threshold'",
            fetch_one=True
        )
        
        with st.form("config_form"):
            st.write("**Duplicate Detection Thresholds**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                name_threshold = st.slider(
                    "Name Similarity Threshold",
                    50, 100,
                    int(os.getenv("DUPLICATE_NAME_THRESHOLD", 85))
                )
            
            with col2:
                phone_threshold = st.slider(
                    "Phone Similarity Threshold",
                    50, 100,
                    int(os.getenv("DUPLICATE_PHONE_THRESHOLD", 90))
                )
            
            if st.form_submit_button("💾 Save Configuration"):
                new_config = {
                    "name_similarity": name_threshold,
                    "phone_similarity": phone_threshold
                }
                
                update_record("system_config", config['id'], {
                    "config_value": json.dumps(new_config)
                })
                
                st.success("✅ Configuration saved!")
    
    with tab2:
        st.subheader("🗄️ Database Management")
        
        # Test connection
        if st.button("🔍 Test Database Connection"):
            if test_connection():
                st.success("✅ Database connection successful!")
            else:
                st.error("❌ Database connection failed!")
        
        # Show stats
        st.write("**Database Statistics:**")
        
        tables = execute_query("""
            SELECT table_name,
                   pg_total_relation_size(quote_ident(table_name)) as size
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY size DESC
        """, fetch_all=True)
        
        if tables:
            df = pd.DataFrame(tables)
            df['size_mb'] = df['size'] / (1024 * 1024)
            st.dataframe(df[['table_name', 'size_mb']], use_container_width=True)
        
        # Warning section for dangerous operations
        st.divider()
        st.subheader("⚠️ Danger Zone")
        
        if st.checkbox("Show dangerous operations"):
            if st.button("🗑️ Clear All Screening Results", type="secondary"):
                if st.session_state.get('confirm_clear_screening'):
                    execute_query("DELETE FROM screening_results")
                    st.success("✅ Cleared all screening results")
                    st.session_state.confirm_clear_screening = False
                else:
                    st.session_state.confirm_clear_screening = True
                    st.warning("⚠️ Click again to confirm deletion")
    
    with tab3:
        st.subheader("ℹ️ System Information")
        
        st.write("**Environment:**")
        st.code(f"""
Database: {os.getenv('DB_NAME')}
Host: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}
Email: {os.getenv('EMAIL')}
        """)
        
        st.write("**Version Information:**")
        st.code("""
RMS Version: 1.0.0
Python: 3.11+
Streamlit: 1.31.0
        """)
        
        st.write("**Installed Modules:**")
        modules_status = {
            "Email Handler": "✅ Active",
            "CV Parser": "✅ Active",
            "Duplicate Detector": "✅ Active",
            "Screening Engine": "✅ Active",
            "Recommendation Engine": "✅ Active",
            "Analytics": "✅ Active"
        }
        
        for module, status in modules_status.items():
            st.write(f"**{module}:** {status}")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>🎯 Recruitment Management System v1.0 | Powered by AI</p>
    <p>Built with Streamlit, PostgreSQL, Groq, and Sentence Transformers</p>
</div>
""", unsafe_allow_html=True)
