import os
import psycopg2
from psycopg2.extras import DictCursor

# Get the database connection URL from the environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.
    The connection string is retrieved from the DATABASE_URL environment
    variable, which is the standard practice for services like Render.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        # Use DictCursor to get rows as dictionaries (like sqlite3.Row)
        conn.cursor_factory = DictCursor
        return conn
    except psycopg2.OperationalError as e:
        # A more descriptive error message for connection issues
        raise Exception(f"Error connecting to the database: {e}")

def init_db():
    """
    Initializes the database schema.
    This function creates all the necessary tables if they don't already exist.
    It's safe to run this multiple times.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'teacher')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Courses table
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

    # Enrollment table
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

    # Materials table
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

    # Attendance table
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

    # Posts table (for forum)
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

    # Replies table (for forum)
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
    # This allows you to run `python database.py` to set up the schema
    # after you've set the DATABASE_URL environment variable.
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
    else:
        init_db()
