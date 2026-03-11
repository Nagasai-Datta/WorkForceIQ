# WorkforceIQ — Enterprise Workforce Skill & Utilization Analytics Platform

A full-stack AI-powered internal tool for enterprises to analyze employee skills,
optimize project allocation, and predict attrition risk using Machine Learning.

Built with Flask, PostgreSQL (Supabase), and Scikit-learn.

---

## Project Scope

This platform solves a real enterprise problem — HR and Project Managers currently
rely on static spreadsheets to track workforce data. This leads to:

- Some employees being overworked while others sit idle
- HR having no way to predict who might quit
- No central view of what skills the team has vs what projects need

WorkforceIQ centralizes all of this into one role-based web application.

---

## Features

### HR Manager

- View all employees, filter by skill and department
- See attrition risk score (ML prediction) per employee
- Skill gap analysis — which skills have low coverage
- Full analytics dashboard with charts

### Project Manager

- Live utilization heatmap (green/yellow/red per employee load)
- Create projects, assign employees to projects
- System automatically blocks over-allocation (>100%)
- Update project status (Draft → Active → Completed)

### Employee

- View own profile, assigned projects, skill list
- Edit profile (satisfaction score, hours, department)
- Add skills manually or paste resume text for AI extraction
- Privacy toggle for contact info visibility

### Admin

- Create new users with any role
- Delete users
- Change roles of existing users
- Full access to all dashboards

---

## Machine Learning

### Model 1 — Attrition Prediction (Random Forest)

- **Algorithm:** Random Forest Classifier (150 trees)
- **Training data:** 1000 synthetic employees generated in code
- **Features used:** years_experience, satisfaction_score, monthly_hours,
  total_allocation_percentage, num_projects
- **Output:** Risk level (High / Medium / Low) + probability percentage
- **Accuracy:** ~78–82% on test split
- **When it trains:** Automatically on first app startup, saves to `ml/models/attrition_model.pkl`

### Model 2 — Skill Extraction (TF-IDF)

- **Algorithm:** TF-IDF (Term Frequency–Inverse Document Frequency)
- **Input:** Free-form resume text pasted by employee
- **Output:** List of detected skills matched against the skills database
- **No training needed** — pure mathematical text vectorization
- **How it works:** Scores each word by importance, matches against
  a skill alias dictionary (e.g. "k8s" → Kubernetes, "reactjs" → React)

---

## Database Schema (Supabase PostgreSQL)

```
users              → login credentials + role
employees          → profile data (name, dept, satisfaction, experience)
skills             → master skill list
employee_skills    → which employee has which skill + proficiency level (1–5)
projects           → project details + status lifecycle
assignments        → employee ↔ project mapping + allocation %
utilization_reports→ workload history per employee
```

### Project Status Lifecycle

```
Draft → Validating → Active → Paused → Completed
                          ↑_______↓ (can loop back if attrition risk found)
```

---

## Authentication & Authorization

- Passwords stored as **Werkzeug PBKDF2-SHA256 hashes** — never plain text
- Role stored in **Flask server-side session** after login
- Every route protected by `@role_required()` decorator
- Wrong role attempting access → 403 Forbidden page

### Role Permissions

| Role              | Access                                         |
| ----------------- | ---------------------------------------------- |
| `employee`        | Own dashboard, profile, skills only            |
| `project_manager` | Heatmap, projects, allocation                  |
| `hr`              | All employees, attrition analytics, skill gaps |
| `admin`           | Everything + user management                   |

---

## Tech Stack

| Layer      | Technology                                 |
| ---------- | ------------------------------------------ |
| Backend    | Python 3, Flask 3.0                        |
| Database   | PostgreSQL via Supabase (cloud)            |
| ML         | Scikit-learn (Random Forest + TF-IDF)      |
| Frontend   | HTML5, CSS3, Vanilla JavaScript            |
| Charts     | Chart.js                                   |
| Auth       | Werkzeug password hashing + Flask sessions |
| Deployment | Railway / Render / PythonAnywhere          |

