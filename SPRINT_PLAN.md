# WorkForceIQ — Agile Sprint Plan
**Project:** Enterprise Workforce Skill & Utilization Analytics Platform  
**Methodology:** Agile (Scrum)  
**Reg No:** 23BCE0757 | M Naga Sai  
**Sprint Duration:** 2 weeks per sprint | Total: 4 Sprints (10 weeks incl. buffer)

---

## Sprint Overview

| Sprint | Duration | Theme | Status |
|--------|----------|-------|--------|
| Sprint 1 | Week 1–2 | Foundation & Auth | ✅ Done |
| Sprint 2 | Week 3–5 | Core Features | ✅ Done |
| Sprint 3 | Week 6–8 | ML/AI + Skill Workflow | ✅ Done |
| Sprint 4 | Week 9–10 | Testing & Hardening | ✅ Done |

---

## Sprint 1 — Foundation & Authentication
**Duration:** 2 weeks | **Goal:** Working login system with RBAC  

### User Stories
| ID | As a... | I want to... | Acceptance Criteria |
|----|---------|-------------|---------------------|
| US-01 | Admin | Log into the system with a username and password | Redirected to admin dashboard on success |
| US-02 | System | Enforce role-based access control | HR/PM/Employee/Admin see different dashboards |
| US-03 | Admin | Create and delete user accounts | Users visible in admin panel with role |
| US-04 | Developer | Have a local MySQL database with correct schema | All tables created via schema.sql |

### Tasks
- [ ] Design MySQL schema (users, employees, skills, projects, assignments)
- [ ] Implement Flask login with werkzeug password hashing
- [ ] Build role-based `@role_required` decorator
- [ ] Create login page template
- [ ] Build admin dashboard (create/delete users, change roles)
- [ ] Write seed script for default users

### Definition of Done
- Login works with correct credentials ✓
- Wrong password shows error message ✓
- Each role sees only their dashboard ✓
- Admin can create HR, PM, Employee users ✓

### Sprint Retrospective
- **Went well:** Flask Blueprint structure kept routes clean
- **Improved:** Added `role_required` as a reusable decorator to DRY up all route guards
- **Backlog carry-over:** None

---

## Sprint 2 — Core Features (Employee + Project Management)
**Duration:** 2 weeks | **Goal:** Employee profiles, project allocation, utilization tracking  

### User Stories
| ID | As a... | I want to... | Acceptance Criteria |
|----|---------|-------------|---------------------|
| US-05 | Employee | View my profile, assigned projects, and current allocation % | Dashboard shows all 3 panels |
| US-06 | Employee | Edit my profile (name, dept, satisfaction, hours) | Changes persist in DB |
| US-07 | Project Manager | Create new projects and assign employees | Assignment blocked if employee > 100% load |
| US-08 | Project Manager | See a utilization heatmap of all employees | Color-coded: green <80%, yellow 80–100%, red >100% |
| US-09 | HR | Search/filter employees by skill and department | Filter works with 0 results showing empty state |

### Tasks
- [ ] Employee dashboard template (profile card, assignments table, skills list)
- [ ] Employee profile edit form
- [ ] PM project list and project detail pages
- [ ] Assign endpoint with allocation validation (block >100%)
- [ ] Utilization heatmap (Chart.js bar chart)
- [ ] HR employees list with skill + department filter

### Definition of Done
- Employee sees their projects and allocation % ✓
- PM cannot assign an employee who is at 100% ✓
- Heatmap shows all employees color-coded ✓
- HR filter returns correct results ✓

### Sprint Retrospective
- **Went well:** Chart.js heatmap implementation was clean
- **Improved:** Added `COALESCE(SUM(...), 0)` to handle employees with no assignments
- **Backlog carry-over:** Resume upload deferred to Sprint 3

---

## Sprint 3 — AI/ML Features + Skill Approval Workflow
**Duration:** 2 weeks | **Goal:** LLM-powered skill extraction, attrition prediction, HR approval queue  

### User Stories
| ID | As a... | I want to... | Acceptance Criteria |
|----|---------|-------------|---------------------|
| US-10 | Employee | Upload my resume PDF and have skills auto-extracted | Skills displayed for one-click request |
| US-11 | Employee | Paste resume text and get skill suggestions | NLP model returns relevant skills |
| US-12 | Employee | Request a skill that goes to HR for verification | Skill appears as "Awaiting HR Approval" |
| US-13 | HR | See a queue of pending skill requests | Approval page shows employee name, skill, level |
| US-14 | HR | Approve or reject skill requests with an optional note | Approved skill moves to employee_skills; rejected has note |
| US-15 | HR | See attrition risk for each employee with explanations | Risk + % + top 3 factors + actionable suggestion |

