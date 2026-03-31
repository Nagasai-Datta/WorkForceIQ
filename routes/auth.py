from flask import Blueprint, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash
from typing import Any, MutableMapping, cast
from db import query_db

auth_bp = Blueprint('auth', __name__)

ROLE_REDIRECT = {
    'hr':              'hr.dashboard',
    'project_manager': 'pm.dashboard',
    'employee':        'employee.dashboard',
    'admin':           'admin.dashboard',
}

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for(ROLE_REDIRECT[session['role']]))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    typed_session: MutableMapping[str, Any] = cast(MutableMapping[str, Any], session)
    if 'user_id' in session:
        return redirect(url_for(ROLE_REDIRECT[typed_session['role']]))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            error = 'Please fill in all fields.'
        else:
            user = cast("dict[str, Any] | None", query_db('SELECT * FROM users WHERE username=%s', (username,), one=True))
            if not user or not check_password_hash(user['password_hash'], password):
                error = 'Invalid username or password.'
            else:
                typed_session.clear()
                typed_session['user_id'] = user['user_id']
                typed_session['username'] = user['username']
                typed_session['role'] = user['role']
                emp = cast("dict[str, Any] | None", query_db('SELECT employee_id FROM employees WHERE user_id=%s',
                               (user['user_id'],), one=True))
                typed_session['employee_id'] = emp['employee_id'] if emp else None
                return redirect(url_for(ROLE_REDIRECT[user['role']]))
    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
