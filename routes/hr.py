import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth_utils import role_required
from db import query_db, execute_db
from ml.train_attrition import predict_attrition

hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

# ── Internal helper ───────────────────────────────────────────────────────────
def _get_attrition_data():
    employees = query_db('''
        SELECT e.*,
               COALESCE(a.total_allocation, 0) AS total_allocation,
               COALESCE(a.num_projects, 0)     AS num_projects,
               COALESCE(s.skill_count, 0)      AS skill_count
        FROM employees e
        LEFT JOIN (
            SELECT employee_id,
                   SUM(allocation_percentage) AS total_allocation,
                   COUNT(assignment_id) AS num_projects
            FROM assignments
            GROUP BY employee_id
        ) a ON e.employee_id = a.employee_id
        LEFT JOIN (
            SELECT employee_id, COUNT(skill_id) AS skill_count
            FROM employee_skills
            GROUP BY employee_id
        ) s ON e.employee_id = s.employee_id
        ORDER BY e.employee_id
    ''') or []

    results = []
    for emp in employees:
        d    = dict(emp)
        pred = predict_attrition(d)
        results.append({
            'employee':    d,
            'risk':        pred['risk'],
            'probability': pred['probability'],
            'explanation': pred['explanation'],
        })
    results.sort(key=lambda x: x['probability'], reverse=True)
    return results

# ── Dashboard ─────────────────────────────────────────────────────────────────
@hr_bp.route('/dashboard')
@role_required('hr', 'admin')
def dashboard():
    total_row = query_db('SELECT COUNT(*) AS c FROM employees', one=True)
    total     = total_row['c'] if total_row else 0

    avg_row = query_db('SELECT ROUND(AVG(satisfaction_score),1) AS a FROM employees', one=True)
    avg_sat = avg_row['a'] if avg_row else 0

    predictions = _get_attrition_data()
    high_risk   = sum(1 for p in predictions if p['risk'] == 'High')

    dept_rows = query_db('SELECT department, COUNT(*) AS c FROM employees GROUP BY department') or []
    dept_data = json.dumps([{'dept': r['department'] or 'Unknown', 'count': r['c']} for r in dept_rows])

    skill_rows = query_db('''
        SELECT s.skill_name, COUNT(es.employee_id) AS c
        FROM skills s
        LEFT JOIN employee_skills es ON s.skill_id = es.skill_id
        GROUP BY s.skill_name ORDER BY c DESC LIMIT 8
    ''') or []
    skill_data = json.dumps([{'skill': r['skill_name'], 'count': r['c']} for r in skill_rows])

    # Pending skill approvals count
    pending_count_row = query_db(
        "SELECT COUNT(*) AS c FROM pending_skills WHERE status='pending'", one=True)
    pending_count = pending_count_row['c'] if pending_count_row else 0

    return render_template('hr/dashboard.html',
        total_employees=total,
        avg_satisfaction=avg_sat,
        high_risk_count=high_risk,
        top_predictions=predictions[:5],
        dept_data=dept_data,
        skill_data=skill_data,
        pending_count=pending_count,
    )

# ── Employees list ────────────────────────────────────────────────────────────
@hr_bp.route('/employees')
@role_required('hr', 'admin')
def employees():
    skill_q = request.args.get('skill', '').strip()
    dept_q  = request.args.get('dept',  '').strip()

    sql = '''
        SELECT e.*,
               COALESCE(a.total_allocation,0) AS total_allocation,
               COALESCE(a.num_projects,0)     AS num_projects
        FROM employees e
        LEFT JOIN (
            SELECT employee_id,
                   SUM(allocation_percentage) AS total_allocation,
                   COUNT(assignment_id) AS num_projects
            FROM assignments
            GROUP BY employee_id
        ) a ON e.employee_id = a.employee_id
        WHERE 1=1
    '''
    params = []
    if skill_q:
        sql += '''
            AND EXISTS (
                SELECT 1
                FROM employee_skills es
                JOIN skills s ON es.skill_id = s.skill_id
                WHERE es.employee_id = e.employee_id
                  AND LOWER(s.skill_name) LIKE %s
            )
        '''
        params.append(f'%{skill_q.lower()}%')
    if dept_q:
        sql += ' AND e.department = %s'
        params.append(dept_q)
    sql += ' ORDER BY e.name'

    raw = query_db(sql, params) or []
    emp_list = []
    for emp in raw:
        skills = query_db('''
            SELECT s.skill_name, es.proficiency_level
            FROM employee_skills es JOIN skills s ON es.skill_id=s.skill_id
            WHERE es.employee_id=%s ORDER BY es.proficiency_level DESC, s.skill_name
        ''', (emp['employee_id'],))
        d = dict(emp)
        d['skills'] = skills
        emp_list.append(d)

    all_skills  = query_db('SELECT skill_name FROM skills ORDER BY skill_name') or []
    departments = query_db('SELECT DISTINCT department FROM employees WHERE department IS NOT NULL ORDER BY department') or []
    return render_template('hr/employees.html',
        employees=emp_list, all_skills=all_skills,
        departments=departments, skill_filter=skill_q, dept_filter=dept_q)

