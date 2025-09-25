from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date
import json
# Import the new database connection function
from database import init_db, get_db_connection
import psycopg2

app = Flask(__name__)
# It's a good practice to get the secret key from an environment variable
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-default-fallback-secret-key')
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user:
        # Access columns by index or key if using DictCursor
        return User(user['id'], user['username'], user['role'])
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['username'], user['role'])
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if user already exists
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        existing_user = cur.fetchone()
        if existing_user:
            flash('Username already exists')
            cur.close()
            conn.close()
            return render_template('register.html')

        # Create new user
        password_hash = generate_password_hash(password)
        cur.execute('INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)',
                    (username, password_hash, role))
        conn.commit()
        cur.close()
        conn.close()

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    if current_user.role == 'teacher':
        cur.execute('''
            SELECT c.*, COUNT(e.user_id) as enrolled_count
            FROM courses c
            LEFT JOIN enrollment e ON c.id = e.course_id
            WHERE c.teacher_id = %s
            GROUP BY c.id
        ''', (current_user.id,))
        courses = cur.fetchall()
        available_courses = []

    else:  # Student
        cur.execute('''
            SELECT c.*, u.username as teacher_name,
            (SELECT COUNT(*) FROM attendance WHERE student_id = %s AND course_id = c.id AND status = 'present') as present_count,
            (SELECT COUNT(*) FROM attendance WHERE student_id = %s AND course_id = c.id) as total_attendance
            FROM courses c
            JOIN users u ON c.teacher_id = u.id
            JOIN enrollment e ON c.id = e.course_id
            WHERE e.user_id = %s
        ''', (current_user.id, current_user.id, current_user.id))
        enrolled_courses = cur.fetchall()

        cur.execute('''
            SELECT c.*, u.username as teacher_name
            FROM courses c
            JOIN users u ON c.teacher_id = u.id
            WHERE c.id NOT IN (
                SELECT course_id FROM enrollment WHERE user_id = %s
            )
        ''', (current_user.id,))
        available_courses = cur.fetchall()
        courses = enrolled_courses

    cur.close()
    conn.close()
    return render_template('dashboard.html', courses=courses, available_courses=available_courses)

@app.route('/create_course', methods=['POST'])
@login_required
def create_course():
    if current_user.role != 'teacher':
        flash('Only teachers can create courses')
        return redirect(url_for('dashboard'))

    title = request.form['title']
    description = request.form['description']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO courses (title, description, teacher_id) VALUES (%s, %s, %s)',
                (title, description, current_user.id))
    conn.commit()
    cur.close()
    conn.close()

    flash('Course created successfully!')
    return redirect(url_for('dashboard'))

