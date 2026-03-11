import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
load_dotenv()

def get_db():
    url = os.environ.get('DATABASE_URL', '')
    # Supabase requires SSL
    if 'sslmode' not in url:
        url += '?sslmode=require'
    return psycopg2.connect(url)

def query_db(sql, args=(), one=False):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    finally:
        conn.close()

def execute_db(sql, args=()):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, args)
        conn.commit()
    finally:
        conn.close()
