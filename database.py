import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson.objectid import ObjectId
from datetime import datetime

# Global MongoDB connection
_db = None

def to_object_id(value):
    """Convert string to ObjectId safely"""
    try:
        if isinstance(value, str):
            return ObjectId(value)
        return value
    except Exception as e:
        print(f"Error converting to ObjectId: {e}")
        return value

def get_db_connection():
    """Get MongoDB database connection"""
    global _db
    
    MONGODB_URL = os.environ.get('MONGODB_URL') or os.environ.get('DATABASE_URL')
    
    if MONGODB_URL is None:
        raise Exception("MONGODB_URL or DATABASE_URL environment variable not set")
    
    try:
        # Connection options for MongoDB Atlas - PyMongo compatible
        client = MongoClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=20000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000,
            retryWrites=True,
            tls=True,
            tlsAllowInvalidCertificates=True,
            maxPoolSize=50,
            minPoolSize=10
        )
        # Verify connection with ping
        client.admin.command('ping', timeoutMS=20000)
        _db = client['remote_classroom']
        print("✓ MongoDB connection successful")
        return _db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"✗ MongoDB connection failed: {e}")
        print("Troubleshooting steps:")
        print("1. Verify IP whitelist in MongoDB Atlas includes 0.0.0.0/0 or Render IPs")
        print("2. Check connection string format: mongodb+srv://user:pass@cluster.mongodb.net/database")
        print("3. Ensure username and password are correct")
        raise Exception(f"Error connecting to MongoDB: {e}")

def init_db():
    """Initialize MongoDB collections and indexes"""
    try:
        db = get_db_connection()
        
        # Create collections if they don't exist
        collections = ['users', 'courses', 'enrollment', 'materials', 'attendance', 'posts', 'replies']
        
        for collection_name in collections:
            if collection_name not in db.list_collection_names():
                db.create_collection(collection_name)
        
        # Create indexes for better query performance
        db['users'].create_index('username', unique=True)
        db['enrollment'].create_index([('user_id', 1), ('course_id', 1)], unique=True)
        db['attendance'].create_index([('student_id', 1), ('course_id', 1), ('date', 1)], unique=True)
        db['materials'].create_index('course_id')
        db['posts'].create_index('course_id')
        db['replies'].create_index('post_id')
        
        print("MongoDB collections and indexes initialized successfully.")
    except Exception as e:
        raise Exception(f"Error initializing MongoDB: {e}")

# Utility functions for document operations
def create_user(username, password_hash, role):
    """Create a new user"""
    db = get_db_connection()
    user = {
        'username': username,
        'password_hash': password_hash,
        'role': role,
        'created_at': datetime.now()
    }
    result = db['users'].insert_one(user)
    return result.inserted_id

def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        db = get_db_connection()
        # Ensure user_id is a valid ObjectId
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return db['users'].find_one({'_id': user_id})
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None

def get_user_by_username(username):
    """Get user by username"""
    db = get_db_connection()
    return db['users'].find_one({'username': username})

def create_course(title, description, teacher_id):
    """Create a new course"""
    try:
        db = get_db_connection()
        # Ensure teacher_id is a valid ObjectId
        if isinstance(teacher_id, str):
            teacher_id = ObjectId(teacher_id)
        course = {
            'title': title,
            'description': description,
            'teacher_id': teacher_id,
            'created_at': datetime.now()
        }
        result = db['courses'].insert_one(course)
        return result.inserted_id
    except Exception as e:
        print(f"Error creating course: {e}")
        raise

def get_course(course_id):
    """Get course by ID"""
    try:
        db = get_db_connection()
        if isinstance(course_id, str):
            course_id = ObjectId(course_id)
        return db['courses'].find_one({'_id': course_id})
    except Exception as e:
        print(f"Error getting course: {e}")
        return None

def get_teacher_courses(teacher_id):
    """Get all courses for a teacher"""
    db = get_db_connection()
    return list(db['courses'].aggregate([
        {'$match': {'teacher_id': to_object_id(teacher_id)}},
        {'$lookup': {
            'from': 'enrollment',
            'localField': '_id',
            'foreignField': 'course_id',
            'as': 'enrollments'
        }},
        {'$addFields': {'enrolled_count': {'$size': '$enrollments'}}},
        {'$project': {'enrollments': 0}}
    ]))

def get_student_courses(student_id):
    """Get enrolled courses for a student"""
    db = get_db_connection()
    return list(db['courses'].aggregate([
        {'$lookup': {
            'from': 'enrollment',
            'localField': '_id',
            'foreignField': 'course_id',
            'as': 'enrollments'
        }},
        {'$match': {'enrollments.user_id': to_object_id(student_id)}},
        {'$lookup': {
            'from': 'users',
            'localField': 'teacher_id',
            'foreignField': '_id',
            'as': 'teacher'
        }},
        {'$addFields': {
            'teacher_name': {'$arrayElemAt': ['$teacher.username', 0]},
            'present_count': {
                '$cond': [
                    {'$isArray': '$enrollments'},
                    {'$size': '$enrollments'},
                    0
                ]
            }
        }},
        {'$project': {'enrollments': 0, 'teacher': 0}}
    ]))