---

## Project Structure

```
wfiq/
├── app.py                  # Entry point — registers all blueprints, starts ML
├── config.py               # App config (secret key, DB URL)
├── db.py                   # Database connection + query helpers
├── auth_utils.py           # login_required and role_required decorators
├── seed_passwords.py       # One-time script to set demo account passwords
├── requirements.txt        # All Python dependencies
├── Procfile                # For Railway/Render deployment
├── .env                    # Your secrets (never commit this)
│
├── ml/
│   ├── train_attrition.py  # Generates synthetic data + trains Random Forest
│   └── skill_extractor.py  # TF-IDF resume skill extraction
│
├── routes/
│   ├── auth.py             # /login  /logout
│   ├── hr.py               # /hr/dashboard  /hr/employees  /hr/analytics
│   ├── pm.py               # /pm/dashboard  /pm/projects  /pm/assign
│   ├── employee.py         # /employee/dashboard  /employee/profile
│   └── admin.py            # /admin/dashboard  /admin/create-user
│
└── templates/
    ├── base.html           # Shared sidebar + navbar (all pages extend this)
    ├── login.html          # Login page
    ├── 403.html            # Access denied page
    ├── hr/                 # HR templates
    ├── pm/                 # Project Manager templates
    ├── employee/           # Employee templates
    └── admin/              # Admin templates
```

---

## Local Setup (Step by Step)

### Prerequisites

- Python 3.10 or higher
- pip
- A Supabase account (free)

### Step 1 — Clone the repo

```bash
git clone https://github.com/YOURNAME/workforce-iq.git
cd workforce-iq
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Set up Supabase database

1. Go to supabase.com → create a new project
2. Open SQL Editor → paste and run the contents of `schema.sql`
3. Copy your database connection URI from Settings → Database

### Step 4 — Configure environment

Create a `.env` file in the project root:

```
SECRET_KEY=any-random-string-you-want
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxx.supabase.co:5432/postgres
```

### Step 5 — Seed demo passwords (run once only)

```bash
python seed_passwords.py
```

You should see 5 green checkmarks. If you see a DB error, check your DATABASE_URL.

### Step 6 — Run the app

```bash
python app.py
```

Open `http://localhost:8080` in your browser.

---

## Demo Accounts

All accounts use password: `password123`

| Username       | Role            | Dashboard                            |
| -------------- | --------------- | ------------------------------------ |
| `admin`        | Admin           | User management + all access         |
| `hr_manager`   | HR Manager      | Attrition, skill gaps, employee list |
| `proj_manager` | Project Manager | Heatmap, project allocation          |
| `emp_john`     | Employee        | Profile, skills, projects            |
| `emp_sarah`    | Employee        | Profile, skills, projects            |

---

## Retraining the ML Model

The attrition model trains automatically on startup using synthetic data.
The model file is saved at `ml/models/attrition_model.pkl`.

To force a retrain (e.g. after adding more employees):

```bash
# Delete the saved model so it retrains on next startup
rm ml/models/attrition_model.pkl
python app.py
```

As you add real employees through the app, their data feeds into
predictions immediately — no retraining needed for predictions,
only if you want to update the training distribution.

---

## SDLC Model Used

**Agile** — developed in iterative sprints:

1. Requirements & user stories
2. Database schema design
3. Authentication module
4. Core CRUD modules (employees, projects, skills)
5. ML integration (attrition + skill extraction)
6. Dashboard & visualization
7. Testing & deployment

---

## 👤 Authors

- **Name:** M Naga Sai
- **Reg No:** 23BCE0757

- **Name:** Adarsh Anand
- **Reg No:** 23BCE0807

- **Name:** M Naga Sai
- **Reg No:** 23BCE2047

- **Course:** Software Engineering Lab
