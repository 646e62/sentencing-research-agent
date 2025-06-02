import os
import psycopg2

# If you want, you can set these as environment variables or just use them directly here
DB_NAME = os.getenv('PGDATABASE', 'sentencing_db')
DB_USER = os.getenv('PGUSER', 'sentencing_user')
DB_PASS = os.getenv('PGPASSWORD', 'sentencing_pass_2025')
DB_HOST = os.getenv('PGHOST', 'localhost')
DB_PORT = os.getenv('PGPORT', '5432')

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"PostgreSQL connection successful! Version: {version[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Database connection failed: {e}")
