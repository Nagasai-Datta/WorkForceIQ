import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth_utils import role_required
from db import query_db, execute_db
from ml.train_attrition import predict_attrition
from typing import Any, cast

hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

def _get_attrition_data():
    employees = query_db('''
        SELECT e.*,
               COALESCE(SUM(a.allocation_percentage),0) AS total_allocation,
               COUNT(a.assignment_id) AS num_projects
        FROM employees e
        LEFT JOIN assignments a ON e.employee_id = a.employee_id
        GROUP BY e.employee_id
    ''') or []
    results = []
    for emp in employees:
        risk, prob = predict_attrition(dict(emp))
        results.append({'employee': dict(emp), 'risk': risk, 'probability': prob})
    results.sort(key=lambda x: x['probability'], reverse=True)
    return results

@hr_bp.route('/dashboard')
@role_required('hr', 'admin')
def dashboard():
    total_row = cast("dict[str, Any] | None",
                     query_db('SELECT COUNT(*) AS c FROM employees', one=True))
    total = total_row['c'] if total_row is not None else 0

    avg_row = cast("dict[str, Any] | None",
                   query_db('SELECT ROUND(AVG(satisfaction_score)::numeric,1) AS a FROM employees', one=True))
    avg_sat = avg_row['a'] if avg_row is not None else 0

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

    return render_template('hr/dashboard.html',
        total_employees=total,
        avg_satisfaction=avg_sat,
        high_risk_count=high_risk,
        top_predictions=predictions[:5],
        dept_data=dept_data,
        skill_data=skill_data,
    )

@hr_bp.route('/employees')
@role_required('hr', 'admin')
def employees():
    skill_q = request.args.get('skill', '').strip()
    dept_q  = request.args.get('dept', '').strip()

    sql = '''
        SELECT DISTINCT e.*,
               COALESCE(SUM(a.allocation_percentage),0) AS total_allocation,
               COUNT(DISTINCT a.assignment_id) AS num_projects
        FROM employees e
        LEFT JOIN assignments a ON e.employee_id = a.employee_id
        LEFT JOIN employee_skills es ON e.employee_id = es.employee_id
        LEFT JOIN skills s ON es.skill_id = s.skill_id
        WHERE 1=1
    '''
    params = []
    if skill_q:
        sql += ' AND LOWER(s.skill_name) LIKE %s'
        params.append(f'%{skill_q.lower()}%')
    if dept_q:
        sql += ' AND e.department = %s'
        params.append(dept_q)
    sql += ' GROUP BY e.employee_id ORDER BY e.name'

    raw = query_db(sql, params) or []
    emp_list = []
    for emp in raw:
        skills = query_db('''
            SELECT s.skill_name, es.proficiency_level
            FROM employee_skills es JOIN skills s ON es.skill_id=s.skill_id
            WHERE es.employee_id=%s ORDER BY es.proficiency_level DESC
        ''', (emp['employee_id'],))
        d = dict(emp)
        d['skills'] = skills
        emp_list.append(d)

    all_skills  = query_db('SELECT skill_name FROM skills ORDER BY skill_name') or []
    departments = query_db('SELECT DISTINCT department FROM employees WHERE department IS NOT NULL ORDER BY department') or []
    return render_template('hr/employees.html',
        employees=emp_list, all_skills=all_skills,
        departments=departments, skill_filter=skill_q, dept_filter=dept_q)

@hr_bp.route('/employee/<int:eid>')
@role_required('hr', 'admin')
def employee_detail(eid):
    emp = query_db('''
        SELECT e.*,
               COALESCE(SUM(a.allocation_percentage),0) AS total_allocation,
               COUNT(a.assignment_id) AS num_projects
        FROM employees e
        LEFT JOIN assignments a ON e.employee_id=a.employee_id
        WHERE e.employee_id=%s GROUP BY e.employee_id
    ''', (eid,), one=True)
    if not emp:
        flash('Employee not found.', 'error')
        return redirect(url_for('hr.employees'))

    skills = query_db('''
        SELECT s.skill_name, es.proficiency_level
        FROM employee_skills es JOIN skills s ON es.skill_id=s.skill_id
        WHERE es.employee_id=%s ORDER BY es.proficiency_level DESC
    ''', (eid,))

    assignments = query_db('''
        SELECT p.project_name, p.status, a.allocation_percentage, a.start_date, a.end_date, a.hours_logged
        FROM assignments a JOIN projects p ON a.project_id=p.project_id
        WHERE a.employee_id=%s
    ''', (eid,))

    typed_emp = cast("dict[str, Any]", emp)
    risk, prob = predict_attrition(dict(typed_emp))
    return render_template('hr/employee_detail.html',
        emp=emp, skills=skills, assignments=assignments, risk=risk, prob=prob)

@hr_bp.route('/analytics')
@role_required('hr', 'admin')
def analytics():
    predictions = _get_attrition_data() or []

    skill_coverage = query_db('''
        SELECT s.skill_name,
               COUNT(es.employee_id) AS emp_count,
               ROUND(AVG(es.proficiency_level)::numeric,1) AS avg_prof
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