def get_available_courses(student_id):
    """Get courses not enrolled by student"""
    db = get_db_connection()
    return list(db['courses'].aggregate([
        {'$lookup': {
            'from': 'enrollment',
            'let': {'course_id': '$_id'},
            'pipeline': [
                {'$match': {
                    'user_id': to_object_id(student_id),
                    'course_id': '$$course_id'
                }}
            ],
            'as': 'enrollments'
        }},
        {'$match': {'enrollments': {'$size': 0}}},
        {'$lookup': {
            'from': 'users',
            'localField': 'teacher_id',
            'foreignField': '_id',
            'as': 'teacher'
        }},
        {'$addFields': {'teacher_name': {'$arrayElemAt': ['$teacher.username', 0]}}},
        {'$project': {'enrollments': 0, 'teacher': 0}}
    ]))

def enroll_student(user_id, course_id):
    """Enroll student in course"""
    db = get_db_connection()
    enrollment = {
        'user_id': to_object_id(user_id),
        'course_id': to_object_id(course_id),
        'enrolled_at': datetime.now()
    }
    db['enrollment'].insert_one(enrollment)

def is_enrolled(user_id, course_id):
    """Check if student is enrolled in course"""
    db = get_db_connection()
    return db['enrollment'].find_one({'user_id': to_object_id(user_id), 'course_id': to_object_id(course_id)}) is not None

def get_course_materials(course_id):
    """Get all materials for a course"""
    db = get_db_connection()
    return list(db['materials'].find({'course_id': to_object_id(course_id)}))

def add_material(course_id, title, filepath):
    """Add material to course"""
    db = get_db_connection()
    material = {
        'course_id': to_object_id(course_id),
        'title': title,
        'filepath': filepath,
        'uploaded_at': datetime.now()
    }
    result = db['materials'].insert_one(material)
    return result.inserted_id

def get_material(material_id):
    """Get material by ID"""
    db = get_db_connection()
    return db['materials'].find_one({'_id': to_object_id(material_id)})

def get_course_posts(course_id):
    """Get all posts for a course"""
    db = get_db_connection()
    return list(db['posts'].aggregate([
        {'$match': {'course_id': to_object_id(course_id)}},
        {'$lookup': {
            'from': 'users',
            'localField': 'user_id',
            'foreignField': '_id',
            'as': 'user'
        }},
        {'$lookup': {
            'from': 'replies',
            'localField': '_id',
            'foreignField': 'post_id',
            'as': 'replies'
        }},
        {'$addFields': {
            'username': {'$arrayElemAt': ['$user.username', 0]},
            'reply_count': {'$size': '$replies'}
        }},
        {'$project': {'user': 0, 'replies': 0}},
        {'$sort': {'timestamp': -1}}
    ]))

def create_post(course_id, user_id, content):
    """Create a new post"""
    db = get_db_connection()
    post = {
        'course_id': to_object_id(course_id),
        'user_id': to_object_id(user_id),
        'content': content,
        'timestamp': datetime.now()
    }
    result = db['posts'].insert_one(post)
    return result.inserted_id

def create_reply(post_id, user_id, content):
    """Create a reply to a post"""
    db = get_db_connection()
    reply = {
        'post_id': to_object_id(post_id),
        'user_id': to_object_id(user_id),
        'content': content,
        'timestamp': datetime.now()
    }
    result = db['replies'].insert_one(reply)
    return result.inserted_id

def record_attendance(student_id, course_id, date, status):
    """Record attendance"""
    db = get_db_connection()
    attendance = {
        'student_id': to_object_id(student_id),
        'course_id': to_object_id(course_id),
        'date': date,
        'status': status,
        'recorded_at': datetime.now()
    }
    db['attendance'].update_one(
        {'student_id': to_object_id(student_id), 'course_id': to_object_id(course_id), 'date': date},
        {'$set': attendance},
        upsert=True
    )

def get_course_students(course_id):
    """Get all students enrolled in a course"""
    db = get_db_connection()
    return list(db['users'].aggregate([
        {'$lookup': {
            'from': 'enrollment',
            'localField': '_id',
            'foreignField': 'user_id',
            'as': 'enrollments'
        }},
        {'$match': {
            'role': 'student',
            'enrollments.course_id': to_object_id(course_id)
        }},
        {'$project': {'enrollments': 0}}
    ]))

def delete_attendance_for_date(course_id, date):
    """Delete all attendance records for a course on a specific date"""
    db = get_db_connection()
    db['attendance'].delete_many({'course_id': to_object_id(course_id), 'date': date})

if __name__ == '__main__':
    init_db()
