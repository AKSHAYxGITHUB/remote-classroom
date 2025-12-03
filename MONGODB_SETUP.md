# MongoDB Setup Guide for Remote Classroom

This application has been successfully converted from PostgreSQL to MongoDB. No UI changes are required!

## Prerequisites

- Python 3.7 or higher
- MongoDB Atlas account or local MongoDB installation

## Installation

### 1. Update Dependencies

The `requirements.txt` has been updated to use MongoDB:

```bash
pip install -r requirements.txt
```

This will install:
- `pymongo==4.5.0` - MongoDB Python driver
- `python-dotenv==1.0.0` - For environment variables

### 2. Configure Database Connection

You have two options:

#### Option A: MongoDB Atlas (Cloud) - Recommended for Hosting
1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free account and cluster
3. Get your connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/remote_classroom?retryWrites=true&w=majority`)
4. Set the environment variable:

```bash
export MONGODB_URL="mongodb+srv://username:password@cluster.mongodb.net/remote_classroom?retryWrites=true&w=majority"
```

#### Option B: Local MongoDB
1. Install MongoDB from [mongodb.com](https://www.mongodb.com/try/download/community)
2. Start MongoDB service
3. Set environment variable:

```bash
export MONGODB_URL="mongodb://localhost:27017"
```

### 3. Initialize Database

Run the initialization script to create collections and indexes:

```bash
python database.py
```

This will:
- Create all necessary collections (users, courses, enrollment, materials, attendance, posts, replies)
- Create indexes for optimal query performance
- Display a success message

## Key Changes Made

### Database Structure
- PostgreSQL tables → MongoDB collections
- Integer IDs → MongoDB ObjectIds (BSON format)
- Automatic timestamps using Python datetime

### Modified Database Functions
All database operations now use MongoDB:
- `get_db_connection()` - Returns MongoDB database instance
- `create_user()` - Insert user document
- `get_user_by_id()` - Find user by ObjectId
- `get_user_by_username()` - Find user by username
- `create_course()` - Insert course document
- `get_course()` - Get course by ID
- `get_teacher_courses()` - Get teacher's courses with enrollment count
- `get_student_courses()` - Get enrolled courses for student
- `get_available_courses()` - Get courses not enrolled by student
- `enroll_student()` - Add enrollment document
- `is_enrolled()` - Check enrollment status
- `get_course_materials()` - Get course materials
- `add_material()` - Upload material metadata
- `get_material()` - Get material by ID
- `get_course_posts()` - Get posts with user info and reply count
- `create_post()` - Create discussion post
- `create_reply()` - Add reply to post
- `record_attendance()` - Record/update attendance
- `get_course_students()` - Get enrolled students
- `delete_attendance_for_date()` - Delete attendance records

### Application Changes
- Updated imports to use MongoDB functions from `database.py`
- Modified route handlers to use new database functions
- All ObjectIds are converted to strings for user sessions
- No UI changes required - all endpoints work the same

## Running the Application

### Development
```bash
python app.py
```

### Production (with Gunicorn)
```bash
gunicorn app:app
```

## Deployment on Render.com

1. Set environment variable in Render dashboard:
   - Name: `MONGODB_URL`
   - Value: Your MongoDB Atlas connection string

2. The application will automatically initialize the database on first run

3. Push your code and deploy!

## Testing

The application maintains full compatibility with existing UI:
- User registration and login work with hashed passwords
- Course creation and enrollment
- Material uploads and downloads
- Discussion posts and replies
- Attendance tracking

No frontend changes needed!

## Troubleshooting

### Connection Errors
- Verify `MONGODB_URL` is set correctly
- Check MongoDB service is running (for local MongoDB)
- For Atlas, whitelist your IP address in security settings

### Collection Not Found
Run `python database.py` to initialize collections

### Import Errors
Ensure all dependencies are installed: `pip install -r requirements.txt`

## Database Schema

### users
```json
{
  "_id": ObjectId,
  "username": String (unique),
  "password_hash": String,
  "role": String ("student" or "teacher"),
  "created_at": DateTime
}
```

### courses
```json
{
  "_id": ObjectId,
  "title": String,
  "description": String,
  "teacher_id": ObjectId,
  "created_at": DateTime
}
```

### enrollment
```json
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "course_id": ObjectId,
  "enrolled_at": DateTime
}
```

### materials
```json
{
  "_id": ObjectId,
  "course_id": ObjectId,
  "title": String,
  "filepath": String,
  "uploaded_at": DateTime
}
```

### attendance
```json
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "course_id": ObjectId,
  "date": Date,
  "status": String ("present" or "absent"),
  "recorded_at": DateTime
}
```

### posts
```json
{
  "_id": ObjectId,
  "course_id": ObjectId,
  "user_id": ObjectId,
  "content": String,
  "timestamp": DateTime
}
```

### replies
```json
{
  "_id": ObjectId,
  "post_id": ObjectId,
  "user_id": ObjectId,
  "content": String,
  "timestamp": DateTime
}
```

## Support

For issues or questions about MongoDB integration, refer to:
- [MongoDB Python Driver Documentation](https://pymongo.readthedocs.io/)
- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)
