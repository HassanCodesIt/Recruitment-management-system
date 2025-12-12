# 🎯 Recruitment Management System (RMS)

## Complete AI-Powered Recruitment Platform

A comprehensive, production-ready recruitment management system with automated CV collection, AI-based parsing, intelligent screening, duplicate detection, vacancy recommendations, and advanced analytics.

---

## ✨ Features

### 1. **Automated CV Collection** 📧
- Fetch resumes from Gmail inbox automatically
- Extract PDF/DOCX attachments
- Track email processing with detailed logs

### 2. **AI-Based CV Parsing & Data Extraction** 🤖
- Multi-method text extraction (PDFMiner, PDFPlumber, OCR)
- LLM-powered structured data extraction (Groq/Llama)
- Spacy NER for entity recognition
- Extracts: name, email, phone, skills, experience, education, projects, certifications

### 3. **AI-Driven Screening & Shortlisting** 🔍
- Semantic similarity matching using Sentence Transformers
- Skill-based keyword matching
- Experience validation
- Configurable weighted scoring
- Automated longlist and shortlist generation
- Comprehensive audit trail

### 4. **Customizable Matching Criteria** ⚙️
- Configure semantic similarity weight
- Adjust skill match weight
- Set experience requirements
- Define score thresholds
- Custom longlist/shortlist percentages

### 5. **Candidate Duplicate Detection** 🔍
- Exact email matching
- Phone number normalization and matching
- Fuzzy name matching (Token Set Ratio)
- Configurable similarity thresholds
- Automatic duplicate flagging with confidence scores

### 6. **Future Vacancy Recommendations** 💡
- ML-based candidate recommendations for new roles
- Cross-matching historical candidates against new JDs
- Match reasoning and score explanation
- Contact tracking and response management

### 7. **Reporting & Analytics Dashboard** 📊
- Real-time KPIs (total candidates, screening stats, duplicate rate)
- Recruitment funnel visualization
- Candidate source distribution
- Daily trends and charts
- Export reports to CSV

### 8. **RESTful API Integration** 🔌
- FastAPI endpoints for all operations
- CRUD operations for candidates and JDs
- Screening and recommendation triggers
- Dashboard metrics API

### 9. **Comprehensive Streamlit UI** 🖥️
- **Dashboard**: KPIs, funnel, recent activity
- **CV Collection**: Email fetching, manual upload, bulk processing
- **Job Descriptions**: Create/edit JDs, configure matching criteria
- **Screening**: Run AI screening, view shortlists/longlists
- **Candidate Database**: Search, filter, view profiles, download CVs
- **Vacancy Recommendations**: AI-powered candidate suggestions
- **Analytics**: Trends, charts, export reports
- **Settings**: System configuration, database management

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **PostgreSQL 12+**
- **Gmail account** with app-specific password (for email fetching)
- **Groq API key** (for LLM-based parsing)

### Installation

1. **Clone/Navigate to the project directory**
   ```bash
   cd c:\Users\91807\Desktop\n8n_Agents\Recruitment_Manasgement_System
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # OR
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download Spacy model**
   ```bash
   python -m spacy download en_core_web_sm
   ```

5. **Configure environment variables**
   - Copy `.env.template` to `.env`
   - Update the following variables:
     ```env
     DB_NAME=recruitment_management_system
     DB_USER=postgres
     DB_PASSWORD=your_password
     DB_HOST=localhost
     DB_PORT=5432
     
     EMAIL=your_email@gmail.com
     PASSWORD=your_app_specific_password
     
     GROQ_API_KEY=your_groq_api_key
     ```

6. **Initialize the database**
   ```bash
   python init_database.py
   ```
   
   This will:
   - Create the database
   - Execute schema creation
   - Set up indexes and views
   - Insert default configuration

7. **Run the application**
   ```bash
   streamlit run app.py
   ```
   
   The app will open at: `http://localhost:8501`

---

## 📁 Project Structure

```
Recruitment_Management_System/
│
├── app.py                      # Main Streamlit application
├── database.py                 # Database connection and utilities
├── init_database.py            # Database initialization script
├── database_schema.sql         # PostgreSQL schema
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
│
├── modules/                    # Core feature modules
│   ├── __init__.py
│   ├── email_handler.py        # Email fetching and resume extraction
│   ├── cv_parser.py           # AI-powered CV parsing
│   ├── duplicate_detector.py  # Fuzzy matching for duplicates
│   ├── screening_engine.py    # AI screening and shortlisting
│   ├── recommendation_engine.py # Vacancy recommendations
│   └── analytics.py           # KPIs and reporting
│
├── uploads/                    # File storage
│   └── resumes/               # Uploaded/fetched resumes
│
├── PDF_to_DB module/          # Legacy PDF parsing module
├── email_fetch module/        # Legacy email fetching module
└── README.md                  # This file
```

---

## 🔧 Configuration

### Duplicate Detection Thresholds
Edit in `.env`:
```env
DUPLICATE_NAME_THRESHOLD=85    # Name similarity % (50-100)
DUPLICATE_PHONE_THRESHOLD=90  # Phone similarity % (50-100)
```

### Screening Weights
Configure per Job Description in the UI, or set defaults in `.env`:
```env
DEFAULT_SEMANTIC_WEIGHT=0.7     # Semantic similarity importance
DEFAULT_SKILL_WEIGHT=0.3        # Skill match importance
DEFAULT_EXPERIENCE_WEIGHT=0.0   # Experience match importance
MIN_SCORE_THRESHOLD=50          # Minimum passing score
```

