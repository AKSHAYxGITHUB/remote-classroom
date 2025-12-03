from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date
import json
from database import (
    init_db, get_db_connection, get_user_by_id, get_user_by_username,
    create_user, create_course, get_course, get_teacher_courses, get_student_courses,
    get_available_courses, enroll_student, is_enrolled, get_course_materials,
    add_material, get_material, get_course_posts, create_post, create_reply,
    record_attendance, get_course_students, delete_attendance_for_date
)
from bson.objectid import ObjectId

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-default-fallback-secret-key')
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database on app startup
try:
    init_db()
    print("Database initialized successfully")
except Exception as e:
    print(f"Warning: Could not initialize database on startup: {e}")

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
    try:
        user_doc = get_user_by_id(user_id)
        if user_doc:
            return User(str(user_doc['_id']), user_doc['username'], user_doc['role'])
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)

        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(str(user['_id']), user['username'], user['role'])
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']

            existing_user = get_user_by_username(username)
            if existing_user:
                flash('Username already exists')
                return render_template('register.html')

            password_hash = generate_password_hash(password)
            create_user(username, password_hash, role)

            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Registration error: {e}")
            flash(f'Registration failed: {str(e)}')
            return render_template('register.html')

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'teacher':
        courses = get_teacher_courses(current_user.id)
        available_courses = []
    else:
        courses = get_student_courses(current_user.id)
        available_courses = get_available_courses(current_user.id)

    # Add id field for template compatibility with MongoDB _id
    for course in courses:
        course['id'] = str(course['_id'])
    
    for course in available_courses:
        course['id'] = str(course['_id'])

    return render_template('dashboard.html', courses=courses, available_courses=available_courses)

@app.route('/create_course', methods=['POST'])
@login_required
def create_course_route():
    if current_user.role != 'teacher':
        flash('Only teachers can create courses')
        return redirect(url_for('dashboard'))

    title = request.form['title']
    description = request.form['description']

    create_course(title, description, current_user.id)

    flash('Course created successfully!')
    return redirect(url_for('dashboard'))

@app.route('/course/<course_id>')
@login_required
def course(course_id):
    try:
        course_data = get_course(course_id)

        if not course_data:
            flash('Course not found')
            return redirect(url_for('dashboard'))

        if current_user.role == 'student':
            if not is_enrolled(current_user.id, course_id):
                flash('You are not enrolled in this course')
                return redirect(url_for('dashboard'))
        elif current_user.role == 'teacher' and str(course_data['teacher_id']) != current_user.id:
            flash('You do not have access to this course')
            return redirect(url_for('dashboard'))

        materials = get_course_materials(course_id)
        posts = get_course_posts(course_id)

        students = []
        if current_user.role == 'teacher':
            students = get_course_students(course_id)

        # Add teacher name
        teacher = get_user_by_id(str(course_data['teacher_id']))
        course_data['teacher_name'] = teacher['username'] if teacher else 'Unknown'
        
        # Add id field for template compatibility with MongoDB _id
        course_data['id'] = str(course_data['_id'])
        
        # Add id field to materials and posts for template compatibility
        for material in materials:
            material['id'] = str(material['_id'])
        
        for post in posts:
            post['id'] = str(post['_id'])
        
        # Add id field to students for template compatibility
        for student in students:
            student['id'] = str(student['_id'])
        
        return render_template('course.html', course=course_data, materials=materials, posts=posts, students=students)
    except Exception as e:
        flash(f'Error loading course: {str(e)}')
        return redirect(url_for('dashboard'))


@app.route('/upload_material/<course_id>', methods=['POST'])
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

        add_material(course_id, title, filepath)

        return jsonify({'success': True, 'message': 'Material uploaded successfully'})

@app.route('/download_material/<material_id>')
@login_required
def download_material(material_id):
    try:
        material = get_material(material_id)

        if not material:
            flash('Material not found')
            return redirect(url_for('dashboard'))

        return send_file(material['filepath'], as_attachment=True)
    except Exception as e:
        flash(f'Error downloading material: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/enroll/<course_id>')
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        flash('Only students can enroll in courses')
        return redirect(url_for('dashboard'))

    if is_enrolled(current_user.id, course_id):
        flash('You are already enrolled in this course')
    else:
        enroll_student(current_user.id, course_id)
        flash('Successfully enrolled in the course!')

    return redirect(url_for('dashboard'))

@app.route('/take_attendance/<course_id>', methods=['POST'])
@login_required
def take_attendance(course_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Only teachers can take attendance'}), 403

    attendance_date = request.form['date']
    student_ids = request.form.getlist('students')

    students = get_course_students(course_id)
    
    delete_attendance_for_date(course_id, attendance_date)

    for student in students:
        status = 'present' if str(student['_id']) in student_ids else 'absent'
        record_attendance(str(student['_id']), course_id, attendance_date, status)

    return jsonify({'success': True, 'message': 'Attendance recorded successfully'})

@app.route('/api/ask', methods=['POST'])
@login_required
def ask_ai():
    data = request.json
    question = data.get('question', '')
    course_id = data.get('course_id', '')

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    materials = get_course_materials(course_id)
    context = "Course materials context: " + " ".join([m['title'] for m in materials])

    try:
        response = get_ai_response(question, context)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': 'AI service temporarily unavailable'}), 500

@app.route('/post_question/<course_id>', methods=['POST'])
@login_required
def post_question(course_id):
    content = request.form['content']

    create_post(course_id, current_user.id, content)

    return redirect(url_for('course', course_id=course_id))

@app.route('/post_reply/<post_id>', methods=['POST'])
@login_required
def post_reply(post_id):
    content = request.form['content']
    course_id = request.form['course_id']

    create_reply(post_id, current_user.id, content)

    return redirect(url_for('course', course_id=course_id))

@app.route('/mission')
def mission():
    return render_template('mission.html')

@app.errorhandler(500)
def internal_error(error):
    print(f"500 Error: {error}")
    return jsonify({'error': 'Internal Server Error', 'message': str(error)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not Found', 'message': str(error)}), 404

@app.errorhandler(Exception)
def handle_exception(error):
    print(f"Unhandled Exception: {error}")
    import traceback
    traceback.print_exc()
    return jsonify({'error': 'An error occurred', 'message': str(error)}), 500

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
    # REMOVED init_db() from here
    app.run(debug=True)
