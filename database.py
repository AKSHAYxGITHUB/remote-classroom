import sqlite3
from datetime import datetime

DATABASE = 'rajasthan_digi_shala.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'teacher')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Courses table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            teacher_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users (id)
        )
    ''')
    
    # Enrollment table (many-to-many relationship between students and courses)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS enrollment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id),
            UNIQUE(user_id, course_id)
        )
    ''')
    
    # Materials table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            filepath TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')
    
    # Attendance table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            date DATE NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('present', 'absent')),
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id),
            UNIQUE(student_id, course_id, date)
        )
    ''')
    
    # Posts table (for forum)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Replies table (for forum)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    
    # Insert sample data if tables are empty
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        insert_sample_data(conn)
    
    conn.close()

def insert_sample_data(conn):
    from werkzeug.security import generate_password_hash
    
    # Sample users
    users = [
        ('teacher1', generate_password_hash('password123'), 'teacher'),
        ('student1', generate_password_hash('password123'), 'student'),
        ('student2', generate_password_hash('password123'), 'student'),
    ]
    
    conn.executemany('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', users)
    
    # Sample courses
    courses = [
        ('Hindi Literature', 'Comprehensive course on Hindi literature and poetry', 1),
        ('Mathematics Basics', 'Fundamental mathematics concepts for beginners', 1),
        ('Rajasthani Culture', 'Exploring the rich culture and traditions of Rajasthan', 1),
    ]
    
    conn.executemany('INSERT INTO courses (title, description, teacher_id) VALUES (?, ?, ?)', courses)
    
    # Sample enrollments
    enrollments = [
        (2, 1), (2, 2), (2, 3),  # student1 enrolled in all courses
        (3, 1), (3, 2),           # student2 enrolled in courses 1 and 2
    ]
    
    conn.executemany('INSERT INTO enrollment (user_id, course_id) VALUES (?, ?)', enrollments)
    
    conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")