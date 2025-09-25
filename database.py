import os
import psycopg2
from psycopg2.extras import DictCursor

def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL is None:
        raise Exception("DATABASE_URL environment variable not set")
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        conn.cursor_factory = DictCursor
        return conn
    except psycopg2.OperationalError as e:
        raise Exception(f"Error connecting to the database: {e}")

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'teacher')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            teacher_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users (id)
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS enrollment (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id),
            UNIQUE(user_id, course_id)
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            filepath TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            date DATE NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('present', 'absent')),
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id),
            UNIQUE(student_id, course_id, date)
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS replies (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    ''')

    conn.commit()
    cur.close()
    conn.close()
    print("Database schema initialized.")

if __name__ == '__main__':
    init_db()
