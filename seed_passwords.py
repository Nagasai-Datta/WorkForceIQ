"""Run once: python seed_passwords.py"""
from werkzeug.security import generate_password_hash
from db import execute_db

accounts = [
    ('admin',        'password123'),
    ('hr_manager',   'password123'),
    ('proj_manager', 'password123'),
    ('emp_john',     'password123'),
    ('emp_sarah',    'password123'),
]

for username, pwd in accounts:
    h = generate_password_hash(pwd)
    execute_db('UPDATE users SET password_hash=%s WHERE username=%s', (h, username))
    print(f' {username}')

print('\nDone! Login with password: password123')
