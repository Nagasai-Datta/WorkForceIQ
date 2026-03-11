from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from auth_utils import role_required
from db import query_db, execute_db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    users = query_db('''
        SELECT u.*, e.name, e.department, e.employee_id
        FROM users u
        LEFT JOIN employees e ON u.user_id=e.user_id
        ORDER BY u.created_at DESC
    ''')
    role_counts = query_db('SELECT role, COUNT(*) AS c FROM users GROUP BY role')
    return render_template('admin/dashboard.html', users=users, role_counts=role_counts)

@admin_bp.route('/create-user', methods=['POST'])
@role_required('admin')
def create_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role     = request.form.get('role', 'employee')
    name     = request.form.get('name', username).strip()
    email    = request.form.get('email', '').strip()
    dept     = request.form.get('department', '').strip()

    if not username or not password or not email:
        flash('Username, password and email are required.', 'error')
        return redirect(url_for('admin.dashboard'))

    existing = query_db('SELECT user_id FROM users WHERE username=%s', (username,), one=True)
    if existing:
        flash('Username already taken.', 'error')
        return redirect(url_for('admin.dashboard'))

    pw_hash = generate_password_hash(password)
    try:
        # Create user
        conn = __import__('psycopg2').connect(__import__('os').environ.get('DATABASE_URL'))
        cur  = conn.cursor()
        cur.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s) RETURNING user_id',
            (username, pw_hash, role)
        )
        new_uid = cur.fetchone()[0]

        # Create employee profile
        cur.execute('''
            INSERT INTO employees (user_id, name, email, department)
            VALUES (%s, %s, %s, %s)
        ''', (new_uid, name, email, dept or None))

        conn.commit()
        conn.close()
        flash(f'User "{username}" created successfully!', 'success')
    except Exception as e:
        flash(f'Error creating user: {e}', 'error')

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete-user/<int:uid>', methods=['POST'])
@role_required('admin')
def delete_user(uid):
    if uid == session['user_id']:
        flash("You can't delete yourself.", 'error')
        return redirect(url_for('admin.dashboard'))
    execute_db('DELETE FROM users WHERE user_id=%s', (uid,))
    flash('User deleted.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/change-role/<int:uid>', methods=['POST'])
@role_required('admin')
def change_role(uid):
    role = request.form.get('role')
    valid = ('hr', 'project_manager', 'employee', 'admin')
    if role in valid:
        execute_db('UPDATE users SET role=%s WHERE user_id=%s', (role, uid))
        flash('Role updated.', 'success')
    return redirect(url_for('admin.dashboard'))
