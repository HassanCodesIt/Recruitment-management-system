# 🎯 Quick Start Guide - Recruitment Management System

## ⚡ Fast Track to Running the System

### Step 1: Run Setup (One-Time)

Double-click `setup.bat` or run in terminal:
```bash
setup.bat
```

This will:
- ✅ Check Python installation
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Download Spacy model
- ✅ Create .env file

### Step 2: Configure Credentials

Edit `.env` file with your details:
```env
DB_PASSWORD=your_postgresql_password
EMAIL=your_email@gmail.com
PASSWORD=your_gmail_app_password
GROQ_API_KEY=your_groq_api_key
```

**Get Gmail App Password:** https://myaccount.google.com/apppasswords
**Get Groq API Key:** https://console.groq.com/

### Step 3: Initialize Database

```bash
python init_database.py
```

Expected output:
```
✅ Database 'recruitment_management_system' created successfully
✅ Database schema created successfully
📊 Created 8 tables
✅ All required tables exist
🎉 Database initialization completed successfully!
```

### Step 4: Run the Application

Double-click `run.bat` or:
```bash
streamlit run app.py
```

Browser opens at: `http://localhost:8501`

---

## 🎯 First-Time Workflow

### 1. Create a Job Description
- Go to "📋 Job Descriptions" page
- Click "Create/Edit JD" tab
- Fill in the form:
  - Job Title: "Senior Python Developer"
  - Description: "Looking for experienced Python developer..."
  - Required Skills: "Python, AWS, Docker"
  - Min Experience: 3 years
- Configure screening weights (or use defaults)
- Click "Save Job Description"

### 2. Add Candidates

**Option A: Fetch from Email**
- Go to "📧 CV Collection" → "Email Fetching"
- Click "🔄 Fetch Now"
- Click "🔍 Parse All Downloaded Resumes"

**Option B: Manual Upload**
- Go to "📧 CV Collection" → "Manual Upload"
- Upload PDF/DOCX files
- Click "🚀 Parse & Store Resumes"

### 3. Run AI Screening
- Go to "🔍 Screening & Shortlisting"
- Select your Job Description from dropdown
- Click "🚀 Run Screening"
- Wait for AI processing (shows progress)
- View results in 3 tabs:
  - 🎯 Shortlist (top candidates)
  - 📋 Longlist (extended list)
  - 📊 All Results (full data)

### 4.Review Candidates
- Go to "👥 Candidate Database"
- Search/filter candidates
- Click on any candidate to view:
  - Full parsed profile
  - Skills
  - Download original CV
  - Duplicate status (if any)

### 5. Get Recommendations
- Go to "💡 Vacancy Recommendations"
- Select a Job Description
- Click "💡 Generate Recommendations"
- Review AI-suggested candidates from database
- Mark as contacted and track responses

### 6. Monitor Analytics
- "📊 Dashboard" for overview
- "📈 Analytics & Reports" for trends
- Export data as CSV

---

## 🔧 Troubleshooting

### Database Connection Error
```
❌ Database connection failed
```

**Fix:**
1. Ensure PostgreSQL is running: `pg_ctl status`
2. Check credentials in `.env`
3. Verify database exists: `psql -l`

### Email Fetch Error
```
❌ Failed to connect to email
```

**Fix:**
1. Use app-specific password, not regular password
2. Enable IMAP in Gmail: Settings → Forwarding and POP/IMAP
3. Check `.env` EMAIL and PASSWORD

### No Candidates Found
```
⚠️ No candidates available for screening
```

**Fix:**
1. Upload or fetch CVs first
2. Check "Candidate Database" page
3. Ensure CVs were parsed successfully (check logs)

### LLM Parsing Fails
```
❌ Failed to parse resume
```

**Fix:**
1. Verify Groq API key is valid
2. Check API quota hasn't been exceeded
3. LLM will fallback to regex/Spacy extraction

---

## 📱 UI Navigation

```
└── 🏠 Sidebar
    ├── 📊 Dashboard           → KPIs, funnel, recent activity
    ├── 📧 CV Collection       → Fetch emails, upload CVs
    ├── 📋 Job Descriptions    → Create/manage JDs
    ├── 🔍 Screening           → Run AI screening
    ├── 👥 Candidate Database  → View/search candidates
    ├── 💡 Recommendations     → AI suggestions
    ├── 📈 Analytics           → Charts, trends, exports
    └── ⚙️ Settings            → Configuration, database
```

---

## 💡 Pro Tips

1. **Batch Upload**: Upload multiple CVs at once for efficiency
2. **Configure Weights**: Adjust screening weights per job type
3. **Export Data**: Download results as CSV for offline analysis
4. **Check Duplicates**: Review duplicate candidates before final selection
5. **Use Recommendations**: Don't miss great candidates from past applications
6. **Monitor Analytics**: Track recruitment pipeline health

---

## 📞 Need Help?

1. Check `README.md` for detailed documentation
2. Review `walkthrough.md` for implementation details
3. Check terminal logs for error details
4. Inspect database: `psql -d recruitment_management_system`

---

## 🚀 You're Ready!

The system is production-ready with:
- ✅ AI-powered CV parsing
- ✅ Intelligent screening
- ✅ Duplicate detection
- ✅ Vacancy recommendations
- ✅ Comprehensive analytics

**Start recruiting smarter today! 🎯**