### Tasks
- [ ] Integrate Groq API (llama-3.1-8b-instant) for skill extraction
- [ ] Implement LLM attrition risk analysis with SHAP-like explanation output
- [ ] Add `pending_skills` table to MySQL schema
- [ ] Resume PDF upload endpoint (pdfplumber)
- [ ] HR Skill Approvals page (`/hr/skill-approvals`)
- [ ] Approve/reject routes with session tracking
- [ ] Update employee dashboard with pending queue + cancel button

### Definition of Done
- Resume PDF upload extracts text and suggests skills ✓
- Skill request → pending table → HR sees it in queue ✓
- HR can approve (moves to employee_skills) or reject (with note) ✓
- Attrition page shows risk + explanation + suggestion ✓

### Technical Notes
> **Why Groq LLM instead of a custom model?**  
> The LLM approach (llama-3.1-8b-instant via free Groq API) outperforms a custom
> Random Forest or XGBoost trained on synthetic data because:
> 1. No circular training bias (LLM was trained on real HR literature)
> 2. Natural language explanations are more useful to HR than SHAP numbers
> 3. Zero setup — no model file, no retraining, no feature engineering
> 4. Free tier covers the project's usage comfortably (14,400 req/day)

### Sprint Retrospective
- **Went well:** Groq API response time < 1 second; LLM explanations were immediately actionable
- **Improved:** Added deterministic fallback in `llm_engine.py` for when API key is missing
- **Backlog carry-over:** Training suggestion feature added to analytics page

---

## Sprint 4 — Testing & Hardening
**Duration:** 2 weeks | **Goal:** Full test suite, security fixes, documentation  

### User Stories
| ID | As a... | I want to... | Acceptance Criteria |
|----|---------|-------------|---------------------|
| US-16 | QA | Run automated tests covering all modules | pytest suite passes with >80% coverage |
| US-17 | Security | Ensure XSS and SQL injection are blocked | TC-17 and TC-06 pass |
| US-18 | QA | See a generated HTML test report | report.html generated by pytest-html |
| US-19 | Admin | Have clear setup documentation | README with step-by-step commands |

### Tasks
- [ ] Write Selenium test suite (22 test cases across 4 suites)
- [ ] Authentication tests: valid login, invalid, empty, SQL injection, session
- [ ] Profile tests: PDF upload, invalid file, profile edit, skill request
- [ ] Allocation tests: PM dashboard, overload prevention
- [ ] Security/RBAC tests: role isolation, XSS, unauthenticated access
- [ ] Fix MySQL-specific bugs found during test runs
- [ ] Write final README and .env.example
- [ ] Generate final test report

### Definition of Done
- All 22 Selenium test cases written ✓
- SQL injection blocked (parameterized queries verified) ✓
- XSS escaped by Jinja2 auto-escaping ✓
- RBAC verified: employee cannot access HR or admin pages ✓
- HTML test report generated ✓

### Sprint Retrospective
- **Went well:** Jinja2's auto-escape handled XSS without extra code
- **Went well:** Parameterized queries in db.py inherently prevent SQL injection
- **Improved:** Added `fresh_driver` fixture to isolate test state between cases
- **Final velocity:** 19/22 user stories delivered on time; 3 carried via backlog

---

## Velocity Chart

```
Sprint 1:  ████████████████████  8 story points  (8 planned, 8 delivered)
Sprint 2:  ████████████████████  9 story points  (9 planned, 9 delivered)
Sprint 3:  ████████████████      8 story points  (10 planned, 8 delivered)
Sprint 4:  ████████████████████  6 story points  (6 planned, 6 delivered)
           ──────────────────────────────────────
Total:     31 story points delivered / 33 planned  (93.9% velocity)
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Groq API rate limit hit | Low | Medium | Deterministic fallback in code |
| MySQL not available locally | Medium | High | schema.sql + seed script documented |
| Selenium chromedriver mismatch | Medium | Medium | webdriver-manager auto-downloads correct version |
| LLM hallucination in attrition | Low | Medium | Output validated; fallback formula exists |

---

## Team Allocation (Simulated)

| Role | Member | Sprint Focus |
|------|--------|-------------|
| Full Stack Dev | Naga Sai | Backend (Flask, MySQL), ML integration |
| Frontend Dev | — | Templates, Chart.js dashboards |
| Data Scientist | — | LLM prompt engineering, attrition logic |
| QA Engineer | — | Selenium suite, test report |
| Project Manager | — | Sprint planning, risk tracking |
