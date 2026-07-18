import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        age INTEGER,
        grade TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Tests table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        chapters TEXT,
        score REAL DEFAULT 0,
        max_score REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Questions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER NOT NULL,
        stage TEXT NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL,
        student_answer TEXT,
        is_correct INTEGER,
        trick_explanation TEXT,
        FOREIGN KEY(test_id) REFERENCES tests(id) ON DELETE CASCADE
    )
    ''')
    
    # Analyses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analyses (
        test_id INTEGER PRIMARY KEY,
        beginner_correct INTEGER DEFAULT 0,
        beginner_total INTEGER DEFAULT 0,
        intermediate_correct INTEGER DEFAULT 0,
        intermediate_total INTEGER DEFAULT 0,
        professional_correct INTEGER DEFAULT 0,
        professional_total INTEGER DEFAULT 0,
        chart_image_path TEXT,
        ai_feedback TEXT,
        improvement_tips TEXT,
        FOREIGN KEY(test_id) REFERENCES tests(id) ON DELETE CASCADE
    )
    ''')
    
    # Migration: Add chapters column to tests table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE tests ADD COLUMN chapters TEXT')
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

# Settings Helpers
def get_setting(key, default=None):
    conn = get_db_connection()
    row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    if row:
        return row['value']
    return default

def set_setting(key, value):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

# User Helpers
def get_user_by_email(email):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE email = ?', (email.strip().lower(),)).fetchone()
    conn.close()
    return row

def get_user_by_id(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return row

def create_user(name, email, age, grade):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (name, email, age, grade) VALUES (?, ?, ?, ?)',
            (name.strip(), email.strip().lower(), age, grade.strip())
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        user_id = None
    finally:
        conn.close()
    return user_id

# Test Helpers
def create_test_session(user_id, subject, chapters=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tests (user_id, subject, chapters, status) VALUES (?, ?, ?, ?)',
        (user_id, subject, chapters, 'pending')
    )
    conn.commit()
    test_id = cursor.lastrowid
    conn.close()
    return test_id

def get_test_session(test_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM tests WHERE id = ?', (test_id,)).fetchone()
    conn.close()
    return row

def get_user_tests(user_id):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT t.*, a.chart_image_path, a.ai_feedback,
               (SELECT COUNT(*) FROM questions q WHERE q.test_id = t.id) as total_questions
        FROM tests t
        LEFT JOIN analyses a ON t.id = a.test_id
        WHERE t.user_id = ?
        ORDER BY t.created_at DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return rows

def get_test_questions(test_id):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM questions WHERE test_id = ? ORDER BY id ASC', (test_id,)).fetchall()
    conn.close()
    return rows

def save_answer(question_id, student_answer, is_correct):
    conn = get_db_connection()
    conn.execute(
        'UPDATE questions SET student_answer = ?, is_correct = ? WHERE id = ?',
        (student_answer, 1 if is_correct else 0, question_id)
    )
    conn.commit()
    conn.close()

def update_test_score(test_id, score, max_score):
    conn = get_db_connection()
    conn.execute(
        'UPDATE tests SET score = ?, max_score = ?, status = ? WHERE id = ?',
        (score, max_score, 'completed', test_id)
    )
    conn.commit()
    conn.close()

def get_test_analysis(test_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM analyses WHERE test_id = ?', (test_id,)).fetchone()
    conn.close()
    return row

def save_test_analysis(test_id, beg_correct, beg_total, int_correct, int_total, prof_correct, prof_total, chart_path, feedback, tips):
    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO analyses 
        (test_id, beginner_correct, beginner_total, intermediate_correct, intermediate_total, professional_correct, professional_total, chart_image_path, ai_feedback, improvement_tips)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (test_id, beg_correct, beg_total, int_correct, int_total, prof_correct, prof_total, chart_path, feedback, tips))
    conn.commit()
    conn.close()

def insert_test_questions(test_id, questions):
    conn = get_db_connection()
    cursor = conn.cursor()
    for q in questions:
        cursor.execute('''
            INSERT INTO questions (test_id, stage, question_text, option_a, option_b, option_c, option_d, correct_option, student_answer, is_correct, trick_explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)
        ''', (
            test_id,
            q['stage'],
            q['question'],
            q['option_a'],
            q['option_b'],
            q['option_c'],
            q['option_d'],
            q['correct_option'],
            q['trick_explanation']
        ))
    conn.commit()
    conn.close()

def delete_test_session(test_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM tests WHERE id = ?', (test_id,))
    conn.commit()
    conn.close()

def get_user_previous_questions(user_id, subject):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT q.question_text 
        FROM questions q
        JOIN tests t ON q.test_id = t.id
        WHERE t.user_id = ? AND LOWER(t.subject) = LOWER(?)
    ''', (user_id, subject.strip())).fetchall()
    conn.close()
    return [row['question_text'] for row in rows]


