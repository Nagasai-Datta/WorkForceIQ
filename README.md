# WorkForceIQ — Enterprise Workforce Analytics Platform

**Reg No:** 23BCE0757 | M Naga Sai

**Reg No:** 23BCE0807 | Adarsh Anand

**Reg No:** 23BCE2047 | Suhani Agarwal

**Stack:** Python · Flask · MySQL (local) · Groq LLM API · Selenium

---

## What This Does

A full-stack internal HR tool that:

- Tracks employee skills, projects, and utilization across roles (HR / PM / Employee / Admin)
- Parses PDF resumes using NLP to auto-suggest skills for HR approval
- Predicts employee attrition risk using a free LLM (Groq / LLaMA 3.1) with plain-English explanations
- Enforces an HR skill approval workflow before any skill is added to an employee profile

---

## Tech Stack

| Layer       | Technology                                 |
| ----------- | ------------------------------------------ |
| Backend     | Python 3.11 + Flask 3.0                    |
| Database    | MySQL (local)                              |
| AI / ML     | Groq API — llama-3.1-8b-instant (free)     |
| PDF Parsing | pdfplumber                                 |
| Auth        | Werkzeug password hashing + Flask sessions |
| Frontend    | Jinja2 templates + Chart.js                |
| Testing     | Selenium (Python library) + pytest         |

---

## Setup — Step by Step

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Create the MySQL database

```bash
# Open MySQL (you must have MySQL running locally)
mysql -u root -p
```

Then inside MySQL:

```sql
CREATE DATABASE workforceiq;
EXIT;
```

Then load the schema:

```bash
mysql -u root -p workforceiq < schema.sql
```

### 3. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
SECRET_KEY=any-long-random-string
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=workforceiq
GROQ_API_KEY=gsk_...        ← get this free at console.groq.com
```

### 4. Get your FREE Groq API key (2 minutes)

1. Go to **https://console.groq.com** → Sign up
2. Click **API Keys** → **Create API Key** → copy it
3. Paste it into `.env` as `GROQ_API_KEY=gsk_...`

### 5. Create demo users

```bash
python3 seed_passwords.py
```

This creates:

| Username | Password   | Role            |
| -------- | ---------- | --------------- |
| admin    | Admin@123  | Admin           |
| hr1      | Hr@123456  | HR Manager      |
| pm1      | Pm@123456  | Project Manager |
| emp1     | Emp@123456 | Employee        |

### 6. Run the app

```bash
cd WorkForceIQ
source venv/bin/activate
python3 app.py
```

Open **http://localhost:8080** in your browser.

---

## Running the Test Suite (Selenium)

### What is this?

These are Python scripts that automatically control Chrome — opening pages, clicking buttons, filling forms — and check the results. This is the **Selenium Python library**, not the Chrome browser extension. You do not need to manually install chromedriver; `webdriver-manager` downloads the right one for your Chrome version automatically.

### Install test dependencies

```bash
pip install selenium pytest pytest-html webdriver-manager requests
```

### Run tests

**Terminal 1** — start the Flask app:

```bash
cd WorkForceIQ
source venv/bin/activate
python3 app.py
```

**Terminal 2** — run all 20 test cases and generate HTML report:

```bash
cd WorkForceIQ
source venv/bin/activate
pytest tests -v

(For generating a report as HTML file)

pytest tests/ -v --html=tests/report.html
```

The file `tests/report.html` is your printable test report (open it in Chrome).

### Run a single suite

```bash
pytest tests/test_TC01_TC04_authentication.py -v
pytest tests/test_TC16_TC20_security_performance.py -v
```

### Test coverage (matches your PDF exactly)

| Test File                              | TC IDs         | Module                 |
| -------------------------------------- | -------------- | ---------------------- |
| test_TC01_TC04_authentication.py       | TC-01 to TC-04 | Authentication         |
| test_TC05_TC08_profile_management.py   | TC-05 to TC-08 | Profile Management     |
| test_TC09_TC12_project_allocation.py   | TC-09 to TC-12 | Project Allocation     |
| test_TC13_TC15_analytics.py            | TC-13 to TC-15 | Analytics              |
| test_TC16_TC20_security_performance.py | TC-16 to TC-20 | Security + Performance |

---

## Project Structure

```
WorkForceIQ/
├── app.py                    # Flask entry point
├── config.py                 # Config from .env
├── db.py                     # MySQL connection layer
├── auth_utils.py             # @role_required decorator
├── schema.sql                # Run once to create all tables
├── seed_passwords.py         # Creates demo users
├── requirements.txt
├── .env.example              # Copy to .env and fill in
├── SPRINT_PLAN.md            # Agile sprint documentation
│
├── ml/
│   ├── llm_engine.py         # Groq API integration (skill extraction + attrition)
│   ├── skill_extractor.py    # Thin wrapper over llm_engine
│   └── train_attrition.py    # Attrition prediction (LLM-based, no training needed)
│
├── routes/
│   ├── auth.py               # Login / logout
│   ├── hr.py                 # HR dashboard, employees, analytics, skill approvals
│   ├── pm.py                 # Project Manager dashboard, assign, create project
│   ├── employee.py           # Employee dashboard, profile, PDF upload, skill request
│   └── admin.py              # User management
│
├── templates/                # Jinja2 HTML templates per role
│
├── uploads/                  # Resume PDFs stored here (gitignored)
│
└── tests/
    ├── conftest.py                              # Selenium fixtures + Page helper
    ├── test_TC01_TC04_authentication.py         # TC-01 to TC-04
    ├── test_TC05_TC08_profile_management.py     # TC-05 to TC-08
    ├── test_TC09_TC12_project_allocation.py     # TC-09 to TC-12
    ├── test_TC13_TC15_analytics.py              # TC-13 to TC-15
    └── test_TC16_TC20_security_performance.py   # TC-16 to TC-20
```

---

## Skill Approval Workflow

```
Employee clicks "Request Skill"
        ↓
Saved to pending_skills table (status = pending)
        ↓
Employee sees "⏳ Awaiting HR Approval" on their dashboard
        ↓
HR sees amber alert: "N skill requests awaiting review"
        ↓
HR goes to /hr/skill-approvals
        ↓
✓ Approve → skill moves to employee_skills (shows on profile)
✕ Reject  → HR adds a reason note, employee can re-submit
```

---

## SDLC Model — Agile

See `SPRINT_PLAN.md` for the full 4-sprint breakdown with user stories,
tasks, definition of done, and retrospectives.
