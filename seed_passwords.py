"""
Run this ONCE after importing schema.sql to set secure passwords.
Usage:  python3 seed_passwords.py
"""
from werkzeug.security import generate_password_hash # type: ignore
from db import execute_db, query_db

SEED_USERS = [
    ('admin',   'Admin@123',   'admin'),
    ('hr1',     'Hr@123456',   'hr'),
    ('pm1',     'Pm@123456',   'project_manager'),
    ('emp1',    'Emp@123456',  'employee'),
]

for username, password, role in SEED_USERS:
    existing = query_db('SELECT user_id FROM users WHERE username=%s', (username,), one=True)
    pw_hash  = generate_password_hash(password)
    if existing:
        execute_db('UPDATE users SET password_hash=%s, role=%s WHERE username=%s',
                   (pw_hash, role, username))
        print(f"  Updated : {username}")
    else:
        uid = execute_db(
            'INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)',
            (username, pw_hash, role))
        execute_db(
            'INSERT IGNORE INTO employees (user_id, name, email, department) VALUES (%s,%s,%s,%s)',
            (uid, username.capitalize(), f'{username}@company.com', 'General'))
        print(f"  Created : {username} ({role})")

print("\nDone! Seed credentials:")
for u, p, r in SEED_USERS:
    print(f"  {u:12s}  {p:14s}  [{r}]")
