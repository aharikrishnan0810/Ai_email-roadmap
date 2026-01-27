import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME', 'emails.db') # Use a file for SQLite

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def create_table_if_not_exists():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gmail_id TEXT UNIQUE,
            sender TEXT,
            subject TEXT,
            body TEXT,
            category VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

def insert_email(gmail_id, sender, subject, body, category):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO emails (gmail_id, sender, subject, body, category)
            VALUES (?, ?, ?, ?, ?)
        """, (gmail_id, sender, subject, body, category))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Duplicate gmail_id
    
    cursor.close()
    conn.close()

def fetch_stored_emails(category=None, limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()

    if category:
        cursor.execute("""
            SELECT id, sender, subject, body, category, created_at
            FROM emails
            WHERE category = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (category, limit))
    else:
        cursor.execute("""
            SELECT id, sender, subject, body, category, created_at
            FROM emails
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    emails = []
    for row in rows:
        emails.append({
            "id": row["id"],
            "sender": row["sender"],
            "subject": row["subject"],
            "body": row["body"],
            "category": row["category"],
            "created_at": row["created_at"]
        })

    return emails

def fetch_email_by_id(email_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, sender, subject, body, category, created_at
        FROM emails
        WHERE id = ?
    """, (email_id,))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "sender": row["sender"],
        "subject": row["subject"],
        "body": row["body"],
        "category": row["category"],
        "created_at": row["created_at"]
    }