@app.route('/course/<int:course_id>')
@login_required
def course(course_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        SELECT c.*, u.username as teacher_name
        FROM courses c
        JOIN users u ON c.teacher_id = u.id
        WHERE c.id = %s
    ''', (course_id,))
    course_data = cur.fetchone()

    if not course_data:
        flash('Course not found')
        cur.close()
        conn.close()
        return redirect(url_for('dashboard'))

    # Check access
    if current_user.role == 'student':
        cur.execute('SELECT * FROM enrollment WHERE user_id = %s AND course_id = %s',
                    (current_user.id, course_id))
        if not cur.fetchone():
            flash('You are not enrolled in this course')
            cur.close()
            conn.close()
            return redirect(url_for('dashboard'))
    elif current_user.role == 'teacher' and course_data['teacher_id'] != current_user.id:
        flash('You do not have access to this course')
        cur.close()
        conn.close()
        return redirect(url_for('dashboard'))

    cur.execute('SELECT * FROM materials WHERE course_id = %s', (course_id,))
    materials = cur.fetchall()

    cur.execute('''
        SELECT p.*, u.username, COUNT(r.id) as reply_count
        FROM posts p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN replies r ON p.id = r.post_id
        WHERE p.course_id = %s
        GROUP BY p.id, u.username, p.content, p.timestamp
        ORDER BY p.timestamp DESC
    ''', (course_id,))
    posts = cur.fetchall()

    students = []
    if current_user.role == 'teacher':
        cur.execute('''
            SELECT u.* FROM users u
            JOIN enrollment e ON u.id = e.user_id
            WHERE e.course_id = %s AND u.role = 'student'
        ''', (course_id,))
        students = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('course.html', course=course_data, materials=materials, posts=posts, students=students)


@app.route('/upload_material/<int:course_id>', methods=['POST'])
@login_required
def upload_material(course_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Only teachers can upload materials'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        title = request.form.get('title', filename)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO materials (course_id, title, filepath) VALUES (%s, %s, %s)',
                    (course_id, title, filepath))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Material uploaded successfully'})

@app.route('/download_material/<int:material_id>')
@login_required
def download_material(material_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM materials WHERE id = %s', (material_id,))
    material = cur.fetchone()
    cur.close()
    conn.close()

    if not material:
        flash('Material not found')
        return redirect(url_for('dashboard'))

    return send_file(material['filepath'], as_attachment=True)

@app.route('/enroll/<int:course_id>')
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        flash('Only students can enroll in courses')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM enrollment WHERE user_id = %s AND course_id = %s',
                (current_user.id, course_id))
    if cur.fetchone():
        flash('You are already enrolled in this course')
    else:
        cur.execute('INSERT INTO enrollment (user_id, course_id) VALUES (%s, %s)',
                    (current_user.id, course_id))
        conn.commit()
        flash('Successfully enrolled in the course!')

    cur.close()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/take_attendance/<int:course_id>', methods=['POST'])
@login_required
def take_attendance(course_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Only teachers can take attendance'}), 403

    attendance_date = request.form['date']
    student_ids = request.form.getlist('students')

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        SELECT u.id FROM users u
        JOIN enrollment e ON u.id = e.user_id
        WHERE e.course_id = %s AND u.role = 'student'
    ''', (course_id,))
    all_students = cur.fetchall()

    cur.execute('DELETE FROM attendance WHERE course_id = %s AND date = %s',
                (course_id, attendance_date))

    for student in all_students:
        status = 'present' if str(student['id']) in student_ids else 'absent'
        cur.execute('INSERT INTO attendance (student_id, course_id, date, status) VALUES (%s, %s, %s, %s)',
                    (student['id'], course_id, attendance_date, status))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'success': True, 'message': 'Attendance recorded successfully'})

@app.route('/api/ask', methods=['POST'])
@login_required
def ask_ai():
    data = request.json
    question = data.get('question', '')
    course_id = data.get('course_id', '')

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM materials WHERE course_id = %s', (course_id,))
    materials = cur.fetchall()
    cur.close()
    conn.close()

    context = "Course materials context: " + " ".join([m['title'] for m in materials])

    try:
        response = get_ai_response(question, context)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': 'AI service temporarily unavailable'}), 500

@app.route('/post_question/<int:course_id>', methods=['POST'])
@login_required
def post_question(course_id):
    content = request.form['content']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO posts (course_id, user_id, content, timestamp) VALUES (%s, %s, %s, %s)',
                (course_id, current_user.id, content, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('course', course_id=course_id))

@app.route('/post_reply/<int:post_id>', methods=['POST'])
@login_required
def post_reply(post_id):
    content = request.form['content']
    course_id = request.form['course_id']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO replies (post_id, user_id, content, timestamp) VALUES (%s, %s, %s, %s)',
                (post_id, current_user.id, content, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('course', course_id=course_id))

@app.route('/mission')
def mission():
    return render_template('mission.html')

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Rajasthan Digi-Shala",
        "short_name": "DigiShala",
        "description": "Broker-Free Digital Education Platform for Rajasthan",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#4F46E5",
        "theme_color": "#F59E0B",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

if __name__ == '__main__':
    # Initialize the database schema if running this script directly
    # In a production environment on Render, you might run this from the shell
    init_db()
    # For local testing, you might use a different port
    app.run(debug=True, port=5001)
