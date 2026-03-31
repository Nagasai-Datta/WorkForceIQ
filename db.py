"""
db.py — MySQL connection layer (replaces psycopg2/Supabase)
Configure via .env:
  DB_HOST=localhost
  DB_PORT=3306
  DB_USER=root
  DB_PASSWORD=yourpassword
  DB_NAME=workforceiq
"""
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def _get_cfg():
    return dict(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'workforceiq'),
        charset='utf8mb4',
        use_unicode=True,
        autocommit=False,
    )

def get_db():
    return mysql.connector.connect(**_get_cfg())

def query_db(sql, args=(), one=False):
    """Execute SELECT, return list[dict] or single dict."""
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    finally:
        conn.close()

def execute_db(sql, args=()):
    """Execute INSERT/UPDATE/DELETE. Returns lastrowid."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, args)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
