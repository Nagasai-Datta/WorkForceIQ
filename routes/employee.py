import os
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, jsonify, current_app)
from werkzeug.utils import secure_filename
from auth_utils import role_required
from db import query_db, execute_db
from ml.skill_extractor import extract_skills_from_text, extract_skill_names

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

# ── helpers ──────────────────────────────────────────────────────────────────
def _allowed_file(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in
            current_app.config.get('ALLOWED_EXTENSIONS', {'pdf'}))

def _get_eid():
    return session.get('employee_id')

# ── Dashboard ─────────────────────────────────────────────────────────────────
@employee_bp.route('/dashboard')
@role_required('employee', 'admin')
def dashboard():
    eid = _get_eid()
    emp = query_db('''
        SELECT e.*,
               COALESCE(SUM(a.allocation_percentage),0) AS total_allocation,
               COUNT(a.assignment_id)                   AS num_projects
        FROM employees e
        LEFT JOIN assignments a ON e.employee_id=a.employee_id
        WHERE e.employee_id=%s 
    ''', (eid,), one=True)

    skills = query_db('''
        SELECT s.skill_id, s.skill_name, es.proficiency_level
        FROM employee_skills es JOIN skills s ON es.skill_id=s.skill_id
        WHERE es.employee_id=%s ORDER BY es.proficiency_level DESC
    ''', (eid,))

    # Pending skill requests (not yet approved)
    pending = query_db('''
        SELECT ps.pending_id, s.skill_name, ps.proficiency_level,
               ps.status, ps.submitted_at, ps.review_note
        FROM pending_skills ps JOIN skills s ON ps.skill_id=s.skill_id
        WHERE ps.employee_id=%s AND ps.status='pending'
        ORDER BY ps.submitted_at DESC
    ''', (eid,))

    assignments = query_db('''
        SELECT p.project_id, p.project_name, p.status,
               a.allocation_percentage, a.hours_logged, a.start_date, a.end_date
        FROM assignments a JOIN projects p ON a.project_id=p.project_id
        WHERE a.employee_id=%s ORDER BY a.created_at DESC
    ''', (eid,))

    all_skills = query_db('SELECT skill_id, skill_name FROM skills ORDER BY skill_name') or []

    return render_template('employee/dashboard.html',
        emp=emp, skills=skills, pending=pending,
        assignments=assignments, all_skills=all_skills)

# ── Profile ───────────────────────────────────────────────────────────────────
@employee_bp.route('/profile', methods=['GET', 'POST'])
@role_required('employee', 'admin')
def profile():
    eid = _get_eid()
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        dept    = request.form.get('department', '').strip()
        desig   = request.form.get('designation', '').strip()
        yrs     = request.form.get('years_experience', 0)
        sat     = request.form.get('satisfaction_score', 3.0)
        hrs     = request.form.get('monthly_hours', 160)
        contact = 'show_contact' in request.form
        execute_db('''
            UPDATE employees
            SET name=%s, department=%s, designation=%s,
                years_experience=%s, satisfaction_score=%s,
                monthly_hours=%s, show_contact=%s
            WHERE employee_id=%s
        ''', (name, dept, desig, yrs, sat, hrs, contact, eid))
        flash('Profile updated!', 'success')
        return redirect(url_for('employee.dashboard'))

    emp = query_db('SELECT * FROM employees WHERE employee_id=%s', (eid,), one=True)
    return render_template('employee/profile.html', emp=emp)

# ── Add skill (→ pending queue, not direct DB insert) ────────────────────────
@employee_bp.route('/skills/add', methods=['POST'])
@role_required('employee', 'admin')
def add_skill():
    eid   = _get_eid()
    sid   = request.form.get('skill_id')
    level = request.form.get('proficiency_level', 3)

    if not sid:
        flash('Please select a skill.', 'error')
        return redirect(url_for('employee.dashboard'))

    # Check if already approved
    existing = query_db(
        'SELECT es_id FROM employee_skills WHERE employee_id=%s AND skill_id=%s',
        (eid, sid), one=True)
    if existing:
        flash('You already have this skill approved.', 'warning')
        return redirect(url_for('employee.dashboard'))

    # Check if already pending
    already_pending = query_db(
        "SELECT pending_id FROM pending_skills WHERE employee_id=%s AND skill_id=%s AND status='pending'",
        (eid, sid), one=True)
    if already_pending:
        flash('This skill is already awaiting HR approval.', 'warning')
        return redirect(url_for('employee.dashboard'))

    execute_db('''
        INSERT INTO pending_skills (employee_id, skill_id, proficiency_level, status)
        VALUES (%s, %s, %s, 'pending')
    ''', (eid, sid, level))
    flash('Skill request submitted — awaiting HR approval.', 'info')
    return redirect(url_for('employee.dashboard'))

