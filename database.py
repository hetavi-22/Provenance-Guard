import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "provenance_guard.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            content_id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            text TEXT NOT NULL,
            llm_score REAL,
            stylometric_score REAL,
            combined_confidence REAL,
            attribution TEXT,
            status TEXT DEFAULT 'classified',
            appeal_reasoning TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_submission(content_id, creator_id, text, llm_score, stylometric_score, combined_confidence, attribution):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat() + "Z"
    cursor.execute("""
        INSERT INTO submissions (
            content_id, creator_id, timestamp, text, llm_score, stylometric_score, combined_confidence, attribution, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'classified')
    """, (content_id, creator_id, timestamp, text, llm_score, stylometric_score, combined_confidence, attribution))
    conn.commit()
    conn.close()

def get_submission(content_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM submissions WHERE content_id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def submit_appeal(content_id, reasoning):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE submissions 
        SET status = 'under_review', appeal_reasoning = ? 
        WHERE content_id = ?
    """, (reasoning, content_id))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_all_submissions(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM submissions ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_analytics_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total submissions
    cursor.execute("SELECT COUNT(*) FROM submissions")
    total = cursor.fetchone()[0]
    
    if total == 0:
        conn.close()
        return {
            "total_submissions": 0,
            "likely_human": 0,
            "likely_ai": 0,
            "uncertain": 0,
            "total_appeals": 0,
            "appeal_rate": 0.0,
            "avg_confidence": 0.0
        }
        
    # Attribution breakdown
    cursor.execute("SELECT attribution, COUNT(*) FROM submissions GROUP BY attribution")
    breakdown = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Total appeals (status = 'under_review' or having appeal reasoning)
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE status = 'under_review'")
    appeals = cursor.fetchone()[0]
    
    # Average combined confidence
    cursor.execute("SELECT AVG(combined_confidence) FROM submissions")
    avg_confidence = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_submissions": total,
        "likely_human": breakdown.get("likely_human", 0),
        "likely_ai": breakdown.get("likely_ai", 0),
        "uncertain": breakdown.get("uncertain", 0),
        "total_appeals": appeals,
        "appeal_rate": round((appeals / total) * 100, 1),
        "avg_confidence": round(avg_confidence or 0.0, 2)
    }

