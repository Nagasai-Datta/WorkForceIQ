from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from auth_utils import role_required
from db import query_db, execute_db
from ml.skill_extractor import extract_skills_tfidf
from typing import Any, cast

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.route('/dashboard')
@role_required('employee', 'admin')
def dashboard():
    eid = session.get('employee_id')
    emp = query_db('''
        SELECT e.*,
               COALESCE(SUM(a.allocation_percentage),0) AS total_allocation,
               COUNT(a.assignment_id) AS num_projects
        FROM employees e
        LEFT JOIN assignments a ON e.employee_id=a.employee_id
        WHERE e.employee_id=%s GROUP BY e.employee_id
    ''', (eid,), one=True)

    skills = query_db('''
        SELECT s.skill_id, s.skill_name, es.proficiency_level
        FROM employee_skills es JOIN skills s ON es.skill_id=s.skill_id
        WHERE es.employee_id=%s ORDER BY es.proficiency_level DESC
    ''', (eid,))

    assignments = query_db('''
        SELECT p.project_id, p.project_name, p.status,
               a.allocation_percentage, a.hours_logged, a.start_date, a.end_date
        FROM assignments a JOIN projects p ON a.project_id=p.project_id
        WHERE a.employee_id=%s ORDER BY a.created_at DESC
    ''', (eid,))

    return render_template('employee/dashboard.html',
        emp=emp, skills=skills, assignments=assignments)

@employee_bp.route('/profile', methods=['GET', 'POST'])
@role_required('employee', 'admin')
def profile():
    eid = session.get('employee_id')
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

@employee_bp.route('/skills/add', methods=['POST'])
@role_required('employee', 'admin')
def add_skill():
    eid   = session.get('employee_id')
    sid   = request.form.get('skill_id')
    level = request.form.get('proficiency_level', 3)
    try:
        execute_db('''
            INSERT INTO employee_skills (employee_id, skill_id, proficiency_level)
            VALUES (%s, %s, %s)
            ON CONFLICT (employee_id, skill_id)
            DO UPDATE SET proficiency_level=EXCLUDED.proficiency_level
        ''', (eid, sid, level))
        flash('Skill added!', 'success')
    except Exception:
        flash('Could not add skill.', 'error')
    return redirect(url_for('employee.dashboard'))

@employee_bp.route('/skills/remove/<int:sid>', methods=['POST'])
@role_required('employee', 'admin')
def remove_skill(sid):
    eid = session.get('employee_id')
    execute_db(
        'DELETE FROM employee_skills WHERE employee_id=%s AND skill_id=%s',
        (eid, sid)
    )
    flash('Skill removed.', 'success')
    return redirect(url_for('employee.dashboard'))

@employee_bp.route('/extract-skills', methods=['POST'])
@role_required('employee', 'admin')
def extract_skills():
    """
    TF-IDF skill extraction from pasted resume text.
    Returns JSON list of matched skill names.
    """
    resume_text = request.form.get('resume_text', '')
    matched = extract_skills_tfidf(resume_text)

    # Map extracted skill names to skill_ids in DB
    results: list[dict[str, Any]] = []
    for skill_name in matched:
        row = cast("dict[str, Any] | None",
                   query_db(
                       'SELECT skill_id, skill_name FROM skills WHERE LOWER(skill_name) LIKE %s LIMIT 1',
                       (f'%{skill_name.lower()}%',), one=True
                   ))
        if row:
            results.append({'id': row['skill_id'], 'name': row['skill_name']})

    return jsonify({'skills': results, 'raw': matched})

@employee_bp.route('/skills-list')
@role_required('employee', 'admin')
def skills_list():
    from flask import jsonify
    skills = query_db('SELECT skill_id AS id, skill_name AS name FROM skills ORDER BY skill_name') or []
    return jsonify({'skills': [dict(s) for s in skills]})
