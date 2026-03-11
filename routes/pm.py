import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth_utils import role_required
from db import query_db, execute_db
from typing import Any, cast

pm_bp = Blueprint('pm', __name__, url_prefix='/pm')

@pm_bp.route('/dashboard')
@role_required('project_manager', 'admin')
def dashboard():
    # All employees with their total allocation
    employees = query_db('''
        SELECT e.employee_id, e.name, e.department, e.designation,
               COALESCE(SUM(a.allocation_percentage),0) AS total_allocation,
               COUNT(a.assignment_id) AS num_projects
        FROM employees e
        LEFT JOIN assignments a ON e.employee_id=a.employee_id
        GROUP BY e.employee_id ORDER BY total_allocation DESC
    ''') or []

    overloaded = sum(1 for e in employees if e['total_allocation'] > 80)
    projects   = query_db("SELECT * FROM projects ORDER BY status, project_name") or []
    active_p   = sum(1 for p in projects if p['status'] == 'active')

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
        SELECT e.employee_id, e.name, e.department, a.allocation_percentage,
               a.hours_logged, a.assignment_id,
               COALESCE(SUM(a2.allocation_percentage),0) AS total_alloc
        FROM assignments a
        JOIN employees e ON a.employee_id=e.employee_id
        LEFT JOIN assignments a2 ON e.employee_id=a2.employee_id
        WHERE a.project_id=%s
        GROUP BY e.employee_id, e.name, e.department,
                 a.allocation_percentage, a.hours_logged, a.assignment_id
    ''', (pid,)) or []

    # Available employees (not yet on this project)
    available = query_db('''
        SELECT e.employee_id, e.name, e.department, e.designation,
               COALESCE(SUM(a.allocation_percentage),0) AS total_alloc
        FROM employees e
        LEFT JOIN assignments a ON e.employee_id=a.employee_id
        WHERE e.employee_id NOT IN (
            SELECT employee_id FROM assignments WHERE project_id=%s
        )
        GROUP BY e.employee_id ORDER BY total_alloc ASC
    ''', (pid,)) or []

    all_skills = query_db('SELECT skill_name FROM skills ORDER BY skill_name') or []

    return render_template('pm/project_detail.html',
        project=project, team=team, available=available, all_skills=all_skills)

@pm_bp.route('/assign', methods=['POST'])
@role_required('project_manager', 'admin')
def assign():
    pid_str = request.form.get('project_id')
    eid_str = request.form.get('employee_id')
    alloc_str = request.form.get('allocation_percentage', '0')

    pid = int(pid_str) if pid_str is not None else 0
    eid = int(eid_str) if eid_str is not None else 0
    alloc = int(alloc_str) if alloc_str is not None else 0

    if alloc < 1 or alloc > 100:
        flash('Allocation must be between 1 and 100%.', 'error')
        return redirect(url_for('pm.project_detail', pid=pid))

    # Check current load
    current_row = cast("dict[str, Any] | None",
                       query_db(
                           'SELECT COALESCE(SUM(allocation_percentage),0) AS tot FROM assignments WHERE employee_id=%s',
                           (eid,), one=True
                       ))
    current = current_row['tot'] if current_row is not None else 0

    if int(current) + alloc > 100:
        remaining = 100 - int(current)
        flash(f'Cannot assign — employee only has {remaining}% capacity left.', 'error')
        return redirect(url_for('pm.project_detail', pid=pid))

    try:
        execute_db('''
            INSERT INTO assignments (employee_id, project_id, allocation_percentage, start_date, end_date)
            VALUES (%s, %s, %s, NOW(), NOW() + INTERVAL '3 months')
        ''', (eid, pid, alloc))
        flash('Employee assigned successfully!', 'success')
    except Exception as e:
        flash('Assignment failed — employee may already be on this project.', 'error')

    return redirect(url_for('pm.project_detail', pid=pid))

@pm_bp.route('/unassign/<int:aid>', methods=['POST'])
@role_required('project_manager', 'admin')
def unassign(aid):
    a = query_db('SELECT project_id FROM assignments WHERE assignment_id=%s', (aid,), one=True)
    a_typed = cast("dict[str, Any] | None", a)
    pid = a_typed['project_id'] if a_typed else None
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
        VALUES (%s, %s, %s, %s, 'draft', %s)
    ''', (name, desc, start or None, end or None, session['user_id']))
    flash('Project created!', 'success')
    return redirect(url_for('pm.projects'))

@pm_bp.route('/project/<int:pid>/status', methods=['POST'])
@role_required('project_manager', 'admin')
def update_status(pid):
    status = request.form.get('status')
    valid = ('draft', 'validating', 'active', 'paused', 'completed')
    if status in valid:
        execute_db('UPDATE projects SET status=%s WHERE project_id=%s', (status, pid))
        flash('Status updated.', 'success')
    return redirect(url_for('pm.project_detail', pid=pid))
