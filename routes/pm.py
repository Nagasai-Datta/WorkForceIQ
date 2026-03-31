import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth_utils import role_required
from db import query_db, execute_db

pm_bp = Blueprint('pm', __name__, url_prefix='/pm')

@pm_bp.route('/dashboard')
@role_required('project_manager', 'admin')
def dashboard():
    employees = query_db('''
        SELECT e.employee_id, e.name, e.department, e.designation,
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
        ORDER BY COALESCE(a.total_allocation,0) DESC, e.name
    ''') or []

    overloaded = sum(1 for e in employees if e['total_allocation'] > 80)
    projects   = query_db("SELECT * FROM projects ORDER BY status, project_name") or []
    active_p   = sum(1 for p in projects if p['status'] == 'Active')

    heatmap = json.dumps([{
        'name':  e['name'],
        'alloc': int(e['total_allocation']),
        'dept':  e['department'] or '',
    } for e in employees])

    return render_template('pm/dashboard.html',
        employees=employees,
        projects=projects,
        heatmap=heatmap,
        overloaded=overloaded,
        active_projects=active_p,
        total_employees=len(employees),
    )

@pm_bp.route('/projects')
@role_required('project_manager', 'admin')
def projects():
    projs = query_db("SELECT * FROM projects ORDER BY created_at DESC") or []
    return render_template('pm/projects.html', projects=projs)

@pm_bp.route('/project/<int:pid>')
@role_required('project_manager', 'admin')
def project_detail(pid):
    project = query_db('SELECT * FROM projects WHERE project_id=%s', (pid,), one=True)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('pm.projects'))

    team = query_db('''
        SELECT a.assignment_id, e.employee_id, e.name, e.department, e.designation,
               a.allocation_percentage, a.hours_logged, a.start_date, a.end_date,
               COALESCE(t.total_alloc, 0) AS total_alloc
        FROM assignments a
        JOIN employees e ON a.employee_id=e.employee_id
        LEFT JOIN (
            SELECT employee_id, SUM(allocation_percentage) AS total_alloc
            FROM assignments
            GROUP BY employee_id
        ) t ON e.employee_id = t.employee_id
        WHERE a.project_id=%s
        ORDER BY e.name
    ''', (pid,)) or []

    available = query_db('''
        SELECT e.employee_id, e.name, e.department, e.designation,
               COALESCE(t.total_alloc, 0) AS total_alloc
        FROM employees e
        LEFT JOIN (
            SELECT employee_id, SUM(allocation_percentage) AS total_alloc
            FROM assignments
            GROUP BY employee_id
        ) t ON e.employee_id = t.employee_id
        WHERE e.employee_id NOT IN (
            SELECT employee_id FROM assignments WHERE project_id=%s
        )
        ORDER BY COALESCE(t.total_alloc, 0) ASC, e.name
    ''', (pid,)) or []

    all_skills = query_db('SELECT skill_name FROM skills ORDER BY skill_name') or []

    return render_template('pm/project_detail.html',
        project=project, team=team, available=available, all_skills=all_skills)

@pm_bp.route('/assign', methods=['POST'])
@role_required('project_manager', 'admin')
def assign():
    pid   = int(request.form.get('project_id') or 0)
    eid   = int(request.form.get('employee_id') or 0)
    alloc = int(request.form.get('allocation_percentage') or 0)

    if alloc < 1 or alloc > 100:
        flash('Allocation must be between 1 and 100%.', 'error')
        return redirect(url_for('pm.project_detail', pid=pid))

    current_row = query_db(
        'SELECT COALESCE(SUM(allocation_percentage),0) AS tot FROM assignments WHERE employee_id=%s',
        (eid,), one=True)
    current = int(current_row['tot']) if current_row else 0

    if current + alloc > 100:
        remaining = 100 - current
        flash(f'Cannot assign — employee only has {remaining}% capacity left.', 'error')
        return redirect(url_for('pm.project_detail', pid=pid))

    try:
        # MySQL-compatible interval syntax
        execute_db('''
            INSERT INTO assignments (employee_id, project_id, allocation_percentage, start_date, end_date)
            VALUES (%s, %s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 3 MONTH))
        ''', (eid, pid, alloc))
        flash('Employee assigned successfully!', 'success')
    except Exception:
        flash('Assignment failed — employee may already be on this project.', 'error')

    return redirect(url_for('pm.project_detail', pid=pid))

@pm_bp.route('/unassign/<int:aid>', methods=['POST'])
@role_required('project_manager', 'admin')
def unassign(aid):
    a   = query_db('SELECT project_id FROM assignments WHERE assignment_id=%s', (aid,), one=True)
    pid = a['project_id'] if a else None
    execute_db('DELETE FROM assignments WHERE assignment_id=%s', (aid,))
    flash('Employee removed from project.', 'success')
    return redirect(url_for('pm.project_detail', pid=pid) if pid else url_for('pm.projects'))

@pm_bp.route('/project/create', methods=['POST'])
@role_required('project_manager', 'admin')
def create_project():
    name  = request.form.get('project_name', '').strip()
    desc  = request.form.get('description', '').strip()
    start = request.form.get('start_date')
    end   = request.form.get('end_date')
    if not name:
        flash('Project name is required.', 'error')
        return redirect(url_for('pm.projects'))
    execute_db('''
        INSERT INTO projects (project_name, description, start_date, end_date, status, created_by)
        VALUES (%s, %s, %s, %s, 'Draft', %s)
    ''', (name, desc, start or None, end or None, session['user_id']))
    flash('Project created!', 'success')
    return redirect(url_for('pm.projects'))

@pm_bp.route('/project/<int:pid>/status', methods=['POST'])
@role_required('project_manager', 'admin')
def update_status(pid):
    status = request.form.get('status')
    valid  = ('Draft', 'Validating', 'Active', 'Paused', 'Completed')
    if status in valid:
        execute_db('UPDATE projects SET status=%s WHERE project_id=%s', (status, pid))
        flash('Status updated.', 'success')
    return redirect(url_for('pm.project_detail', pid=pid))

@pm_bp.route('/log-hours/<int:aid>', methods=['POST'])
@role_required('project_manager', 'admin')
def log_hours(aid):
    hrs = request.form.get('hours', 0)
    a   = query_db('SELECT project_id FROM assignments WHERE assignment_id=%s', (aid,), one=True)
    execute_db('UPDATE assignments SET hours_logged=hours_logged+%s WHERE assignment_id=%s',
               (hrs, aid))
    flash('Hours logged.', 'success')
    pid = a['project_id'] if a else None
    return redirect(url_for('pm.project_detail', pid=pid) if pid else url_for('pm.projects'))