### Email Fetching
- Uses Gmail IMAP
- Requires app-specific password (not regular Gmail password)
- Generate here: https://myaccount.google.com/apppasswords

---

## 📊 Database Schema

### Core Tables

- **candidates**: Candidate profiles with parsed CV data
- **job_descriptions**: JD requirements and matching config
- **screening_results**: AI screening scores and rankings
- **screening_history**: Audit trail of screening operations
- **vacancy_recommendations**: ML-based candidate recommendations
- **email_logs**: Email fetching activity tracker
- **analytics_metrics**: KPI calculations and trends
- **system_config**: System-wide configuration

### Views

- **active_candidates**: Non-duplicate candidates
- **latest_screening_summary**: Screening stats by JD
- **duplicate_candidates_report**: Duplicate detection results

---

## 🧪 Testing

### Test Database Initialization
```bash
python init_database.py
```

### Test Email Fetching
```bash
python -m modules.email_handler
```

### Test CV Parsing
```bash
python -m modules.cv_parser "path/to/resume.pdf"
```

### Test Duplicate Detection
```bash
python -m modules.duplicate_detector
```

### Test Screening Engine
```bash
python -m modules.screening_engine
```

### Test Recommendation Engine
```bash
python -m modules.recommendation_engine
```

### Test Analytics
```bash
python -m modules.analytics
```

---

## 🎯 Usage Workflow

### 1. **Set Up Job Descriptions**
- Go to "Job Descriptions" page
- Create a new JD with requirements
- Configure screening weights

### 2. **Collect Candidates**
- **Option A**: Fetch from email
  - Go to "CV Collection" → "Email Fetching"
  - Click "Fetch Now"
  - Auto-parse fetched resumes
  
- **Option B**: Manual upload
  - Go to "CV Collection" → "Manual Upload"
  - Upload PDF/DOCX files
  - Click "Parse & Store Resumes"

### 3. **Run Screening**
- Go to "Screening & Shortlisting"
- Select a Job Description
- Click "Run Screening"
- View shortlist and longlist

### 4. **Review Candidates**
- Check "Candidate Database" for all profiles
- View duplicate detections
- Download CVs

### 5. **Get Recommendations**
- Go to "Vacancy Recommendations"
- Select a JD
- Click "Generate Recommendations"
- Review AI-suggested candidates

### 6. **Monitor Analytics**
- Dashboard shows real-time KPIs
- "Analytics & Reports" page for trends
- Export data as CSV

---

## 🔌 API Endpoints (Optional FastAPI Integration)

If you want to add API access, create `api/main.py`:

```python
from fastapi import FastAPI
from modules.screening_engine import ScreeningEngine

app = FastAPI()

@app.post("/api/screening/run/{jd_id}")
def run_screening(jd_id: int):
    engine = ScreeningEngine()
    result = engine.screen_candidates(jd_id)
    return result

# Add other endpoints...
```

Run with:
```bash
uvicorn api.main:app --reload
```

---

## 🐛 Troubleshooting

### Database Connection Failed
- Check PostgreSQL is running: `pg_isready`
- Verify credentials in `.env`
- Ensure database exists

### Email Fetching Not Working
- Use app-specific password, not regular password
- Enable IMAP in Gmail settings
- Check firewall allows port 993

### CV Parsing Returns Empty Data
- Install Tesseract OCR for scanned PDFs
- Check Groq API key is valid
- Verify file format (PDF/DOCX only)

### Duplicate Detection Not Working
- Ensure candidates have email or phone
- Adjust thresholds in Settings page
- Check database has existing candidates

---

## 📈 Performance Tips

1. **Database Indexing**: Already optimized with indexes on frequently queried columns
2. **Batch Processing**: Upload multiple CVs at once for efficiency
3. **Embedding Caching**: Consider caching embeddings for large candidate databases
4. **Connection Pooling**: Already implemented in `database.py`

---

## 🔐 Security Considerations

- **API Keys**: Never commit `.env` to version control
- **Database**: Use strong passwords, restrict network access
- **Email**: Use app-specific passwords, not main credentials
- **File Uploads**: Validate file types and sizes
- **SQL Injection**: All queries use parameterized statements

---

## 🚧 Future Enhancements

- [ ] Multi-user support with authentication
- [ ] Email notifications for screening results
- [ ] Interview scheduling integration
- [ ] Video interview analysis
- [ ] Advanced ML models (BERT, GPT-4)
- [ ] Mobile app
- [ ] Integration with ATS systems

---

## 📝 License

Proprietary - Internal Use Only

---

## 👥 Support

For issues or questions:
- Check troubleshooting section above
- Review logs in terminal
- Inspect database with: `psql -d recruitment_management_system`

---

## 🎉 Acknowledgments

Built with:
- **Streamlit** - Web UI framework
- **PostgreSQL** - Database
- **Groq/Llama** - LLM for CV parsing
- **Sentence Transformers** - Semantic matching
- **Spacy** - Named Entity Recognition
- **TheFuzz** - Fuzzy matching
- **Plotly** - Data visualization

---

**Version**: 1.0.0  
**Last Updated**: December 2025  
**Status**: Production Ready ✅