# ── Employee detail ───────────────────────────────────────────────────────────
@hr_bp.route('/employee/<int:eid>')
@role_required('hr', 'admin')
def employee_detail(eid):
    emp = query_db('''
        SELECT e.*,
               COALESCE(a.total_allocation,0) AS total_allocation,
               COALESCE(a.num_projects,0)     AS num_projects,
               COALESCE(s.skill_count,0)      AS skill_count
        FROM employees e
        LEFT JOIN (
            SELECT employee_id,
                   SUM(allocation_percentage) AS total_allocation,
                   COUNT(assignment_id) AS num_projects
            FROM assignments
            GROUP BY employee_id
        ) a ON e.employee_id = a.employee_id
        LEFT JOIN (
            SELECT employee_id, COUNT(skill_id) AS skill_count
            FROM employee_skills
            GROUP BY employee_id
        ) s ON e.employee_id = s.employee_id
        WHERE e.employee_id=%s
    ''', (eid,), one=True)
    if not emp:
        flash('Employee not found.', 'error')
        return redirect(url_for('hr.employees'))

    skills = query_db('''
        SELECT s.skill_name, es.proficiency_level
        FROM employee_skills es JOIN skills s ON es.skill_id=s.skill_id
        WHERE es.employee_id=%s ORDER BY es.proficiency_level DESC, s.skill_name
    ''', (eid,))

    assignments = query_db('''
        SELECT p.project_name, p.status, a.allocation_percentage,
               a.start_date, a.end_date, a.hours_logged
        FROM assignments a JOIN projects p ON a.project_id=p.project_id
        WHERE a.employee_id=%s
    ''', (eid,))

    pred = predict_attrition(dict(emp))
    return render_template('hr/employee_detail.html',
        emp=emp, skills=skills, assignments=assignments,
        pred=pred)

# ── Analytics ─────────────────────────────────────────────────────────────────
@hr_bp.route('/analytics')
@role_required('hr', 'admin')
def analytics():
    predictions = _get_attrition_data() or []

    skill_coverage = query_db('''
        SELECT s.skill_name,
               COUNT(es.employee_id) AS emp_count,
               ROUND(AVG(es.proficiency_level),1) AS avg_prof
        FROM skills s
        LEFT JOIN employee_skills es ON s.skill_id=es.skill_id
        GROUP BY s.skill_id, s.skill_name
        ORDER BY emp_count ASC
    ''')

    skill_chart = json.dumps([{
        'skill': r['skill_name'],
        'count': r['emp_count'],
        'avg':   float(r['avg_prof'] or 0)
    } for r in (skill_coverage or [])])

    risk_counts = {'High': 0, 'Medium': 0, 'Low': 0}
    for p in predictions:
        risk_counts[p['risk']] += 1

    return render_template('hr/analytics.html',
        predictions=predictions,
        skill_coverage=skill_coverage,
        skill_chart=skill_chart,
        risk_counts=json.dumps(risk_counts),
    )

# ── Skill Approval Dashboard  (NEW) ──────────────────────────────────────────
@hr_bp.route('/skill-approvals')
@role_required('hr', 'admin')
def skill_approvals():
    pending = query_db('''
        SELECT ps.pending_id, ps.employee_id, ps.skill_id,
               ps.proficiency_level, ps.submitted_at,
               e.name AS employee_name, e.department,
               s.skill_name
        FROM pending_skills ps
        JOIN employees e ON ps.employee_id = e.employee_id
        JOIN skills    s ON ps.skill_id    = s.skill_id
        WHERE ps.status = 'pending'
        ORDER BY ps.submitted_at ASC
    ''') or []

    recent = query_db('''
        SELECT ps.pending_id, ps.status, ps.reviewed_at, ps.review_note,
               e.name AS employee_name, s.skill_name,
               u.username AS reviewed_by_name
        FROM pending_skills ps
        JOIN employees e ON ps.employee_id = e.employee_id
        JOIN skills    s ON ps.skill_id    = s.skill_id
        LEFT JOIN users u ON ps.reviewed_by = u.user_id
        WHERE ps.status != 'pending'
        ORDER BY ps.reviewed_at DESC
        LIMIT 30
    ''') or []

    return render_template('hr/skill_approvals.html',
        pending=pending, recent=recent)

# ── Approve skill ─────────────────────────────────────────────────────────────
@hr_bp.route('/skill-approvals/<int:pid>/approve', methods=['POST'])
@role_required('hr', 'admin')
def approve_skill(pid):
    note = request.form.get('note', '').strip()
    hr_uid = session.get('user_id')

    row = query_db(
        'SELECT * FROM pending_skills WHERE pending_id=%s AND status=%s',
        (pid, 'pending'), one=True)
    if not row:
        flash('Request not found or already reviewed.', 'error')
        return redirect(url_for('hr.skill_approvals'))

    # Insert into approved skills (or update proficiency if already exists)
    execute_db('''
        INSERT INTO employee_skills (employee_id, skill_id, proficiency_level)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE proficiency_level = VALUES(proficiency_level)
    ''', (row['employee_id'], row['skill_id'], row['proficiency_level']))

    # Mark pending as approved
    execute_db('''
        UPDATE pending_skills
        SET status='approved', reviewed_by=%s,
            reviewed_at=NOW(), review_note=%s
        WHERE pending_id=%s
    ''', (hr_uid, note or 'Approved', pid))

    flash('Skill approved and added to employee profile.', 'success')
    return redirect(url_for('hr.skill_approvals'))

# ── Reject skill ──────────────────────────────────────────────────────────────
@hr_bp.route('/skill-approvals/<int:pid>/reject', methods=['POST'])
@role_required('hr', 'admin')
def reject_skill(pid):
    note   = request.form.get('note', '').strip()
    hr_uid = session.get('user_id')

    execute_db('''
        UPDATE pending_skills
        SET status='rejected', reviewed_by=%s,
            reviewed_at=NOW(), review_note=%s
        WHERE pending_id=%s AND status='pending'
    ''', (hr_uid, note or 'Rejected', pid))

    flash('Skill request rejected.', 'warning')
    return redirect(url_for('hr.skill_approvals'))