# ── Remove approved skill ─────────────────────────────────────────────────────
@employee_bp.route('/skills/remove/<int:sid>', methods=['POST'])
@role_required('employee', 'admin')
def remove_skill(sid):
    eid = _get_eid()
    execute_db(
        'DELETE FROM employee_skills WHERE employee_id=%s AND skill_id=%s',
        (eid, sid))
    flash('Skill removed.', 'success')
    return redirect(url_for('employee.dashboard'))

# ── Cancel a pending request ──────────────────────────────────────────────────
@employee_bp.route('/skills/cancel/<int:pid>', methods=['POST'])
@role_required('employee', 'admin')
def cancel_pending(pid):
    eid = _get_eid()
    execute_db(
        "DELETE FROM pending_skills WHERE pending_id=%s AND employee_id=%s AND status='pending'",
        (pid, eid))
    flash('Skill request cancelled.', 'info')
    return redirect(url_for('employee.dashboard'))

# ── Resume PDF upload ─────────────────────────────────────────────────────────
@employee_bp.route('/resume/upload', methods=['POST'])
@role_required('employee', 'admin')
def upload_resume():
    eid  = _get_eid()
    file = request.files.get('resume_pdf')

    if not file or file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('employee.dashboard'))

    if not _allowed_file(file.filename):
        flash('Only PDF files are accepted.', 'error')
        return redirect(url_for('employee.dashboard'))

    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    fname = secure_filename(f"resume_{eid}_{file.filename}")
    fpath = os.path.join(upload_dir, fname)
    file.save(fpath)

    # Save path to employee record
    execute_db('UPDATE employees SET resume_path=%s WHERE employee_id=%s',
               (fpath, eid))

    # Extract text from PDF
    resume_text = _extract_pdf_text(fpath)
    if not resume_text:
        flash('PDF saved but could not extract text for skill parsing.', 'warning')
        return redirect(url_for('employee.dashboard'))

    # Run skill extraction and return JSON for AJAX or redirect with results in session
    matched = extract_skills_from_text(resume_text)
    session['resume_skills'] = matched          # pass to template via session
    flash(f'Resume uploaded! Found {len(matched)} potential skills — review below.', 'success')
    return redirect(url_for('employee.dashboard'))

# ── Extract skills from plain text (AJAX) ────────────────────────────────────
@employee_bp.route('/extract-skills', methods=['POST'])
@role_required('employee', 'admin')
def extract_skills():
    resume_text = request.form.get('resume_text', '')
    matched_raw = extract_skills_from_text(resume_text)

    results = []
    for item in matched_raw:
        row = query_db(
            'SELECT skill_id, skill_name FROM skills WHERE LOWER(skill_name) LIKE %s LIMIT 1',
            (f'%{item["skill"].lower()}%',), one=True)
        if row:
            results.append({
                'id':     row['skill_id'],
                'name':   row['skill_name'],
                'confidence': item.get('confidence'),
                'evidence': item.get('evidence'),
            })

    return jsonify({'skills': results})

# ── Skills list (for dropdowns) ───────────────────────────────────────────────
@employee_bp.route('/skills-list')
@role_required('employee', 'admin')
def skills_list():
    skills = query_db('SELECT skill_id AS id, skill_name AS name FROM skills ORDER BY skill_name') or []
    return jsonify({'skills': [dict(s) for s in skills]})

# ── Internal: PDF text extraction ────────────────────────────────────────────
def _extract_pdf_text(fpath: str) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(fpath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return '\n'.join(text_parts)
    except Exception:
        # Fallback to pypdf
        try:
            from pypdf import PdfReader
            r = PdfReader(fpath)
            return '\n'.join(p.extract_text() or '' for p in r.pages)
        except Exception:
            return ''
