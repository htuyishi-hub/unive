"""
UR Course Management Platform - Complete Application
Magic Link Authentication + College/School/Academic Year/Module Hierarchy

All-in-one Flask application combining models, auth, API routes, and configuration.
"""
import os
import uuid
import json
import logging
import requests
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, redirect, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import jwt

# ==================== CONFIGURATION ====================

app = Flask(__name__)

# Secret keys
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'jwt-secret-key-change-in-production')
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 60 * 24  # 24 hours

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///ur_courses.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300
}

# File uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'pdf',
    'doc',
    'docx',
    'xls',
    'xlsx',
    'ppt',
    'pptx',
    'txt',
    'jpg',
    'jpeg',
    'png',
    'gif',
    'zip',
    'rar'}

# Security
app.config['SESSION_COOKIE_SECURE'] = False  # Set True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize extensions
db = SQLAlchemy(app)
CORS(app)
limiter = Limiter(key_func=get_remote_address, app=app)

# ==================== STRUCTURED LOGGING ====================

def setup_logging():
    """Configure structured logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('UR-Courses')

logger = setup_logging()

def log_action(action_type, user_id=None, details=None):
    """Helper function for structured logging"""
    log_data = {
        'action': action_type,
        'user_id': user_id,
        'details': details,
        'ip': request.remote_addr if request else None,
        'user_agent': request.headers.get('User-Agent') if request else None
    }
    logger.info(f"ACTION: {action_type} | Data: {log_data}")

# ==================== EMAIL NOTIFICATIONS ====================

class EmailService:
    """Email service using SendGrid REST API"""

    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY', os.environ.get('MAIL_PASSWORD', ''))
        self.from_email = os.environ.get('MAIL_FROM', 'noreply@ur.ac.rw')
        self.from_name = os.environ.get('MAIL_FROM_NAME', 'UR Course Management')
        self.base_url = 'https://api.sendgrid.com/v3'

    def send(self, to_email, subject, html_body, text_body=None):
        """Send an email via SendGrid REST API"""
        if not self.api_key:
            logger.warning(f"Email not configured. Email would be sent to {to_email}: {subject}")
            return False

        try:
            url = f"{self.base_url}/mail/send"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'personalizations': [{
                    'to': [{'email': to_email}]
                }],
                'from': {
                    'email': self.from_email,
                    'name': self.from_name
                },
                'subject': subject,
                'content': [
                    {'type': 'text/html', 'value': html_body}
                ]
            }

            if text_body:
                payload['content'].insert(0, {'type': 'text/plain', 'value': text_body})

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code in [200, 202, 201]:
                logger.info(f"Email sent to {to_email}: {subject}")
                return                 logger.error("Failed to send email to {to_email}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_magic_link(self, email, magic_link, user_name):
        """Send magic link email"""
        subject = "Your UR Course Management Login Link"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #3b82f6; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #64748b; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎓 University of Rwanda</h1>
                    <p>Course Management Platform</p>
                </div>
                <div class="content">
                    <h2>Hi {user_name},</h2>
                    <p>Click the button below to securely access your courses and materials:</p>
                    <p style="text-align: center;">
                        <a href="{magic_link}" class="button">Access My Courses</a>
                    </p>
                    <p><strong>This link expires in 1 hour</strong> for your security.</p>
                    <p>If you didn't request this email, please ignore it.</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} University of Rwanda. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        text_body = f"Hi {user_name},\n\nClick the link below to access your courses:\n{magic_link}\n\nThis link expires in 1 hour."

        return self.send(email, subject, html_body, text_body)

    def send_assignment_notification(self, email, assignment_title, module_name, due_date):
        """Send assignment notification email"""
        subject = f"New Assignment: {assignment_title}"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📝 Assignment Alert</h1>
                </div>
                <div class="content">
                    <h2>{assignment_title}</h2>
                    <p><strong>Module:</strong> {module_name}</p>
                    <p><strong>Due Date:</strong> {due_date}</p>
                    <p>Please log in to your dashboard to view and submit the assignment.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send(email, subject, html_body)

email_service = EmailService()

# ==================== REDIS CACHING ====================

try:
    import redis
    redis_available = True
    redis_client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        db=0,
        decode_responses=True
    )

    def cache_api_response(key, data, ttl=300):
        """Cache API response in Redis"""
        try:
            redis_client.setex(key, ttl, json.dumps(data))
        except Exception as e:
            logger.warning(f"Redis cache set failed: {e}")

    def get_cached_response(key):
        """Get cached API response from Redis"""
        try:
            data = redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"Redis cache get failed: {e}")
            return None

    def invalidate_cache(pattern):
        """Invalidate cache entries matching pattern"""
        try:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis cache invalidate failed: {e}")

except ImportError:
    redis_available = False
    logger.warning("Redis not installed. Caching disabled.")

    def cache_api_response(key, data, ttl=300):
        pass

    def get_cached_response(key):
        return None

    def invalidate_cache(pattern):
        pass

# ==================== AUDIT LOGGING ====================

class AuditLog(db.Model):
    """Audit log for tracking user actions"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs')

def log_audit(action, resource_type=None, resource_id=None, details=None):
    """Log an audit trail entry"""
    try:
        auth_header = request.headers.get('Authorization')
        user_id = None
        if auth_header:
            token = auth_header[7:]
            result = decode_token(token)
            if result['success']:
                user_id = result['payload'].get('user_id')

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=json.dumps(details) if details else None,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        logger.error(f"Audit log failed: {e}")

# ==================== MODELS ====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='student')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Social Profile Fields
    avatar_url = db.Column(db.String(500), default='')
    bio = db.Column(db.Text, default='')
    skills = db.Column(db.String(500), default='')
    interests = db.Column(db.String(500), default='')

    # Admin Fields
    admin_role = db.Column(db.String(50))
    assigned_college_id = db.Column(db.Integer)
    assigned_program = db.Column(db.String(100))
    admin_status = db.Column(db.String(20))

    # Knowledge Commons
    reputation = db.Column(db.Integer, default=0)
    is_verified_lecturer = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_social_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'avatar_url': self.avatar_url or '',
            'bio': self.bio or '',
            'skills': [s.strip() for s in self.skills.split(',')] if self.skills else [],
            'interests': [i.strip() for i in self.interests.split(',')] if self.interests else [],
        }

class College(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    schools = db.relationship('School', backref='college', lazy='dynamic')

class School(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    modules = db.relationship('Module', backref='school', lazy='dynamic')

class AcademicYear(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    semesters = db.relationship('Semester', backref='academic_year', lazy='dynamic')

class Semester(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    modules = db.relationship('Module', backref='semester', lazy='dynamic')

# Association table for Module-Student
module_students = db.Table('module_students',
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('module_id', db.Integer, db.ForeignKey('module.id'), primary_key=True),
    db.Column('enrolled_at', db.DateTime, default=datetime.utcnow),
    db.Column('status', db.String(20), default='active')
)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semester.id'), nullable=False)
    credits = db.Column(db.Integer, default=0)
    lecturer_name = db.Column(db.String(200))
    lecturer_email = db.Column(db.String(120))
    tags = db.Column(db.String(500))
    module_type = db.Column(db.String(50), default='core')
    max_students = db.Column(db.Integer, default=100)
    is_enrollment_open = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    program = db.Column(db.String(100))
    year_of_study = db.Column(db.Integer)
    external_link = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    students = db.relationship('User', secondary=module_students,
                              backref=db.backref('modules', lazy='dynamic'),
                              lazy='subquery')
    documents = db.relationship('Document', backref='module', lazy='dynamic')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer)
    file_path = db.Column(db.String(500), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    category = db.Column(db.String(50), default='general')
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_published = db.Column(db.Boolean, default=True)
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Announcement(db.Model):
    """Announcements with scope (University, College, Program, Module)"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    scope = db.Column(db.String(50), default='university')
    
    # Scope fields
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=True)
    program = db.Column(db.String(100), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=True)
    
    # Metadata
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.Column(db.Integer)
    
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', foreign_keys=[author_id], backref='announcements')

# ==================== ASSIGNMENT MODELS ====================

class Assignment(db.Model):
    """Assignment model for coursework"""
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    due_date = db.Column(db.DateTime, nullable=False)
    max_score = db.Column(db.Integer, default=100)
    weight = db.Column(db.Float, default=1.0)  # Weight in final grade
    assignment_type = db.Column(db.String(50), default='assignment')  # assignment, quiz, project, exam
    is_published = db.Column(db.Boolean, default=False)
    allow_late_submission = db.Column(db.Boolean, default=True)
    late_penalty_percent = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    module = db.relationship('Module', backref='assignments')
    submissions = db.relationship('Submission', backref='assignment', lazy='dynamic')

class Submission(db.Model):
    """Student submission for assignments"""
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text)  # Text submission
    file_path = db.Column(db.String(500))  # File upload path
    file_name = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    status = db.Column(db.String(20), default='submitted')  # draft, submitted, late, graded
    score = db.Column(db.Float)  # Grade out of max_score
    feedback = db.Column(db.Text)  # Instructor feedback
    graded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    graded_at = db.Column(db.DateTime)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_late = db.Column(db.Boolean, default=False)

    student = db.relationship('User', foreign_keys=[student_id], backref='submissions')
    grader = db.relationship('User', foreign_keys=[graded_by])

# ==================== QUIZ MODELS ====================

class Quiz(db.Model):
    """Quiz/TExam model for assessments"""
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    quiz_type = db.Column(db.String(50), default='quiz')  # quiz, exam, practice
    time_limit = db.Column(db.Integer)  # Time limit in minutes
    max_attempts = db.Column(db.Integer, default=1)
    passing_score = db.Column(db.Float, default=60.0)  # Percentage
    shuffle_questions = db.Column(db.Boolean, default=True)
    show_results = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=False)
    available_from = db.Column(db.DateTime)
    available_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    module = db.relationship('Module', backref='quizzes')
    questions = db.relationship('Question', backref='quiz', lazy='dynamic', order_by='Question.order')
    submissions = db.relationship('QuizSubmission', backref='quiz', lazy='dynamic')

class Question(db.Model):
    """Question model for quizzes"""
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # multiple_choice, true_false, short_answer
    question_text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text)  # Show after answering
    points = db.Column(db.Float, default=1.0)
    order = db.Column(db.Integer, default=0)
    is_required = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    options = db.relationship('QuestionOption', backref='question', lazy='dynamic', cascade='all, delete-orphan')

class QuestionOption(db.Model):
    """Options for multiple choice questions"""
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)

class QuizSubmission(db.Model):
    """Student quiz submission"""
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attempt_number = db.Column(db.Integer, default=1)
    score = db.Column(db.Float)
    max_score = db.Column(db.Float)
    percentage = db.Column(db.Float)
    passed = db.Column(db.Boolean)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    time_spent_seconds = db.Column(db.Integer)

    student = db.relationship('User', backref='quiz_submissions')
    answers = db.relationship('QuizAnswer', backref='submission', lazy='dynamic', cascade='all, delete-orphan')

class QuizAnswer(db.Model):
    """Student answer to a question"""
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('quiz_submission.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.Text)
    selected_options = db.Column(db.Text)  # JSON array of option IDs
    is_correct = db.Column(db.Boolean)
    points_earned = db.Column(db.Float, default=0)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    question = db.relationship('Question')

# ==================== DISCUSSION FORUM MODELS ====================

class Forum(db.Model):
    """Discussion forum per module"""
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=True)
    allow_attachments = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    module = db.relationship('Module', backref='forums')
    posts = db.relationship('ForumPost', backref='forum', lazy='dynamic', order_by='ForumPost.created_at.desc()')

class ForumPost(db.Model):
    """Forum post (thread starter)"""
    id = db.Column(db.Integer, primary_key=True)
    forum_id = db.Column(db.Integer, db.ForeignKey('forum.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    reply_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', backref='forum_posts')
    comments = db.relationship('ForumComment', backref='post', lazy='dynamic', order_by='ForumComment.created_at')

class ForumComment(db.Model):
    """Forum comment/reply"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('forum_comment.id'))  # For nested replies
    content = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref='forum_comments')
    parent = db.relationship('ForumComment', remote_side=[id], backref='replies')

# ==================== NOTIFICATION MODELS ====================

class Notification(db.Model):
    """User notifications"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info')  # info, warning, success, assignment, grade
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')

# ==================== GRADE BOOK MODELS ====================

class Grade(db.Model):
    """Student grade for a module"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    assignment_score = db.Column(db.Float, default=0)
    quiz_score = db.Column(db.Float, default=0)
    exam_score = db.Column(db.Float, default=0)
    total_score = db.Column(db.Float)
    grade_letter = db.Column(db.String(5))
    gpa_points = db.Column(db.Float)
    credits_earned = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semester.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship('User', backref='grades')
    module = db.relationship('Module')
    semester = db.relationship('Semester')

# ==================== GAMIFICATION MODELS ====================

class Badge(db.Model):
    """Achievement badges"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))  # Emoji or icon name
    category = db.Column(db.String(50))  # achievement, milestone, social, academic
    points_reward = db.Column(db.Integer, default=0)
    rarity = db.Column(db.String(20), default='common')  # common, rare, epic, legendary
    requirement_type = db.Column(db.String(50))  # courses_completed, perfect_quiz, etc.
    requirement_value = db.Column(db.Integer)  # Number required
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_badges = db.relationship('UserBadge', backref='badge', lazy='dynamic')

class UserBadge(db.Model):
    """User earned badges"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='user_badges')

class PointTransaction(db.Model):
    """Point transactions for users"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Integer, nullable=False)  # Positive or negative
    transaction_type = db.Column(db.String(50))  # earned, redeemed, bonus, penalty
    source = db.Column(db.String(100))  # quiz_completed, badge_earned, etc.
    source_id = db.Column(db.String(100))  # ID of related entity
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='point_transactions')

class Streak(db.Model):
    """User learning streaks"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    streak_type = db.Column(db.String(50), default='daily_login')  # daily_login, submission
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_activity_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='streaks')

class Leaderboard(db.Model):
    """Leaderboard entries"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leaderboard_type = db.Column(db.String(50), default='overall')  # overall, weekly, monthly, course
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    rank = db.Column(db.Integer)
    score = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User')

# ==================== ANALYTICS MODELS ====================

class AnalyticsEvent(db.Model):
    """Track user events for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    event_type = db.Column(db.String(100), nullable=False)  # page_view, quiz_start, etc.
    event_data = db.Column(db.Text)  # JSON
    session_id = db.Column(db.String(100))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='analytics_events')

class PerformanceMetrics(db.Model):
    """Aggregated performance metrics"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=True)
    metric_type = db.Column(db.String(50))  # avg_quiz_score, completion_rate, etc.
    metric_value = db.Column(db.Float)
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='performance_metrics')
    module = db.relationship('Module')

class StudySession(db.Model):
    """Track study sessions"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    pages_viewed = db.Column(db.Integer, default=0)
    resources_accessed = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='study_sessions')
    module = db.relationship('Module')



# ==================== SOCIAL NETWORK MODELS ====================

class SocialPost(db.Model):
    """Social posts for learning network"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(50), default='general')
    resource_url = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    is_pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', backref='social_posts')
    likes = db.relationship('SocialLike', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('SocialComment', backref='post', lazy='dynamic', order_by='SocialComment.created_at.asc()')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'author_name': self.author.name,
            'author_avatar': self.author.avatar_url or '',
            'content': self.content,
            'post_type': self.post_type,
            'resource_url': self.resource_url or '',
            'image_url': self.image_url or '',
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'is_liked': False,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class SocialLike(db.Model):
    """Likes on social posts"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('social_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='_post_user_like_uc'),)


class SocialComment(db.Model):
    """Threaded comments on posts"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('social_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('social_comment.id'), nullable=True)
    likes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', backref='social_comments')
    parent = db.relationship('SocialComment', remote_side=[id], backref='replies')

    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'user_id': self.user_id,
            'author_name': self.author.name,
            'author_avatar': self.author.avatar_url or '',
            'content': self.content,
            'parent_id': self.parent_id,
            'likes_count': self.likes_count,
            'replies': [r.to_dict() for r in self.replies] if self.replies else [],
            'created_at': self.created_at.isoformat()
        }


class SocialFollow(db.Model):
    """Follow relationships between users"""
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='_follow_uc'),)

    follower = db.relationship('User', foreign_keys=[follower_id], backref='following')
    followed = db.relationship('User', foreign_keys=[followed_id], backref='followers')


class FriendRequest(db.Model):
    """Friend requests for study buddies"""
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    message = db.Column(db.Text, nullable=True)
    is_quick_friend = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('from_user_id', 'to_user_id', name='_friend_request_uc'),)

    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='friend_requests_sent')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='friend_requests_received')

    def to_dict(self):
        return {
            'id': self.id,
            'from_user_id': self.from_user_id,
            'from_user_name': self.from_user.name,
            'from_user_avatar': self.from_user.avatar_url or '',
            'to_user_id': self.to_user_id,
            'status': self.status,
            'message': self.message or '',
            'is_quick_friend': self.is_quick_friend,
            'created_at': self.created_at.isoformat()
        }


class SocialMention(db.Model):
    """Track @mentions in posts and comments"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('social_post.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('social_comment.id'), nullable=True)
    mentioned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mentioned_name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    mentioned_by = db.relationship('User', foreign_keys=[mentioned_by_id], backref='mentions_made')


class KnowledgePost(db.Model):
    """Knowledge Commons posts"""
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(20), default='insight')
    faculty_code = db.Column(db.String(20))
    course_code = db.Column(db.String(50))
    course_name = db.Column(db.String(200))
    tags = db.Column(db.String(500))
    is_anonymous = db.Column(db.Boolean, default=False)
    is_flagged = db.Column(db.Boolean, default=False)
    quality_score = db.Column(db.Float, default=0.0)
    likes = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', backref='knowledge_posts')

    def to_dict(self):
        return {
            'id': self.id,
            'author': self.author.name if not self.is_anonymous else 'Anonymous',
            'author_id': self.author_id,
            'title': self.title,
            'content': self.content,
            'post_type': self.post_type,
            'faculty_code': self.faculty_code,
            'course_code': self.course_code,
            'course_name': self.course_name,
            'tags': [t.strip() for t in self.tags.split(',')] if self.tags else [],
            'is_anonymous': self.is_anonymous,
            'likes': self.likes,
            'views': self.views,
            'created_at': self.created_at.isoformat(),
            'quality_score': self.quality_score
        }

class KnowledgePostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('knowledge_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='_kpost_user_like_uc'),)

class KnowledgeAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('knowledge_post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    helpful_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', backref='knowledge_answers')

    def to_dict(self):
        return {
            'id': self.id,
            'author': self.author.name,
            'author_id': self.author_id,
            'content': self.content,
            'is_verified': self.is_verified,
            'helpful_count': self.helpful_count,
            'created_at': self.created_at.isoformat()
        }

class HelpfulAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('knowledge_answer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('answer_id', 'user_id', name='_answer_user_helpful_uc'),)

class UserFollow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('follower_id', 'following_id', name='_user_follow_uc'),)

class ContentReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(50))
    content_id = db.Column(db.Integer)
    content_type = db.Column(db.String(50))
    reason = db.Column(db.Text)
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Conversation(db.Model):
    """Conversation for direct messaging"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    is_group = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    participants = db.relationship('ConversationParticipant', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('DirectMessage', backref='conversation', lazy='dynamic', order_by='DirectMessage.created_at.desc()')

    def to_dict(self, current_user_id=None):
        last_message = self.messages.first()
        unread_count = 0
        if current_user_id:
            participant = ConversationParticipant.query.filter_by(
                conversation_id=self.id, user_id=current_user_id
            ).first()
            if participant:
                unread_count = DirectMessage.query.filter_by(
                    conversation_id=self.id
                ).filter(
                    DirectMessage.created_at > participant.last_read_at
                ).count()

        return {
            'id': self.id,
            'title': self.title or 'Untitled Conversation',
            'is_group': self.is_group,
            'created_by_id': self.created_by_id,
            'participant_count': self.participants.count(),
            'last_message': last_message.to_dict() if last_message else None,
            'unread_count': unread_count,
            'created_at': self.created_at.isoformat()
        }


class ConversationParticipant(db.Model):
    """Participants in a conversation"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_read_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint('conversation_id', 'user_id', name='_conversation_user_uc'),)

    user = db.relationship('User', backref='conversations')


class DirectMessage(db.Model):
    """Direct messages"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='text')
    file_url = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', backref='sent_messages')

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.name,
            'sender_avatar': self.sender.avatar_url or '',
            'content': self.content,
            'message_type': self.message_type,
            'file_url': self.file_url or '',
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }


class ActivityFeed(db.Model):
    """Activity feed entries"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    source_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    content = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    source_user = db.relationship('User', foreign_keys=[source_user_id], backref='activities_caused')


class StudyGroup(db.Model):
    """Study groups for collaborative learning"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=True)
    max_members = db.Column(db.Integer, default=10)
    is_public = db.Column(db.Boolean, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User', backref='created_study_groups')
    module = db.relationship('Module', backref='study_groups')
    members = db.relationship('StudyGroupMember', backref='group', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description or '',
            'module_id': self.module_id,
            'module_name': self.module.name if self.module else None,
            'max_members': self.max_members,
            'member_count': self.members.count(),
            'is_public': self.is_public,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat()
        }


class StudyGroupMember(db.Model):
    """Members of study groups"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('study_group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), default='member')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('group_id', 'user_id', name='_group_user_uc'),)

    user = db.relationship('User', backref='study_groups')

# ==================== AUTH HELPERS ====================

def generate_token(user_id, token_type='access'):
    if token_type == 'magic':
        expires = timedelta(hours=1)
        payload = {
            'user_id': user_id,
            'exp': datetime.now(timezone.utc) + expires,
            'iat': datetime.now(timezone.utc),
            'type': 'magic',
            'magic_id': str(uuid.uuid4())
        }
    else:
        expires = timedelta(minutes=60*24)
        payload = {
            'user_id': user_id,
            'exp': datetime.now(timezone.utc) + expires,
            'iat': datetime.now(timezone.utc),
            'type': 'access'
        }
    return jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')

def decode_token(token):
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
        return {'success': True, 'payload': payload}
    except jwt.ExpiredSignatureError:
        return {'success': False, 'error': 'Token expired'}
    except jwt.InvalidTokenError as e:
        return {'success': False, 'error': str(e)}

def get_current_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]
    result = decode_token(token)
    if result['success'] and result['payload'].get('type') == 'access':
        return User.query.get(result['payload']['user_id'])
    return None

# ==================== AUTH ROUTES ====================

@app.route('/auth/login', methods=['POST'])
def auth_login():
    """Magic link login - send link to email"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email required'}), 400

    # Find or create user
    user = User.query.filter_by(email=email).first()
    is_new_user = False
    if not user:
        user = User(
            email=email,
            name=data.get('name', email.split('@')[0]),
            role=data.get('role', 'student')
        )
        db.session.add(user)
        db.session.commit()
        is_new_user = True
        logger.info(f"New user created: {email}")

    # Generate magic link
    magic_token = generate_token(user.id, 'magic')
    frontend_url = os.environ.get('FRONTEND_URL', 'https://ur-academia.onrender.com')
    magic_link = f"{frontend_url}/auth/magic-login?token={magic_token}"

    # Send email notification
    email_sent = email_service.send_magic_link(email, magic_link, user.name)

    # Log the action
    log_audit('magic_link_sent', details={
        'email': email,
        'is_new_user': is_new_user,
        'email_sent': email_sent
    })

    # In development, still show link in logs
    if not email_sent or os.environ.get('FLASK_ENV') != 'production':
        logger.info(f"Magic Link for {email}: {magic_link}")

    return jsonify({
        'message': 'Login link sent to your email',
        'email': email,
        'debug_link': magic_link if not email_sent else None  # Only show in dev
    }), 200

@app.route('/auth/magic-login', methods=['GET'])
def magic_login():
    """Handle magic link click"""
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Invalid magic link'}), 400

    result = decode_token(token)
    if not result['success']:
        return jsonify({'error': result['error']}), 400

    if result['payload'].get('type') != 'magic':
        return jsonify({'error': 'Invalid token type'}), 400

    user = User.query.get(result['payload']['user_id'])
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 404

    # Generate access token
    access_token = generate_token(user.id, 'access')

    frontend_url = os.environ.get('FRONTEND_URL', 'https://ur-academia.onrender.com')
    return redirect(f"{frontend_url}/?token={access_token}")

@app.route('/auth/resend', methods=['POST'])
def resend_magic_link():
    """Resend magic link"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    magic_token = generate_token(user.id, 'magic')
    frontend_url = os.environ.get('FRONTEND_URL', 'https://ur-academia.onrender.com')
    magic_link = f"{frontend_url}/auth/magic-login?token={magic_token}"

    print(f"Resending magic link to {email}: {magic_link}")

    return jsonify({'message': 'Magic link resent'}), 200

@app.route('/auth/me', methods=['GET'])
def auth_me():
    """Get current user"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        }
    }), 200

@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    return jsonify({'message': 'Logged out'}), 200

# ==================== ADMIN LOGIN (Hardcoded) ====================

# Admin credentials - multiple emails, same password
ADMIN_EMAILS = [
    'admin@ur.ac.rw',
    'htuyishi@gmail.com',
]
ADMIN_PASSWORD = 'password123'

@app.route('/auth/admin-login', methods=['POST'])
def admin_login():
    """Admin login with email and password"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    # Check if email is in admin list and password matches
    if email not in ADMIN_EMAILS or password != ADMIN_PASSWORD:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Find or create admin user
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            name='System Administrator',
            role='admin'
        )
        db.session.add(user)
        db.session.commit()
    elif user.role != 'admin':
        user.role = 'admin'
        db.session.commit()

    # Generate access token
    access_token = generate_token(user.id, 'access')

    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        },
        'token': access_token
    }), 200

# ==================== API ROUTES ====================

@app.route('/api/colleges', methods=['GET'])
def get_colleges():
    colleges = College.query.filter_by(is_active=True).all()
    return jsonify({
        'colleges': [{
            'id': c.id,
            'code': c.code,
            'name': c.name,
            'description': c.description,
            'school_count': c.schools.count()
        } for c in colleges]
    }), 200

@app.route('/api/colleges/<int:college_id>', methods=['GET'])
def get_college(college_id):
    college = College.query.get_or_404(college_id)
    schools = School.query.filter_by(college_id=college.id, is_active=True).all()
    return jsonify({
        'college': {
            'id': college.id,
            'code': college.code,
            'name': college.name,
            'description': college.description
        },
        'schools': [{
            'id': s.id,
            'code': s.code,
            'name': s.name,
            'module_count': s.modules.count()
        } for s in schools]
    }), 200

@app.route('/api/schools', methods=['GET'])
def get_schools():
    try:
        college_id = request.args.get('college_id')
        query = School.query.filter_by(is_active=True)
        if college_id:
            query = query.filter_by(college_id=college_id)
        schools = query.all()

        school_list = []
        for s in schools:
            data = {
                'id': s.id,
                'code': s.code,
                'name': s.name,
                'college_id': s.college_id
            }
            # Safely access relationships to prevent 500 errors if DB is inconsistent
            try:
                data['college_name'] = s.college.name if s.college else 'Unknown'
                data['module_count'] = s.modules.count()
            except Exception:
                data['college_name'] = 'Unknown'
                data['module_count'] = 0
            school_list.append(data)

        return jsonify({'schools': school_list}), 200
    except Exception as e:
        logger.error(f"Error fetching schools: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/academic-years', methods=['GET'])
def get_academic_years():
    years = AcademicYear.query.order_by(AcademicYear.year_code.desc()).all()
    return jsonify({
        'academic_years': [{
            'id': y.id,
            'year_code': y.year_code,
            'name': y.name,
            'start_date': y.start_date.isoformat(),
            'end_date': y.end_date.isoformat(),
            'is_active': y.is_active,
            'is_completed': y.is_completed,
            'semester_count': y.semesters.count()
        } for y in years]
    }), 200

@app.route('/api/academic-years/<int:year_id>', methods=['GET'])
def get_academic_year(year_id):
    year = AcademicYear.query.get_or_404(year_id)
    semesters = Semester.query.filter_by(academic_year_id=year.id).all()
    return jsonify({
        'academic_year': {
            'id': year.id,
            'year_code': year.year_code,
            'name': year.name,
            'start_date': year.start_date.isoformat(),
            'end_date': year.end_date.isoformat()
        },
        'semesters': [{
            'id': s.id,
            'name': s.name,
            'code': s.code
        } for s in semesters]
    }), 200

@app.route('/api/modules', methods=['GET'])
def get_modules():
    semester_id = request.args.get('semester_id')
    school_id = request.args.get('school_id')
    program = request.args.get('program')
    year = request.args.get('year')
    search = request.args.get('search')

    query = Module.query.filter_by(is_active=True)

    if semester_id:
        query = query.filter_by(semester_id=semester_id)
    if school_id:
        query = query.filter_by(school_id=school_id)
    if program:
        query = query.filter_by(program=program)
    if year:
        query = query.filter_by(year_of_study=year)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Module.name.ilike(search_term)) |
            (Module.module_code.ilike(search_term))
        )

    modules = query.order_by(Module.name).limit(100).all()

    return jsonify({
        'modules': [{
            'id': m.id,
            'module_code': m.module_code,
            'name': m.name,
            'description': m.description,
            'school_id': m.school_id,
            'school_name': m.school.name if m.school else 'Unknown',
            'semester_id': m.semester_id,
            'semester_name': m.semester.name,
            'credits': m.credits,
            'lecturer_name': m.lecturer_name,
            'tags': [t.strip() for t in m.tags.split(',')] if m.tags else [],
            'student_count': len(m.students),
            'document_count': m.documents.count(),
            'is_enrollment_open': m.is_enrollment_open,
            'year_of_study': m.year_of_study,
            'created_at': m.created_at.isoformat() if m.created_at else None
        } for m in modules]
    }), 200

@app.route('/api/modules/<int:module_id>', methods=['GET'])
def get_module(module_id):
    module = Module.query.get_or_404(module_id)
    documents = module.documents.filter_by(is_published=True).all()

    return jsonify({
        'module': {
            'id': module.id,
            'module_code': module.module_code,
            'name': module.name,
            'description': module.description,
            'school_id': module.school_id,
            'school_name': module.school.name if module.school else 'Unknown',
            'college_id': module.school.college.id if module.school and module.school.college else None,
            'college_name': module.school.college.name if module.school and module.school.college else 'Unknown',
            'semester_id': module.semester_id,
            'semester_name': module.semester.name,
            'academic_year_id': module.semester.academic_year.id,
            'academic_year': module.semester.academic_year.name,
            'credits': module.credits,
            'lecturer_name': module.lecturer_name,
            'lecturer_email': module.lecturer_email,
            'tags': [t.strip() for t in module.tags.split(',')] if module.tags else [],
            'module_type': module.module_type,
            'max_students': module.max_students,
            'student_count': len(module.students),
            'is_enrollment_open': module.is_enrollment_open
        },
        'documents': [{
            'id': d.id,
            'title': d.title,
            'file_type': d.file_type,
            'file_size': d.file_size,
            'category': d.category,
            'download_count': d.download_count,
            'uploaded_at': d.created_at.isoformat()
        } for d in documents]
    }), 200

# ==================== ASSIGNMENT API ====================

@app.route('/api/assignments', methods=['GET'])
@limiter.limit("100/hour")
def get_assignments():
    """List assignments (filtered by module, published status)"""
    module_id = request.args.get('module_id')

    query = Assignment.query

    if module_id:
        query = query.filter_by(module_id=module_id)

    # Only show published assignments to students
    user = get_current_user()
    if user and user.role not in ['admin', 'instructor']:
        query = query.filter_by(is_published=True)

    assignments = query.order_by(Assignment.due_date).all()

    # Cache for public endpoints
    cache_key = f"assignments:{module_id or 'all'}:{user.id if user else 'anon'}"
    cached = get_cached_response(cache_key)
    if cached:
        return jsonify(cached), 200

    result = {
        'assignments': [{
            'id': a.id,
            'module_id': a.module_id,
            'module_name': a.module.name if a.module else 'Unknown',
            'title': a.title,
            'description': a.description,
            'due_date': a.due_date.isoformat(),
            'max_score': a.max_score,
            'weight': a.weight,
            'assignment_type': a.assignment_type,
            'is_published': a.is_published,
            'allow_late_submission': a.allow_late_submission,
            'submission_count': a.submissions.count(),
            'created_at': a.created_at.isoformat()
        } for a in assignments]
    }

    cache_api_response(cache_key, result, ttl=300)
    return jsonify(result), 200

@app.route('/api/assignments/<int:assignment_id>', methods=['GET'])
def get_assignment(assignment_id):
    """Get assignment details"""
    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if user has access
    user = get_current_user()
    if not assignment.is_published and (not user or user.role not in ['admin', 'instructor']):
        return jsonify({'error': 'Assignment not found'}), 404

    return jsonify({
        'assignment': {
            'id': assignment.id,
            'module_id': assignment.module_id,
            'module_name': assignment.module.name if assignment.module else 'Unknown',
            'title': assignment.title,
            'description': assignment.description,
            'instructions': assignment.instructions,
            'due_date': assignment.due_date.isoformat(),
            'max_score': assignment.max_score,
            'weight': assignment.weight,
            'assignment_type': assignment.assignment_type,
            'is_published': assignment.is_published,
            'allow_late_submission': assignment.allow_late_submission,
            'late_penalty_percent': assignment.late_penalty_percent,
            'created_at': assignment.created_at.isoformat()
        }
    }), 200

@app.route('/api/assignments', methods=['POST'])
@limiter.limit("50/hour")
def create_assignment():
    """Create a new assignment (admin/instructor only)"""
    user = get_current_user()
    if not user or user.role not in ['admin', 'instructor']:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    assignment = Assignment(
        module_id=data['module_id'],
        title=data['title'],
        description=data.get('description'),
        instructions=data.get('instructions'),
        due_date=datetime.fromisoformat(data['due_date']),
        max_score=data.get('max_score', 100),
        weight=data.get('weight', 1.0),
        assignment_type=data.get('assignment_type', 'assignment'),
        is_published=data.get('is_published', False),
        allow_late_submission=data.get('allow_late_submission', True),
        late_penalty_percent=data.get('late_penalty_percent', 10)
    )

    db.session.add(assignment)
    db.session.commit()

    # Notify enrolled students
    module = Module.query.get(data['module_id'])
    for student in module.students:
        if student.email:
            email_service.send_assignment_notification(
                student.email,
                assignment.title,
                module.name,
                assignment.due_date.strftime('%Y-%m-%d %H:%M')
            )

    log_audit('assignment_created', 'assignment', assignment.id, {
        'title': assignment.title,
        'module_id': assignment.module_id
    })

    invalidate_cache('assignments:*')

    return jsonify({
        'message': 'Assignment created successfully',
        'assignment': {
            'id': assignment.id,
            'title': assignment.title
        }
    }), 201

@app.route('/api/assignments/<int:assignment_id>/submit', methods=['POST'])
@limiter.limit("20/hour")
def submit_assignment(assignment_id):
    """Submit an assignment"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    assignment = Assignment.query.get_or_404(assignment_id)

    if not assignment.is_published:
        return jsonify({'error': 'Assignment not available'}), 403

    # Check if due date has passed
    is_late = datetime.utcnow() > assignment.due_date
    if is_late and not assignment.allow_late_submission:
        return jsonify({'error': 'Late submissions not allowed'}), 400

    data = request.get_json()

    # Check for existing submission
    existing = Submission.query.filter_by(
        assignment_id=assignment_id,
        student_id=user.id
    ).first()

    if existing:
        # Update existing submission
        existing.content = data.get('content', existing.content)
        existing.submitted_at = datetime.utcnow()
        existing.is_late = is_late
        existing.status = 'submitted'
        submission = existing
    else:
        # Create new submission
        submission = Submission(
            assignment_id=assignment_id,
            student_id=user.id,
            content=data.get('content'),
            status='submitted',
            is_late=is_late
        )
        db.session.add(submission)

    db.session.commit()

    log_audit('assignment_submitted', 'submission', submission.id, {
        'assignment_id': assignment_id,
        'is_late': is_late
    })

    invalidate_cache(f'submissions:{assignment_id}:*')

    return jsonify({
        'message': 'Assignment submitted successfully',
        'submission': {
            'id': submission.id,
            'status': submission.status,
            'submitted_at': submission.submitted_at.isoformat(),
            'is_late': submission.is_late
        }
    }), 200

@app.route('/api/submissions', methods=['GET'])
def get_my_submissions():
    """Get current user's submissions"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    submissions = Submission.query.filter_by(student_id=user.id).all()

    return jsonify({
        'submissions': [{
            'id': s.id,
            'assignment_id': s.assignment_id,
            'assignment_title': s.assignment.title,
            'module_name': s.assignment.module.name,
            'status': s.status,
            'score': s.score,
            'submitted_at': s.submitted_at.isoformat(),
            'is_late': s.is_late,
            'graded_at': s.graded_at.isoformat() if s.graded_at else None
        } for s in submissions]
    }), 200

@app.route('/api/submissions/<int:submission_id>', methods=['GET'])
def get_submission(submission_id):
    """Get submission details"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    submission = Submission.query.get_or_404(submission_id)

    # Check access
    if user.role not in ['admin', 'instructor'] and submission.student_id != user.id:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'submission': {
            'id': submission.id,
            'assignment_id': submission.assignment_id,
            'assignment_title': submission.assignment.title,
            'student_id': submission.student_id,
            'student_name': submission.student.name,
            'student_email': submission.student.email,
            'content': submission.content,
            'status': submission.status,
            'score': submission.score,
            'feedback': submission.feedback,
            'submitted_at': submission.submitted_at.isoformat(),
            'graded_at': submission.graded_at.isoformat() if submission.graded_at else None,
            'graded_by_name': submission.grader.name if submission.grader else None
        }
    }), 200

@app.route('/api/submissions/<int:submission_id>/grade', methods=['POST'])
def grade_submission(submission_id):
    """Grade a submission (instructor/admin only)"""
    user = get_current_user()
    if not user or user.role not in ['admin', 'instructor']:
        return jsonify({'error': 'Unauthorized'}), 403

    submission = Submission.query.get_or_404(submission_id)

    data = request.get_json()

    submission.score = data.get('score')
    submission.feedback = data.get('feedback')
    submission.graded_by = user.id
    submission.graded_at = datetime.utcnow()
    submission.status = 'graded'

    db.session.commit()

    log_audit('submission_graded', 'submission', submission.id, {
        'score': submission.score,
        'graded_by': user.id
    })

    return jsonify({
        'message': 'Submission graded successfully',
        'submission': {
            'id': submission.id,
            'score': submission.score,
            'status': submission.status
        }
    }), 200

# ==================== QUIZ API ====================

@app.route('/api/quizzes', methods=['GET'])
def get_quizzes():
    """List quizzes (filtered by module)"""
    module_id = request.args.get('module_id')

    query = Quiz.query

    if module_id:
        query = query.filter_by(module_id=module_id)

    user = get_current_user()
    if user and user.role not in ['admin', 'instructor']:
        query = query.filter_by(is_published=True)

    quizzes = query.order_by(Quiz.created_at.desc()).all()

    return jsonify({
        'quizzes': [{
            'id': q.id,
            'module_id': q.module_id,
            'module_name': q.module.name if q.module else 'Unknown',
            'title': q.title,
            'description': q.description,
            'quiz_type': q.quiz_type,
            'time_limit': q.time_limit,
            'max_attempts': q.max_attempts,
            'passing_score': q.passing_score,
            'question_count': q.questions.count(),
            'is_published': q.is_published,
            'available_from': q.available_from.isoformat() if q.available_from else None,
            'available_until': q.available_until.isoformat() if q.available_until else None
        } for q in quizzes]
    }), 200

@app.route('/api/quizzes/<int:quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    """Get quiz details with questions"""
    quiz = Quiz.query.get_or_404(quiz_id)

    user = get_current_user()
    if not quiz.is_published and (not user or user.role not in ['admin', 'instructor']):
        return jsonify({'error': 'Quiz not found'}), 404

    # Don't show correct answers to students before submission
    questions = quiz.questions.all()

    return jsonify({
        'quiz': {
            'id': quiz.id,
            'module_id': quiz.module_id,
            'title': quiz.title,
            'description': quiz.description,
            'quiz_type': quiz.quiz_type,
            'time_limit': quiz.time_limit,
            'max_attempts': quiz.max_attempts,
            'passing_score': quiz.passing_score,
            'shuffle_questions': quiz.shuffle_questions,
            'show_results': quiz.show_results,
            'questions': [{
                'id': q.id,
                'question_type': q.question_type,
                'question_text': q.question_text,
                'points': q.points,
                'order': q.order,
                'options': None if user and user.role == 'student' else [{
                    'id': o.id,
                    'option_text': o.option_text,
                    'order': o.order
                } for o in q.options.order_by('option.order').all()]
            } for q in questions]
        }
    }), 200

@app.route('/api/quizzes', methods=['POST'])
@limiter.limit("30/hour")
def create_quiz():
    """Create a new quiz"""
    user = get_current_user()
    if not user or user.role not in ['admin', 'instructor']:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    quiz = Quiz(
        module_id=data['module_id'],
        title=data['title'],
        description=data.get('description'),
        quiz_type=data.get('quiz_type', 'quiz'),
        time_limit=data.get('time_limit'),
        max_attempts=data.get('max_attempts', 1),
        passing_score=data.get('passing_score', 60.0),
        shuffle_questions=data.get('shuffle_questions', True),
        show_results=data.get('show_results', True),
        is_published=data.get('is_published', False),
        available_from=datetime.fromisoformat(data['available_from']) if data.get('available_from') else None,
        available_until=datetime.fromisoformat(data['available_until']) if data.get('available_until') else None
    )

    db.session.add(quiz)
    db.session.commit()

    # Add questions if provided
    if data.get('questions'):
        for i, q_data in enumerate(data['questions']):
            question = Question(
                quiz_id=quiz.id,
                question_type=q_data['question_type'],
                question_text=q_data['question_text'],
                explanation=q_data.get('explanation'),
                points=q_data.get('points', 1.0),
                order=i,
                is_required=q_data.get('is_required', True)
            )
            db.session.add(question)
            db.session.flush()

            # Add options for multiple choice
            if q_data.get('options'):
                for j, opt_data in enumerate(q_data['options']):
                    option = QuestionOption(
                        question_id=question.id,
                        option_text=opt_data['option_text'],
                        is_correct=opt_data.get('is_correct', False),
                        order=j
                    )
                    db.session.add(option)

    db.session.commit()

    log_audit('quiz_created', 'quiz', quiz.id, {'title': quiz.title})
    invalidate_cache('quizzes:*')

    return jsonify({
        'message': 'Quiz created successfully',
        'quiz': {'id': quiz.id, 'title': quiz.title}
    }), 201

@app.route('/api/quizzes/<int:quiz_id>/start', methods=['POST'])
def start_quiz(quiz_id):
    """Start a quiz attempt"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    quiz = Quiz.query.get_or_404(quiz_id)

    if not quiz.is_published:
        return jsonify({'error': 'Quiz not available'}), 403

    # Check attempt count
    attempts = QuizSubmission.query.filter_by(
        quiz_id=quiz_id,
        student_id=user.id
    ).count()

    if attempts >= quiz.max_attempts:
        return jsonify({'error': 'Maximum attempts reached'}), 400

    # Create submission
    submission = QuizSubmission(
        quiz_id=quiz_id,
        student_id=user.id,
        attempt_number=attempts + 1
    )
    db.session.add(submission)
    db.session.commit()

    return jsonify({
        'message': 'Quiz started',
        'submission': {
            'id': submission.id,
            'attempt_number': submission.attempt_number,
            'started_at': submission.started_at.isoformat()
        }
    }), 200

@app.route('/api/quizzes/<int:quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    """Submit quiz answers"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json()

    submission_id = data.get('submission_id')
    answers = data.get('answers', [])

    submission = QuizSubmission.query.get_or_404(submission_id)

    if submission.student_id != user.id:
        return jsonify({'error': 'Access denied'}), 403

    if submission.submitted_at:
        return jsonify({'error': 'Already submitted'}), 400

    # Calculate score
    total_points = 0
    earned_points = 0

    for ans_data in answers:
        question = Question.query.get(ans_data['question_id'])
        if not question:
            continue

        total_points += question.points

        is_correct = False
        points_earned = 0

        if question.question_type == 'multiple_choice':
            # Get correct option
            correct_option = QuestionOption.query.filter_by(
                question_id=question.id,
                is_correct=True
            ).first()

            if correct_option and str(correct_option.id) in str(ans_data.get('selected_options', [])):
                is_correct = True
                points_earned = question.points
        elif question.question_type == 'true_false':
            correct_option = QuestionOption.query.filter_by(
                question_id=question.id,
                is_correct=True
            ).first()

            if correct_option and str(correct_option.id) == str(ans_data.get('selected_options', [])):
                is_correct = True
                points_earned = question.points
        elif question.question_type == 'short_answer':
            # Manual grading required - auto-fail for now
            points_earned = 0

        earned_points += points_earned

        # Save answer
        answer = QuizAnswer(
            submission_id=submission.id,
            question_id=question.id,
            answer_text=ans_data.get('answer_text'),
            selected_options=json.dumps(ans_data.get('selected_options', [])),
            is_correct=is_correct,
            points_earned=points_earned
        )
        db.session.add(answer)

    # Calculate final score
    percentage = (earned_points / total_points * 100) if total_points > 0 else 0
    passed = percentage >= quiz.passing_score

    submission.score = earned_points
    submission.max_score = total_points
    submission.percentage = percentage
    submission.passed = passed
    submission.submitted_at = datetime.utcnow()
    submission.time_spent_seconds = int((datetime.utcnow() - submission.started_at).total_seconds())

    db.session.commit()

    log_audit('quiz_submitted', 'quiz_submission', submission.id, {
        'score': earned_points,
        'percentage': percentage,
        'passed': passed
    })

    return jsonify({
        'message': 'Quiz submitted successfully',
        'result': {
            'score': submission.score,
            'max_score': submission.max_score,
            'percentage': round(submission.percentage, 2),
            'passed': submission.passed,
            'time_spent': submission.time_spent_seconds
        }
    }), 200

@app.route('/api/quizzes/<int:quiz_id>/attempts', methods=['GET'])
def get_quiz_attempts(quiz_id):
    """Get student's quiz attempts"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    attempts = QuizSubmission.query.filter_by(
        quiz_id=quiz_id,
        student_id=user.id
    ).order_by(QuizSubmission.attempt_number).all()

    return jsonify({
        'attempts': [{
            'id': a.id,
            'attempt_number': a.attempt_number,
            'score': a.score,
            'max_score': a.max_score,
            'percentage': a.percentage,
            'passed': a.passed,
            'started_at': a.started_at.isoformat(),
            'submitted_at': a.submitted_at.isoformat() if a.submitted_at else None,
            'time_spent_seconds': a.time_spent_seconds
        } for a in attempts]
    }), 200

# ==================== FORUM API ====================

@app.route('/api/forums', methods=['GET'])
def get_forums():
    """List forums"""
    module_id = request.args.get('module_id')

    query = Forum.query.filter_by(is_published=True)

    if module_id:
        query = query.filter_by(module_id=module_id)

    forums = query.all()

    return jsonify({
        'forums': [{
            'id': f.id,
            'module_id': f.module_id,
            'module_name': f.module.name if f.module else 'Unknown',
            'title': f.title,
            'description': f.description,
            'post_count': f.posts.count(),
            'created_at': f.created_at.isoformat()
        } for f in forums]
    }), 200

@app.route('/api/forums/<int:forum_id>', methods=['GET'])
def get_forum(forum_id):
    """Get forum with posts"""
    forum = Forum.query.get_or_404(forum_id)

    posts = forum.posts.filter_by(is_published=True).order_by(
        ForumPost.is_pinned.desc(),
        ForumPost.created_at.desc()
    ).limit(50).all()

    return jsonify({
        'forum': {
            'id': forum.id,
            'module_id': forum.module_id,
            'title': forum.title,
            'description': forum.description,
            'posts': [{
                'id': p.id,
                'title': p.title,
                'author_name': p.author.name,
                'author_id': p.author_id,
                'view_count': p.view_count,
                'reply_count': p.reply_count,
                'is_pinned': p.is_pinned,
                'created_at': p.created_at.isoformat(),
                'updated_at': p.updated_at.isoformat()
            } for p in posts]
        }
    }), 200

@app.route('/api/forums/<int:forum_id>/posts', methods=['POST'])
@limiter.limit("20/hour")
def create_forum_post(forum_id):
    """Create a new forum post"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    forum = Forum.query.get_or_404(forum_id)

    data = request.get_json()

    post = ForumPost(
        forum_id=forum_id,
        author_id=user.id,
        title=data['title'],
        content=data['content']
    )

    db.session.add(post)
    db.session.commit()

    log_audit('forum_post_created', 'forum_post', post.id, {
        'forum_id': forum_id,
        'title': post.title
    })

    return jsonify({
        'message': 'Post created successfully',
        'post': {
            'id': post.id,
            'title': post.title,
            'created_at': post.created_at.isoformat()
        }
    }), 201

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get post with comments"""
    post = ForumPost.query.get_or_404(post_id)

    # Increment view count
    post.view_count += 1
    db.session.commit()

    comments = post.comments.filter_by(is_approved=True).all()

    return jsonify({
        'post': {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'author_id': post.author_id,
            'author_name': post.author.name,
            'is_pinned': post.is_pinned,
            'is_locked': post.is_locked,
            'view_count': post.view_count,
            'created_at': post.created_at.isoformat(),
            'comments': [{
                'id': c.id,
                'content': c.content,
                'author_name': c.author.name,
                'parent_id': c.parent_id,
                'created_at': c.created_at.isoformat()
            } for c in comments]
        }
    }), 200

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@limiter.limit("30/hour")
def create_comment(post_id):
    """Add a comment to a post"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    post = ForumPost.query.get_or_404(post_id)

    if post.is_locked:
        return jsonify({'error': 'Post is locked'}), 400

    data = request.get_json()

    comment = ForumComment(
        post_id=post_id,
        author_id=user.id,
        parent_id=data.get('parent_id'),
        content=data['content']
    )

    db.session.add(comment)

    # Update reply count
    post.reply_count += 1

    db.session.commit()

    # Notify post author
    if post.author_id != user.id:
        notification = Notification(
            user_id=post.author_id,
            title='New reply to your post',
            message=f'{user.name} replied to "{post.title}"',
            notification_type='info',
            link=f'/forum/post/{post_id}'
        )
        db.session.add(notification)
        db.session.commit()

    return jsonify({
        'message': 'Comment added successfully',
        'comment': {
            'id': comment.id,
            'created_at': comment.created_at.isoformat()
        }
    }), 201

# ==================== NOTIFICATIONS API ====================

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get user notifications"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    notifications = Notification.query.filter_by(
        user_id=user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()

    unread_count = Notification.query.filter_by(
        user_id=user.id,
        is_read=False
    ).count()

    return jsonify({
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'is_read': n.is_read,
            'link': n.link,
            'created_at': n.created_at.isoformat()
        } for n in notifications],
        'unread_count': unread_count
    }), 200

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark notification as read"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=user.id
    ).first_or_404()

    notification.is_read = True
    db.session.commit()

    return jsonify({'message': 'Marked as read'}), 200

@app.route('/api/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    """Mark all notifications as read"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    Notification.query.filter_by(
        user_id=user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()

    return jsonify({'message': 'All notifications marked as read'}), 200

# ==================== GRADE BOOK API ====================

@app.route('/api/grades', methods=['GET'])
def get_my_grades():
    """Get student's grades"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    grades = Grade.query.filter_by(
        student_id=user.id
    ).order_by(Grade.created_at.desc()).all()

    # Calculate GPA
    completed_courses = [g for g in grades if g.is_completed and g.gpa_points]
    total_gpa = sum(g.gpa_points * g.credits_earned for g in completed_courses)
    total_credits = sum(g.credits_earned for g in completed_courses)
    gpa = round(total_gpa / total_credits, 2) if total_credits > 0 else 0

    return jsonify({
        'grades': [{
            'id': g.id,
            'module_id': g.module_id,
            'module_code': g.module.module_code,
            'module_name': g.module.name if g.module else 'Unknown',
            'assignment_score': g.assignment_score,
            'quiz_score': g.quiz_score,
            'exam_score': g.exam_score,
            'total_score': g.total_score,
            'grade_letter': g.grade_letter,
            'credits_earned': g.credits_earned,
            'is_completed': g.is_completed,
            'semester': g.semester.name if g.semester else None
        } for g in grades],
        'gpa': gpa,
        'total_credits': total_credits
    }), 200

@app.route('/api/grades/module/<int:module_id>', methods=['GET'])
def get_module_grades(module_id):
    """Get grades for a specific module (instructor/admin)"""
    user = get_current_user()
    if not user or user.role not in ['admin', 'instructor']:
        return jsonify({'error': 'Unauthorized'}), 403

    grades = Grade.query.filter_by(module_id=module_id).all()

    return jsonify({
        'grades': [{
            'id': g.id,
            'student_id': g.student_id,
            'student_name': g.student.name,
            'student_email': g.student.email,
            'total_score': g.total_score,
            'grade_letter': g.grade_letter,
            'is_completed': g.is_completed
        } for g in grades]
    }), 200

@app.route('/api/grades', methods=['POST'])
def update_grade():
    """Update a student's grade (instructor/admin)"""
    user = get_current_user()
    if not user or user.role not in ['admin', 'instructor']:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    grade = Grade.query.filter_by(
        student_id=data['student_id'],
        module_id=data['module_id']
    ).first()

    if not grade:
        grade = Grade(
            student_id=data['student_id'],
            module_id=data['module_id'],
            assignment_score=data.get('assignment_score', 0),
            quiz_score=data.get('quiz_score', 0),
            exam_score=data.get('exam_score', 0),
            credits_earned=data.get('credits_earned', 0),
            semester_id=data.get('semester_id')
        )
        db.session.add(grade)
    else:
        grade.assignment_score = data.get('assignment_score', grade.assignment_score)
        grade.quiz_score = data.get('quiz_score', grade.quiz_score)
        grade.exam_score = data.get('exam_score', grade.exam_score)
        grade.credits_earned = data.get('credits_earned', grade.credits_earned)
        grade.semester_id = data.get('semester_id', grade.semester_id)

    # Calculate total score and grade letter
    grade.total_score = (grade.assignment_score or 0) + (grade.quiz_score or 0) + (grade.exam_score or 0)

    # Grade letter calculation
    if grade.total_score >= 90:
        grade.grade_letter = 'A'
        grade.gpa_points = 4.0
    elif grade.total_score >= 80:
        grade.grade_letter = 'B'
        grade.gpa_points = 3.0
    elif grade.total_score >= 70:
        grade.grade_letter = 'C'
        grade.gpa_points = 2.0
    elif grade.total_score >= 60:
        grade.grade_letter = 'D'
        grade.gpa_points = 1.0
    else:
        grade.grade_letter = 'F'
        grade.gpa_points = 0.0

    db.session.commit()

    # Notify student
    notification = Notification(
        user_id=data['student_id'],
        title='Grade Posted',
        message=f'Your grade for {grade.module.name} has been posted.',
        notification_type='grade',
        link=f'/grades'
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({
        'message': 'Grade updated successfully',
        'grade': {
            'id': grade.id,
            'total_score': grade.total_score,
            'grade_letter': grade.grade_letter
        }
    }), 200

@app.route('/api/grades/transcript', methods=['GET'])
def get_transcript():
    """Generate student transcript"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    grades = Grade.query.filter_by(
        student_id=user.id,
        is_completed=True
    ).all()

    # Calculate cumulative GPA
    total_gpa = sum(g.gpa_points * g.credits_earned for g in grades)
    total_credits = sum(g.credits_earned for g in grades)
    cumulative_gpa = round(total_gpa / total_credits, 2) if total_credits > 0 else 0

    transcript = {
        'student': {
            'name': user.name,
            'email': user.email,
            'id': user.id
        },
        'summary': {
            'total_courses': len(grades),
            'total_credits': total_credits,
            'cumulative_gpa': cumulative_gpa
        },
        'courses': [{
            'module_code': g.module.module_code,
            'module_name': g.module.name if g.module else 'Unknown',
            'credits': g.credits_earned,
            'score': g.total_score,
            'grade': g.grade_letter,
            'gpa_points': g.gpa_points,
            'semester': g.semester.name if g.semester else 'N/A'
        } for g in grades]
    }

    return jsonify(transcript), 200

# ==================== GAMIFICATION API ====================

@app.route('/api/gamification/badges', methods=['GET'])
def get_badges():
    """List all available badges"""
    badges = Badge.query.filter_by(is_active=True).all()

    return jsonify({
        'badges': [{
            'id': b.id,
            'name': b.name,
            'description': b.description,
            'icon': b.icon,
            'category': b.category,
            'points_reward': b.points_reward,
            'rarity': b.rarity,
            'requirement': {
                'type': b.requirement_type,
                'value': b.requirement_value
            }
        } for b in badges]
    }), 200

@app.route('/api/gamification/my-badges', methods=['GET'])
def get_my_badges():
    """Get user's earned badges"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    user_badges = UserBadge.query.filter_by(user_id=user.id).all()

    # Calculate progress for each badge
    badges = Badge.query.filter_by(is_active=True).all()
    badge_progress = []

    for badge in badges:
        user_badge = next((ub for ub in user_badges if ub.badge_id == badge.id), None)

        if user_badge:
            badge_progress.append({
                'badge': {
                    'id': badge.id,
                    'name': badge.name,
                    'icon': badge.icon,
                    'category': badge.category,
                    'rarity': badge.rarity
                },
                'earned_at': user_badge.earned_at.isoformat(),
                'progress': user_badge.progress,
                'is_completed': user_badge.is_completed
            })
        else:
            # Calculate progress
            progress = 0
            if badge.requirement_type == 'courses_completed':
                progress = len([g for g in user.grades if g.is_completed])
            elif badge.requirement_type == 'perfect_quiz':
                perfect_quizzes = QuizSubmission.query.filter_by(
                    student_id=user.id, passed=True
                ).filter(QuizSubmission.percentage >= 100).count()
                progress = perfect_quizzes
            elif badge.requirement_type == 'forum_posts':
                progress = ForumPost.query.filter_by(author_id=user.id).count()

            badge_progress.append({
                'badge': {
                    'id': badge.id,
                    'name': badge.name,
                    'icon': badge.icon,
                    'category': badge.category,
                    'rarity': badge.rarity
                },
                'progress': progress,
                'required': badge.requirement_value,
                'is_completed': False
            })

    return jsonify({'badges': badge_progress}), 200

@app.route('/api/gamification/points', methods=['GET'])
def get_points():
    """Get user's points summary"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    transactions = PointTransaction.query.filter_by(
        user_id=user.id
    ).order_by(PointTransaction.created_at.desc()).limit(50).all()

    total_earned = sum(t.points for t in transactions if t.points > 0)
    total_spent = abs(sum(t.points for t in transactions if t.points < 0))
    balance = total_earned - total_spent

    return jsonify({
        'balance': balance,
        'total_earned': total_earned,
        'total_spent': total_spent,
        'transactions': [{
            'id': t.id,
            'points': t.points,
            'type': t.transaction_type,
            'description': t.description,
            'created_at': t.created_at.isoformat()
        } for t in transactions]
    }), 200

@app.route('/api/gamification/streaks', methods=['GET'])
def get_streaks():
    """Get user's streaks"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    streaks = Streak.query.filter_by(user_id=user.id).all()

    return jsonify({
        'streaks': [{
            'id': s.id,
            'type': s.streak_type,
            'current_streak': s.current_streak,
            'longest_streak': s.longest_streak,
            'last_activity': s.last_activity_date.isoformat() if s.last_activity_date else None
        } for s in streaks]
    }), 200

@app.route('/api/gamification/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard"""
    leaderboard_type = request.args.get('type', 'overall')
    limit = int(request.args.get('limit', 10))

    entries = Leaderboard.query.filter_by(
        leaderboard_type=leaderboard_type
    ).order_by(Leaderboard.score.desc()).limit(limit).all()

    return jsonify({
        'leaderboard': [{
            'rank': i + 1,
            'user_id': e.user_id,
            'user_name': e.user.name,
            'score': e.score
        } for i, e in enumerate(entries)]
    }), 200

@app.route('/api/gamification/award-points', methods=['POST'])
def award_points():
    """Award points to a user (admin/instructor)"""
    user = get_current_user()
    if not user or user.role not in ['admin', 'instructor']:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    transaction = PointTransaction(
        user_id=data['user_id'],
        points=data['points'],
        transaction_type=data.get('type', 'bonus'),
        source='manual_award',
        description=data.get('description', 'Manual point award')
    )
    db.session.add(transaction)
    db.session.commit()

    return jsonify({'message': 'Points awarded successfully'}), 200

# ==================== ANALYTICS API ====================

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_analytics_dashboard():
    """Get student analytics dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    # Quiz performance
    quiz_submissions = QuizSubmission.query.filter_by(student_id=user.id).all()
    avg_quiz_score = sum(s.percentage or 0 for s in quiz_submissions) / len(quiz_submissions) if quiz_submissions else 0
    quizzes_passed = len([s for s in quiz_submissions if s.passed])

    # Study time
    study_sessions = StudySession.query.filter_by(user_id=user.id).all()
    total_study_time = sum(s.duration_seconds or 0 for s in study_sessions)

    # Assignments
    submissions = Submission.query.filter_by(student_id=user.id).all()
    assignments_submitted = len(submissions)
    assignments_graded = len([s for s in submissions if s.status == 'graded'])

    # Forum participation
    posts = ForumPost.query.filter_by(author_id=user.id).count()
    comments = ForumComment.query.filter_by(author_id=user.id).count()

    # Points
    points = PointTransaction.query.filter_by(user_id=user.id).all()
    total_points = sum(p.points for p in points)

    # Badges
    badges_earned = UserBadge.query.filter_by(user_id=user.id).count()

    return jsonify({
        'dashboard': {
            'quiz_performance': {
                'total_quizzes': len(quiz_submissions),
                'quizzes_passed': quizzes_passed,
                'average_score': round(avg_quiz_score, 2)
            },
            'study_time': {
                'total_hours': round(total_study_time / 3600, 2),
                'sessions': len(study_sessions)
            },
            'assignments': {
                'submitted': assignments_submitted,
                'graded': assignments_graded
            },
            'community': {
                'posts': posts,
                'comments': comments,
                'total_contributions': posts + comments
            },
            'gamification': {
                'total_points': total_points,
                'badges_earned': badges_earned
            }
        }
    }), 200

@app.route('/api/analytics/track-event', methods=['POST'])
def track_event():
    """Track an analytics event"""
    user = get_current_user()
    data = request.get_json()

    event = AnalyticsEvent(
        user_id=user.id if user else None,
        event_type=data.get('event_type'),
        event_data=json.dumps(data.get('event_data')),
        session_id=data.get('session_id'),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({'message': 'Event tracked'}), 200

@app.route('/api/analytics/study-sessions', methods=['GET'])
def get_study_sessions():
    """Get user's study sessions"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    sessions = StudySession.query.filter_by(
        user_id=user.id
    ).order_by(StudySession.start_time.desc()).limit(50).all()

    return jsonify({
        'sessions': [{
            'id': s.id,
            'module_id': s.module_id,
            'module_name': s.module.name if s.module else 'Unknown',
            'start_time': s.start_time.isoformat(),
            'end_time': s.end_time.isoformat() if s.end_time else None,
            'duration_seconds': s.duration_seconds,
            'duration_formatted': f"{s.duration_seconds // 60}m" if s.duration_seconds else None,
            'pages_viewed': s.pages_viewed,
            'resources_accessed': s.resources_accessed
        } for s in sessions]
    }), 200

@app.route('/api/analytics/study-sessions/start', methods=['POST'])
def start_study_session():
    """Start a study session"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()

    session = StudySession(
        user_id=user.id,
        module_id=data.get('module_id'),
        start_time=datetime.utcnow()
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        'message': 'Study session started',
        'session_id': session.id
    }), 201

@app.route('/api/analytics/study-sessions/<int:session_id>/end', methods=['POST'])
def end_study_session(session_id):
    """End a study session"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    session = StudySession.query.filter_by(
        id=session_id,
        user_id=user.id
    ).first_or_404()

    session.end_time = datetime.utcnow()
    session.duration_seconds = int((session.end_time - session.start_time).total_seconds())

    data = request.get_json()
    if data:
        session.pages_viewed = data.get('pages_viewed', 0)
        session.resources_accessed = data.get('resources_accessed', 0)

    db.session.commit()

    # Update streak
    streak = Streak.query.filter_by(
        user_id=user.id,
        streak_type='study'
    ).first()

    if not streak:
        streak = Streak(
            user_id=user.id,
            streak_type='study',
            current_streak=1,
            longest_streak=1,
            last_activity_date=datetime.utcnow().date()
        )
        db.session.add(streak)
    else:
        today = datetime.utcnow().date()
        if streak.last_activity_date == today:
            pass  # Already logged today
        elif streak.last_activity_date == today - timedelta(days=1):
            streak.current_streak += 1
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
            streak.last_activity_date = today
        else:
            streak.current_streak = 1
            streak.last_activity_date = today

    db.session.commit()

    return jsonify({
        'message': 'Study session ended',
        'duration': session.duration_seconds
    }), 200

@app.route('/api/analytics/performance/module/<int:module_id>', methods=['GET'])
def get_module_performance(module_id):
    """Get performance metrics for a module"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    # Quiz scores for this module
    module = Module.query.get_or_404(module_id)
    quizzes = Quiz.query.filter_by(module_id=module_id).all()

    quiz_scores = []
    for quiz in quizzes:
        submission = QuizSubmission.query.filter_by(
            quiz_id=quiz.id,
            student_id=user.id
        ).order_by(QuizSubmission.submitted_at.desc()).first()

        if submission:
            quiz_scores.append({
                'quiz_id': quiz.id,
                'quiz_title': quiz.title,
                'score': submission.percentage,
                'passed': submission.passed,
                'submitted_at': submission.submitted_at.isoformat()
            })

    # Assignments for this module
    assignments = Assignment.query.filter_by(module_id=module_id).all()
    assignment_scores = []

    for assignment in assignments:
        submission = Submission.query.filter_by(
            assignment_id=assignment.id,
            student_id=user.id
        ).first()

        if submission:
            assignment_scores.append({
                'assignment_id': assignment.id,
                'assignment_title': assignment.title,
                'score': submission.score,
                'max_score': assignment.max_score,
                'graded': submission.status == 'graded'
            })

    return jsonify({
        'module': {
            'id': module.id,
            'code': module.module_code,
            'name': module.name
        },
        'quizzes': quiz_scores,
        'assignments': assignment_scores,
        'average_quiz_score': sum(q['score'] or 0 for q in quiz_scores) / len(quiz_scores) if quiz_scores else 0,
        'completed_assignments': len([a for a in assignment_scores if a['graded']])
    }), 200

@app.route('/api/admin/analytics/overview', methods=['GET'])
def get_admin_analytics():
    """Get platform-wide analytics (admin only)"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    # User stats
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()

    # Module stats
    total_modules = Module.query.count()

    # Quiz stats
    total_quizzes = Quiz.query.count()
    total_submissions = QuizSubmission.query.count()

    # Forum stats
    total_posts = ForumPost.query.count()
    total_comments = ForumComment.query.count()

    # Engagement
    study_sessions = StudySession.query.all()
    total_study_hours = sum(s.duration_seconds or 0 for s in study_sessions) / 3600

    return jsonify({
        'overview': {
            'users': {
                'total': total_users,
                'active': active_users
            },
            'modules': {
                'total': total_modules
            },
            'quizzes': {
                'total': total_quizzes,
                'submissions': total_submissions
            },
            'forums': {
                'posts': total_posts,
                'comments': total_comments
            },
            'engagement': {
                'total_study_hours': round(total_study_hours, 2)
            }
        }
    }), 200

@app.route('/api/enrolled', methods=['GET'])
def get_enrolled_modules():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    enrolled = []
    for m in user.modules:
        enrolled.append({
            'id': m.id,
            'module_code': m.module_code,
            'name': m.name,
            'school_name': m.school.name if m.school else 'Unknown',
            'college_name': m.school.college.name if m.school and m.school.college else 'Unknown',
            'semester': m.semester.name,
            'academic_year': m.semester.academic_year.name,
            'document_count': m.documents.count(),
            'student_count': len(m.students)
        })

    return jsonify({'modules': enrolled}), 200

@app.route('/api/available', methods=['GET'])
def get_available_modules():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    # Get modules where enrollment is open
    open_modules = Module.query.filter_by(
        is_active=True,
        is_enrollment_open=True
    ).all()

    enrolled_ids = [m.id for m in user.modules]
    available = [m for m in open_modules if m.id not in enrolled_ids]

    return jsonify({
        'modules': [{
            'id': m.id,
            'module_code': m.module_code,
            'name': m.name,
            'description': m.description,
            'school_name': m.school.name if m.school else 'Unknown',
            'college_name': m.school.college.name if m.school and m.school.college else 'Unknown',
            'credits': m.credits,
            'lecturer_name': m.lecturer_name,
            'tags': [t.strip() for t in m.tags.split(',')] if m.tags else [],
            'spots_left': m.max_students - len(m.students)
        } for m in available]
    }), 200

@app.route('/api/enroll/<int:module_id>', methods=['POST'])
def enroll_in_module(module_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    module = Module.query.get_or_404(module_id)

    if user in module.students:
        return jsonify({'error': 'Already enrolled'}), 400

    if not module.is_enrollment_open:
        return jsonify({'error': 'Enrollment not open'}), 400

    if len(module.students) >= module.max_students:
        return jsonify({'error': 'Module is full'}), 400

    module.students.append(user)
    db.session.commit()

    return jsonify({'message': 'Enrolled successfully'}), 200

@app.route('/api/browse/colleges', methods=['GET'])
def browse_colleges():
    """Full hierarchy browse"""
    colleges = College.query.filter_by(is_active=True).all()
    result = []

    for college in colleges:
        college_data = {
            'id': college.id,
            'code': college.code,
            'name': college.name,
            'schools': []
        }

        for school in college.schools.filter_by(is_active=True).all():
            school_data = {
                'id': school.id,
                'code': school.code,
                'name': school.name,
                'modules_by_year': {}
            }

            for module in school.modules.filter_by(is_active=True).all():
                year_name = module.semester.academic_year.name
                semester_name = module.semester.name
                key = f"{year_name} - {semester_name}"

                if key not in school_data['modules_by_year']:
                    school_data['modules_by_year'][key] = {
                        'academic_year': year_name,
                        'semester': semester_name,
                        'modules': []
                    }

                school_data['modules_by_year'][key]['modules'].append({
                    'id': module.id,
                    'module_code': module.module_code,
                    'name': module.name,
                    'credits': module.credits,
                    'student_count': len(module.students)
                })

            school_data['modules_by_year'] = list(school_data['modules_by_year'].values())
            college_data['schools'].append(school_data)

        result.append(college_data)

    return jsonify({'structure': result}), 200

# ==================== SOCIAL NETWORK API ====================

@app.route('/api/social/posts', methods=['GET'])
def get_social_posts():
    """Get all social posts (feed)"""
    posts = SocialPost.query.order_by(SocialPost.created_at.desc()).limit(50).all()
    return jsonify({
        'posts': [p.to_dict() for p in posts],
        'total': len(posts)
    })

@app.route('/api/social/posts', methods=['POST'])
def create_social_post():
    """Create a new social post with @mention support"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(user_data.get('user_id'))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        post = SocialPost(
            user_id=user.id,
            content=data.get('content', ''),
            post_type=data.get('post_type', 'general'),
            resource_url=data.get('resource_url', None)
        )
        db.session.add(post)
        db.session.commit()

        # Process @mentions
        process_mentions(data.get('content', ''), post.id, user.id, user.id)

        # Create activity feed entry for followers
        following_users = SocialFollow.query.filter_by(followed_id=user.id).all()
        for follow in following_users:
            activity = ActivityFeed(
                user_id=follow.follower_id,
                activity_type='post',
                source_user_id=user.id,
                entity_type='post',
                entity_id=post.id,
                content=f"{user.name} created a new post",
                link=f"/public#post-{post.id}"
            )
            db.session.add(activity)
        db.session.commit()

        # Award points for social engagement
        db.session.add(PointTransaction(user_id=user.id, points=10, transaction_type='social_post', description='Created a new post'))
        db.session.commit()

        return jsonify({'post': post.to_dict(), 'message': 'Post created successfully'}), 201
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/posts/<int:post_id>', methods=['DELETE'])
def delete_social_post(post_id):
    """Deletes a social post"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(user_data.get('user_id'))
        post = SocialPost.query.get(post_id)

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Only post author or admin can delete
        if post.user_id != user.id and user.role != 'admin':
            return jsonify({'error': 'Permission denied'}), 403

        # Delete associated likes and comments first
        SocialLike.query.filter_by(post_id=post.id).delete()
        SocialComment.query.filter_by(post_id=post.id).delete()

        db.session.delete(post)
        db.session.commit()

        return jsonify({'message': 'Post deleted successfully'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/posts/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    """Toggle like on a post"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(user_data.get('user_id'))
        post = SocialPost.query.get(post_id)

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        existing_like = SocialLike.query.filter_by(post_id=post.id, user_id=user.id).first()

        if existing_like:
            db.session.delete(existing_like)
            post.likes_count = max(0, post.likes_count - 1)
            liked = False
        else:
            new_like = SocialLike(post_id=post.id, user_id=user.id)
            db.session.add(new_like)
            post.likes_count = post.likes_count + 1
            liked = True

            # Award points to post author
            db.session.add(PointTransaction(user_id=post.user_id, points=2, transaction_type='like_received', description='Post received a like'))

        db.session.commit()

        return jsonify({'liked': liked, 'likes_count': post.likes_count})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    """Get comments for a post"""
    comments = SocialComment.query.filter_by(post_id=post_id, parent_id=None).order_by(SocialComment.created_at.asc()).all()
    return jsonify({'comments': [c.to_dict() for c in comments]})

@app.route('/api/social/posts/<int:post_id>/comments', methods=['POST'])
def create_social_comment(post_id):
    """Create a comment on a post with @mention support"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(user_data.get('user_id'))
        post = SocialPost.query.get(post_id)

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        comment = SocialComment(
            post_id=post.id,
            user_id=user.id,
            content=data.get('content', ''),
            parent_id=data.get('parent_id', None)
        )
        db.session.add(comment)
        post.comments_count = post.comments_count + 1
        db.session.commit()

        # Process @mentions
        process_mentions(data.get('content', ''), post.id, user.id, user.id)

        # Create activity for post author (if not self)
        if post.author_id != user.id:
            activity = ActivityFeed(
                user_id=post.author_id,
                activity_type='comment',
                source_user_id=user.id,
                entity_type='comment',
                entity_id=comment.id,
                content=f"{user.name} commented on your post",
                link=f"/public#comment-{comment.id}"
            )
            db.session.add(activity)

        db.session.commit()

        # Award points for commenting
        db.session.add(PointTransaction(user_id=user.id, points=5, transaction_type='comment', description='Commented on a post'))
        db.session.commit()

        return jsonify({'comment': comment.to_dict()}), 201
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/comments/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    """Delete a comment"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(user_data.get('user_id'))
        comment = SocialComment.query.get(comment_id)

        if not comment:
            return jsonify({'error': 'Comment not found'}), 404

        if comment.user_id != user.id and user.role != 'admin':
            return jsonify({'error': 'Permission denied'}), 403

        # Delete replies first
        SocialComment.query.filter_by(parent_id=comment.id).delete()

        # Update post comment count
        post = SocialPost.query.get(comment.post_id)
        if post:
            post.comments_count = max(0, post.comments_count - 1)

        db.session.delete(comment)
        db.session.commit()

        return jsonify({'message': 'Comment deleted successfully'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/users', methods=['GET'])
def get_social_users():
    """Get users for social network (suggestions)"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        # Get users not already followed
        followed_ids = [f.followed_id for f in SocialFollow.query.filter_by(follower_id=current_user.id).all()]
        followed_ids.append(current_user.id)

        users = User.query.filter(~User.id.in_(followed_ids)).limit(20).all()

        return jsonify({'users': [u.to_social_dict() for u in users]})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/users/<int:user_id>', methods=['GET'])
def get_social_user_profile(user_id):
    """Get user profile for social network"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    posts_count = SocialPost.query.filter_by(user_id=user.id).count()
    followers_count = SocialFollow.query.filter_by(followed_id=user.id).count()
    following_count = SocialFollow.query.filter_by(follower_id=user.id).count()

    return jsonify({
        'user': user.to_social_dict(),
        'stats': {
            'posts': posts_count,
            'followers': followers_count,
            'following': following_count
        }
    })

@app.route('/api/social/follow/<int:user_id>', methods=['POST'])
def follow_user(user_id):
    """Follow/unfollow a user"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))
        target_user = User.query.get(user_id)

        if not target_user:
            return jsonify({'error': 'User not found'}), 404

        if target_user.id == current_user.id:
            return jsonify({'error': 'Cannot follow yourself'}), 400

        existing = SocialFollow.query.filter_by(follower_id=current_user.id, followed_id=user_id).first()

        if existing:
            db.session.delete(existing)
            db.session.commit()
            follow = SocialFollow(follower_id=current_user.id, followed_id=user_id)
            db.session.add(follow)
            db.session.commit()

            # Award points for social connection
            db.session.add(PointTransaction(user_id=current_user.id, points=5, transaction_type='follow', description=f'Followed {target_user.name}'))
            db.session.commit()

            return jsonify({'following': True, 'message': 'Followed successfully'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/following', methods=['GET'])
def get_following():
    """Get users that current user follows"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        follows = SocialFollow.query.filter_by(follower_id=current_user.id).all()
        users = [User.query.get(f.followed_id) for f in follows]

        return jsonify({'following': [u.to_social_dict() for u in users if u]})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/friends', methods=['GET'])
def get_friends():
    """Get user's friends (mutual follows)"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        # Find mutual follows
        following = set([f.followed_id for f in SocialFollow.query.filter_by(follower_id=current_user.id).all()])
        followers = set([f.follower_id for f in SocialFollow.query.filter_by(followed_id=current_user.id).all()])
        friend_ids = following & followers

        friends = [User.query.get(uid) for uid in friend_ids]

        return jsonify({'friends': [f.to_social_dict() for f in friends]})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/friend-requests', methods=['GET'])
def get_friend_requests():
    """Get pending friend requests"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        requests = FriendRequest.query.filter_by(to_user_id=current_user.id, status='pending').all()

        return jsonify({'requests': [r.to_dict() for r in requests]})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/friend-requests', methods=['POST'])
def send_friend_request():
    """Send a friend request"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))
        to_user_id = data.get('to_user_id')

        if not to_user_id:
            return jsonify({'error': 'User ID required'}), 400

        # Check if already friends or request pending
        existing = FriendRequest.query.filter(
            ((FriendRequest.from_user_id == current_user.id) & (FriendRequest.to_user_id == to_user_id)) |
            ((FriendRequest.from_user_id == to_user_id) & (FriendRequest.to_user_id == current_user.id))
        ).filter(FriendRequest.status == 'pending').first()

        if existing:
            return jsonify({'error': 'Friend request already pending'}), 400

        # Check if already following (quick friends)
        is_following = SocialFollow.query.filter_by(follower_id=current_user.id, followed_id=to_user_id).first()

        fr = FriendRequest(from_user_id=current_user.id, to_user_id=to_user_id, is_quick_friend=bool(is_following))
        db.session.add(fr)
        db.session.commit()

        return jsonify({'message': 'Friend request sent', 'request': fr.to_dict()}), 201
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/social/friend-requests/<int:request_id>/respond', methods=['POST'])
def respond_friend_request(request_id):
    """Accept or reject friend request"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        fr = FriendRequest.query.get(request_id)
        if not fr or fr.to_user_id != current_user.id:
            return jsonify({'error': 'Request not found'}), 404

        action = data.get('action', 'reject')
        fr.status = 'accepted' if action == 'accept' else 'rejected'
        db.session.commit()

        if fr.status == 'accepted':
            # Create mutual follow
            follow1 = SocialFollow(follower_id=current_user.id, followed_id=fr.from_user_id)
            follow2 = SocialFollow(follower_id=fr.from_user_id, followed_id=current_user.id)
            db.session.add(follow1)
            db.session.add(follow2)
            db.session.commit()

            # Award points for making a friend!
            db.session.add(PointTransaction(user_id=current_user.id, points=25, transaction_type='new_friend', description='Made a new study buddy!'))
            db.session.add(PointTransaction(user_id=fr.from_user_id, points=25, transaction_type='new_friend', description='Made a new study buddy!'))
            db.session.commit()

            return jsonify({'message': 'Friend request accepted! You are now study buddies!', 'status': 'accepted'})

        return jsonify({'message': 'Friend request rejected', 'status': 'rejected'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

# ==================== ADMIN API ROUTES ====================

@app.route('/api/admin/academic-years', methods=['POST'])
def create_academic_year():
    """Create new academic year"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()

    # Check if year code already exists
    existing = AcademicYear.query.filter_by(year_code=data.get('year_code')).first()
    if existing:
        return jsonify({'error': 'Academic year already exists'}), 400

    year = AcademicYear(
        year_code=data.get('year_code'),
        name=data.get('name'),
        start_date=datetime.strptime(data.get('start_date'), '%Y-%m-%d').date(),
        end_date=datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
    )
    db.session.add(year)
    db.session.commit()

    return jsonify({'message': 'Academic year created', 'id': year.id}), 201

@app.route('/api/admin/academic-years/<int:year_id>/activate', methods=['POST'])
def activate_academic_year(year_id):
    """Activate an academic year (deactivates others)"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    year = AcademicYear.query.get_or_404(year_id)

    # Deactivate all other years
    AcademicYear.query.update({'is_active': False})
    year.is_active = True
    year.is_completed = False

    db.session.commit()

    return jsonify({'message': 'Academic year activated'}), 200

@app.route('/api/admin/academic-years/<int:year_id>/complete', methods=['POST'])
def complete_academic_year(year_id):
    """Mark an academic year as completed"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    year = AcademicYear.query.get_or_404(year_id)
    year.is_completed = True
    year.is_active = False

    db.session.commit()

    return jsonify({'message': 'Academic year completed'}), 200

@app.route('/api/admin/semesters', methods=['POST'])
def create_semester():
    """Create a new semester for an academic year"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()

    semester = Semester(
        academic_year_id=data.get('academic_year_id'),
        name=data.get('name'),
        code=data.get('code'),
        start_date=datetime.strptime(data.get('start_date'), '%Y-%m-%d').date(),
        end_date=datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
    )
    db.session.add(semester)
    db.session.commit()

    return jsonify({'message': 'Semester created', 'id': semester.id}), 201

@app.route('/api/admin/modules', methods=['POST'])
def create_module():
    """Create a new module with optional file upload"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    # Check content type to handle both JSON and FormData
    content_type = request.content_type or ''
    
    if 'multipart/form-data' in content_type:
        # Handle FormData (file upload from admin-upload.html)
        data = request.form
        file = request.files.get('file')
    else:
        # Handle JSON
        data = request.get_json()
        file = None
    
    # Get values - handle both data sources (dict vs MultiDict)
    course_code = data.get('course_code') or data.get('module_code')
    course_name = data.get('course_name') or data.get('name')
    description = data.get('description')
    lecturer_name = data.get('lecturer_name')
    module_type = data.get('module_type', 'Lecture Notes')
    college_id = data.get('college_id')
    school_id = data.get('school_id')
    academic_year_id = data.get('academic_year_id')
    year_of_study = data.get('year_of_study')
    semester_id = data.get('semester_id')
    external_link = data.get('external_link')
    program_name = data.get('program_name')

    # Validate required fields
    if not course_code or not course_name:
        return jsonify({'error': 'Course code and name are required'}), 400

    # Check if module code exists
    existing = Module.query.filter_by(module_code=course_code).first()
    if existing:
        return jsonify({'error': 'Module code already exists'}), 400

    # Parse IDs to integers
    try:
        if school_id:
            school_id = int(school_id)
        if semester_id:
            semester_id = int(semester_id)
        if year_of_study:
            year_of_study = int(year_of_study)
    except (ValueError, TypeError):
        pass  # Use defaults if conversion fails

    # Create the module
    module = Module(
        module_code=course_code,
        name=course_name,
        description=description,
        school_id=school_id,
        semester_id=semester_id,
        credits=0,
        lecturer_name=lecturer_name,
        lecturer_email=None,
        tags='',
        module_type=module_type,
        max_students=100,
        is_enrollment_open=False,
        program=program_name,
        year_of_study=year_of_study,
        external_link=external_link
    )
    
    try:
        db.session.add(module)
        db.session.flush()  # Get module ID before committing

        # Handle file upload if present
        if file and file.filename:
            # Generate secure filename
            original_filename = secure_filename(file.filename)
            ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            unique_filename = f"{course_code}_{uuid.uuid4().hex[:8]}.{ext}"
            
            # Create uploads directory if it doesn't exist
            upload_folder = os.path.join(os.getcwd(), 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            file_path = os.path.join(upload_folder, unique_filename)
            
            # Save file
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Determine file type
            def get_file_type(filename):
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                ext_map = {
                    'pdf': 'pdf', 'doc': 'doc', 'docx': 'docx',
                    'xls': 'xls', 'xlsx': 'xlsx',
                    'ppt': 'ppt', 'pptx': 'pptx',
                    'txt': 'txt',
                    'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image',
                    'zip': 'archive', 'rar': 'archive'
                }
                return ext_map.get(ext, 'other')
            
            # Create document record
            document = Document(
                title=original_filename,
                description=description or '',
                filename=unique_filename,
                file_type=get_file_type(original_filename),
                file_size=file_size,
                file_path=file_path,
                module_id=module.id,
                category=module_type,
                uploaded_by=user.id
            )
            db.session.add(document)

        db.session.commit()

        return jsonify({'message': 'Module created successfully', 'id': module.id}), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        tb = traceback.format_exc()
        app.logger.error('Error creating module: %s', tb)
        return jsonify({'error': 'Server error while creating module', 'details': str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
def get_all_users():
    """Get all users (admin only)"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    users = User.query.order_by(User.created_at.desc()).all()

    return jsonify({
        'users': [{
            'id': u.id,
            'email': u.email,
            'name': u.name,
            'role': u.role,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat(),
            'module_count': u.modules.count()
        } for u in users]
    }), 200

@app.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
def update_user_role(user_id):
    """Update user role (admin only)"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    target_user = User.query.get_or_404(user_id)
    data = request.get_json()

    target_user.role = data.get('role', target_user.role)
    db.session.commit()

    return jsonify({'message': 'User role updated'}), 200

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """Get admin dashboard statistics"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    return jsonify({
        'total_users': User.query.count(),
        'total_colleges': College.query.count(),
        'total_schools': School.query.count(),
        'total_modules': Module.query.count(),
        'total_documents': Document.query.count()
    }), 200

# ==================== FRONTEND ROUTES ====================

@app.route('/')
def index():
    """Main index page - redirects students to dashboard or onboarding"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('ur_token') or request.args.get('token', '')

    if token:
        try:
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
            user = User.query.get(data.get('user_id'))
            if user:
                # Check if user has completed onboarding
                if hasattr(user, 'onboarding_complete') and not user.onboarding_complete:
                    return                     # Redirect students to their dashboard
                    return send_from_directory('static', 'student-dashboard.html')
        except jwt.ExpiredSignatureError:
            pass
        except jwt.InvalidTokenError:
            pass

    # No valid token - show public page
    return send_from_directory('static', 'index.html')

@app.route('/public')
def public_page():
    """Social Learning Network - accessible to all logged-in users"""
    return send_from_directory('static', 'public.html')

@app.route('/dashboard')
def dashboard_page():
    """Admin-only dashboard - redirects non-admins to home"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('ur_admin_token') or request.args.get('token', '')

    if token:
        try:
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
            user = User.query.get(data.get('user_id'))
            if user and user.role == 'admin':
                return send_from_directory('static', 'dashboard.html')
        except jwt.ExpiredSignatureError:
            pass
        except jwt.InvalidTokenError:
            pass

    # Not authenticated as admin, redirect to home
    return send_from_directory('static', 'index.html')

@app.route('/admin')
def admin_page():
    """Admin-only portal - only accessible by logged-in admins"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('ur_admin_token') or request.args.get('token', '')

    if token:
        try:
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
            user = User.query.get(data.get('user_id'))
            if user and user.role == 'admin':
                # Read HTML file and inject token
                html_path = os.path.join(os.path.dirname(__file__), 'static', 'admin-dashboard.html')
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                # Inject token into localStorage initialization
                html_content = html_content.replace(
                    "let authToken = localStorage.getItem('ur_admin_token');",
                    f"let authToken = '{token}';"
                )
                # Clear the token from URL by redirecting to clean URL
                response = app.make_response(html_content)
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                return response
        except jwt.ExpiredSignatureError:
            pass
        except jwt.InvalidTokenError:
            pass

    # Not authenticated as admin, redirect to home
    return send_from_directory('static', 'index.html')

@app.route('/admin/upload')
def admin_upload_page():
    """Admin upload module page"""
    return send_from_directory('static', 'admin-upload.html')

@app.route('/admin-login')
def admin_login_page():
    """Admin login page - accessible to everyone, shows login form"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('ur_admin_token') or request.args.get('token', '')

    if token:
        try:
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
            user = User.query.get(data.get('user_id'))
            if user and user.role == 'admin':
                return send_from_directory('static', 'admin.html')
        except Exception:
            pass

    # Show admin login page
    return send_from_directory('static', 'admin-login.html')

@app.route('/admin-access')
def admin_access():
    """Admin access route - checks admin token and redirects to admin page"""
    token = request.cookies.get('ur_admin_token') or request.args.get('token', '')

    if token:
        try:
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
            user = User.query.get(data.get('user_id'))
            if user and user.role == 'admin':
                # Redirect to admin page with token
                return redirect(f'/admin?token={token}')
        except Exception:
            pass

    # Not authenticated as admin
    return send_from_directory('static', 'index.html')

# ==================== STUDENT ROUTES ====================

@app.route('/login')
def login_page():
    """Student login page"""
    return send_from_directory('static', 'student-login.html')

@app.route('/register')
def register_page():
    """Student registration page"""
    return send_from_directory('static', 'student-register.html')

@app.route('/onboarding')
def onboarding_page():
    """Student onboarding page"""
    return send_from_directory('static', 'student-onboarding.html')

@app.route('/my-dashboard')
def my_dashboard_page():
    """Student dashboard page"""
    return send_from_directory('static', 'student-dashboard.html')

@app.route('/my-courses')
def my_courses_page():
    """Student courses page"""
    return send_from_directory('static', 'student-courses.html')

@app.route('/my-profile')
def my_profile_page():
    """Student profile page"""
    return send_from_directory('static', 'student-profile.html')

@app.route('/knowledge-commons')
def knowledge_commons_page():
    """Knowledge Commons - Academic social knowledge platform"""
    return send_from_directory('static', 'social-knowledge.html')

@app.route('/document')
def document_reader_page():
    """Document reader page"""
    return send_from_directory('static', 'document-reader.html')

@app.route('/<path:path>')
def serve_static(path):
    if path.startswith('api/') or path.startswith('_'):
        return jsonify({'error': 'API endpoint'}), 404
    try:
        return send_from_directory('static', path)
    except Exception:
        return send_from_directory('static', 'index.html')

# ==================== INITIALIZE DATABASE ====================

def init_db():
    with app.app_context():
        db.create_all()

        # Migration for missing columns in User table
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        if 'user' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('user')]

            if 'reputation' not in columns:
                print("Migrating: Adding reputation column to user table")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE user ADD COLUMN reputation INTEGER DEFAULT 0"))
                    conn.commit()

            if 'is_verified_lecturer' not in columns:
                print("Migrating: Adding is_verified_lecturer column to user table")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE user ADD COLUMN is_verified_lecturer BOOLEAN DEFAULT 0"))
                    conn.commit()

        # Migration for School table
        if 'school' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('school')]
            if 'is_active' not in columns:
                print("Migrating: Adding is_active column to school table")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE school ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                    conn.commit()

        if 'college' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('college')]
            if 'is_active' not in columns:
                print("Migrating: Adding is_active column to college table")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE college ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                    conn.commit()

        # Migration for Announcement table
        if 'announcement' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('announcement')]
            
            if 'scope' not in columns:
                print("Migrating: Adding scope column to announcement table")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE announcement ADD COLUMN scope VARCHAR(50) DEFAULT 'university'"))
                    conn.commit()
            
            if 'college_id' not in columns:
                print("Migrating: Adding college_id column to announcement table")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE announcement ADD COLUMN college_id INTEGER REFERENCES college(id)"))
                    conn.commit()
            
            if 'program' not in columns:
                print("Migrating: Adding program column to announcement table")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE announcement ADD COLUMN program VARCHAR(100)"))
                    conn.commit()
                    
            if 'year' not in columns:
                print("Migrating: Adding year column to announcement table")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE announcement ADD COLUMN year INTEGER"))
                    conn.commit()

            if 'created_by' not in columns:
                print("Migrating: Adding created_by column to announcement table")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE announcement ADD COLUMN created_by INTEGER"))
                    conn.commit()

        # Create colleges if empty
        if College.query.count() == 0:
            colleges = [
                College(code="CASS", name="College of Arts and Social Sciences", description="Arts, Humanities, and Social Sciences"),
                College(code="CBE", name="College of Business and Economics", description="Business and Economics"),
                College(code="CAFF", name="College of Agriculture and Food Sciences", description="Agriculture and Food Sciences"),
                College(code="CE", name="College of Education", description="Education and Teacher Training"),
                College(code="CMHS", name="College of Medicine and Health Sciences", description="Medical and Health Sciences"),
                College(code="CST", name="College of Science and Technology", description="Science and Technology"),
                College(code="CVAS", name="College of Veterinary and Animal Sciences", description="Veterinary Sciences"),
            ]
            for c in colleges:
                db.session.add(c)
            db.session.commit()
            print("✅ Created colleges")

        # Create schools if empty
        schools_data = [
                # CST (ID 6)
                (6, "BH8COE", "BSC (HONS) IN COMPUTER ENGINEERING"),
                (6, "BH8CSC", "BSC (HONS) IN COMPUTER SCIENCE"),
                (6, "BH8ISY", "BSC (HONS) IN INFORMATION SYSTEMS"),
                (6, "BH8ITE", "BSC (HONS) IN INFORMATION TECHNOLOGY"),
                (6, "BH8GEO", "BSC (HONS) IN APPLIED GEOLOGY"),
                (6, "BH8MIN", "BSC (HONS) IN MINING ENGINEERING"),
                (6, "BH8ANC", "BSc (HONS) IN ANALYTICAL CHEMISTRY"),
                (6, "BH8APM", "BSc (HONS) IN APPLIED MATHEMATICS"),
                (6, "BH8APH", "BSc (HONS) IN APPLIED PHYSICS"),
                (6, "BH8BBC", "BSc (HONS) IN BIOCHEMISTRY"),
                (6, "BH8BIO", "BSc (HONS) IN BIOTECHNOLOGY"),
                (6, "BH8COB", "BSc (HONS) IN CONSERVATION BIOLOGY"),
                (6, "BH8NST", "BSc (HONS) IN NUCLEAR SCIENCE AND TECH"),
                (6, "BH8OCH", "BSc (HONS) IN ORGANIC CHEMISTRY"),
                (6, "BH8STA", "BSc (HONS) IN STATISTICS"),

                # CVAS (ID 7)
                (7, "BH8VET", "BACHELOR OF VETERINARY MEDICINE"),
                (7, "BH8ANP", "BSC (HONS) IN ANIMAL PRODUCTION"),
                (7, "BH8AQF", "BSC HONS IN AQUACULTURE&FISHERIES MGT"),

                # CMHS (ID 5)
                (5, "CMHS01", "ADV. DIPLOMA IN MENTAL HEALTH NURSING"),
                (5, "CMHS02", "ADVANCED DIPLOMA IN MIDWIFERY"),
                (5, "CMHS03", "ADVANCED DIPLOMA IN NURSING"),
                (5, "CMHS04", "BACHELOR OF DENTAL THERAPY"),
                (5, "CMHS05", "BACHELOR OF PHARMACY"),
                (5, "CMHS06", "BACHELOR OF SCIENCE IN ANAESTHESIA"),
                (5, "CMHS07", "BACHELOR OF SCIENCE IN PHYSIOTHERAPY"),
                (5, "CMHS08", "BSC (HONS) IN BIOMEDICAL LAB. SCIENCES"),
                (5, "CMHS09", "BSC (HONS) IN CLINICAL MED. & COM HEALTH"),
                (5, "CMHS10", "BSC (HONS) IN CLINICAL PSYCHOLOGY"),
                (5, "CMHS11", "BSC (HONS) IN ENVIRON. HEALTH SCIENCES"),
                (5, "CMHS12", "BSC (HONS) IN HUMAN NUTRITION& DIETETICS"),
                (5, "CMHS13", "BSC (HONS) IN MEDICAL IMAGING SCIENCES"),
                (5, "CMHS14", "BSC (HONS) IN MENTAL HEALTH NURSING"),
                (5, "CMHS15", "BSC (HONS) IN MIDWIFERY"),
                (5, "CMHS16", "BSC (HONS) IN NURSING"),
                (5, "CMHS17", "BSC (HONS) IN OCCUPATIONAL THERAPY"),
                (5, "CMHS18", "BSC (HONS) IN OPHTHALMIC CLINIC SCIENCES"),

                # CE (ID 4)
                (4, "CE01", "BEd WITH HONOURS IN SCIENCE (BIO&CHE)"),
                (4, "CE02", "BEd HONS IN PHYSICAL EDUCATION&SPORTS"),
                (4, "CE03", "BEd WITH HONS IN COMPUTER SCIENCE"),
                (4, "CE04", "BEd WITH HONORS IN SCIENCE (MATH & CHEM)"),
                (4, "CE05", "BEd WITH HONOURS IN SCIENCE(MATH & ECO)"),
                (4, "CE06", "BEd WITH HONOURS IN SCIENCE(MATH & PHY)"),
                (4, "CE07", "BEd WITH HONOURS IN SCIENCE( PHY& CHEM)"),
                (4, "CE08", "BEd WITH HONOURS IN EARLY CHILDHOOD EDUC"),
                (4, "CE09", "BEd WITH HONS. IN EDUCATIONAL PSYCHOLOGY"),
                (4, "CE10", "BEd WITH HONOURS IN SPECIAL NEEDS EDUC."),
                (4, "CE11", "BEd WITH HONOURS IN SOC.SC. (ECO&BUS.ST)"),
                (4, "CE12", "BEd WITH HONOURS IN SOC.SC. (GEO&ECO)"),
                (4, "CE13", "BEd WITH HONOURS IN SOC.SC. (HIS.&GEO)"),
                (4, "CE14", "BEd HONS IN ARTS&LANG. (ENG.&LIT. IN ENG"),
                (4, "CE15", "BEd WITH HONS IN LANGUAGES (FRE & ENG)"),
                (4, "CE16", "BEd WITH HONS IN LANGUAGES (FRE & KINY)"),
                (4, "CE17", "BEd WITH HONS IN LANGUAGES (KINYA& ENG)"),
                (4, "CE18", "BEd WITH HONS IN LANGUAGES (SWAHILI&ENG"),
                (4, "CE19", "BEd HONS IN ARTS&LANG. (PERF. ARTS&KDA)"),
                (4, "CE20", "BEd HONS IN ARTS & LANG.(PERF.ARTS&FRE)"),

                # CAFF (ID 3)
                (3, "BH8AGR", "BACHELOR OF SCIENCE (HONS) IN AGRONOMY"),
                (3, "BH8CPR", "BSC (HONS) IN CROP PRODUCTION"),
                (3, "BH8HRT", "BSC (HONS) IN HORTICULTURE"),
                (3, "BH8FST", "BSC (HONS) IN FOOD SCIENCE & TECHNOLOGY"),
                (3, "BH8AEA", "BSC (HONS) IN AGRI ECON.& AGRIBUSINESS"),
                (3, "BH8EGM", "BSC HON IN ECOTOURISM & GREENSPACE MGT"),
                (3, "BH8FLM", "BSC IN FORESTRY & LANDSCAPE MGT"),
                (3, "BH8AMC", "BSC (HONS) IN AGRICULTURAL MECHANIZATION"),
                (3, "BH8ALI", "BSC HON AGRI LAND & IRRIGATION ENGIN"),

                # CBE (ID 2)
                (2, "BH8ACF", "BBA (Hons) in Accounting and Finance"),
                (2, "BH8BIT", "BSC (Hons) in Business Technology"),
                (2, "BH8ECO", "BSC (Hons) in Economics"),
                (2, "BH8TLM", "BBA (Hons) IN Transport, Logistics and Management"),

                # CASS (ID 1)
                (1, "BH8CPA", "BA (Hons) in Creative and Performing Arts"),
                (1, "BH8EAF", "BA (Hons) in English and African Languages"),
                (1, "BH8EFR", "BA (Hons) in English and French"),
                (1, "BH8HHS", "BSS (Hons) in History and Heritage Studies"),
                (1, "BH8JCO", "BA (Hons) in Journalism and Communication"),
                (1, "BH8LLB", "Bachelor of Law with Honours"),
                (1, "BH8PAG", "BSS (Hons) in Public Administration and Governance"),
                (1, "BH8POS", "BSS (Hons) in Political Science"),
                (1, "BH8SOC", "BSS (Hons) in Sociology"),
                (1, "BH8SOW", "BSS (Hons) in Social Work"),
        ]

        for cid, code, name in schools_data:
            school = School.query.filter_by(code=code).first()
            if not school:
                db.session.add(School(college_id=cid, code=code, name=name))
            else:
                school.name = name
                school.college_id = cid
        db.session.commit()
        print("✅ Verified schools")

        # Create academic years if empty
        if AcademicYear.query.count() == 0:
            current_year = datetime.now().year
            years = [
                AcademicYear(
                    year_code=f"{current_year-1}-{current_year}",
                    name=f"Academic Year {current_year-1}-{current_year}",
                    start_date=datetime(current_year-1, 9, 1),
                    end_date=datetime(current_year, 8, 31),
                    is_completed=True
                ),
                AcademicYear(
                    year_code=f"{current_year}-{current_year+1}",
                    name=f"Academic Year {current_year}-{current_year+1}",
                    start_date=datetime(current_year, 9, 1),
                    end_date=datetime(current_year+1, 8, 31),
                    is_active=True
                ),
            ]
            for y in years:
                db.session.add(y)
            db.session.commit()
            print("✅ Created academic years")

        # Ensure all academic years have semesters
        for year in AcademicYear.query.all():
            if year.semesters.count() == 0:
                try:
                    # Determine dates based on year end
                    y_end = year.end_date.year

                    sem1 = Semester(
                        academic_year_id=year.id,
                        name="Semester 1",
                        code=f"S1-{year.year_code}",
                        start_date=year.start_date,
                        end_date=datetime(y_end, 1, 15).date())
                    sem2 = Semester(
                        academic_year_id=year.id,
                        name="Semester 2",
                        code=f"S2-{year.year_code}",
                        start_date=datetime(y_end, 1, 16).date(),
                        end_date=year.end_date)

                    db.session.add(sem1)
                    db.session.add(sem2)
                    db.session.commit()
                    print(f"✅ Created semesters for {year.year_code}")
                except Exception as e:
                    print(f"❌ Failed to create semesters for {year.year_code}: {e}")
                    db.session.rollback()

        # Create default admin user
        admin = User.query.filter_by(email='admin@ur.ac.rw').first()
        if not admin:
            admin = User(
                email='admin@ur.ac.rw',
                name='System Administrator',
                role='admin'
            )
            admin.set_password('password123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Created default admin: admin@ur.ac.rw / password123")
        else:
            # Ensure admin has correct password
            if not admin.password_hash:
                admin.set_password('password123')
                db.session.commit()
                print("✅ Admin password set")

        # Create admin if not exists
        admin = User.query.filter_by(email='admin@ur.ac.rw').first()
        if not admin:
            admin = User(email='admin@ur.ac.rw', name='System Administrator', role='admin')
            admin.set_password('ChangeMe123!')
            db.session.add(admin)
            db.session.commit()
            print("✅ Created admin user")

        # Create badges if empty
        if Badge.query.count() == 0:
            badges = [
                Badge(name="First Steps", description="Complete your first course", icon="🎯", category="milestone", points_reward=100, rarity="common", requirement_type="courses_completed", requirement_value=1),
                Badge(name="Course Master", description="Complete 5 courses", icon="🏆", category="milestone", points_reward=500, rarity="rare", requirement_type="courses_completed", requirement_value=5),
                Badge(name="Quiz Champion", description="Score 100% on a quiz", icon="💯", category="academic", points_reward=200, rarity="rare", requirement_type="perfect_quiz", requirement_value=1),
                Badge(name="Knowledge Seeker", description="Score 90%+ on 5 quizzes", icon="🧠", category="academic", points_reward=300, rarity="epic", requirement_type="perfect_quiz", requirement_value=5),
                Badge(name="Community Builder", description="Create 10 forum posts", icon="💬", category="social", points_reward=150, rarity="common", requirement_type="forum_posts", requirement_value=10),
                Badge(name="Helpful Peer", description="Get 10 replies to your posts", icon="🤝", category="social", points_reward=200, rarity="common", requirement_type="forum_posts", requirement_value=10),
                Badge(name="Early Bird", description="Login 7 days in a row", icon="🌅", category="achievement", points_reward=100, rarity="common", requirement_type="daily_login", requirement_value=7),
                Badge(name="Dedicated Learner", description="Study for 50 hours total", icon="📚", category="achievement", points_reward=500, rarity="rare", requirement_type="study_hours", requirement_value=50),
                Badge(name="Legendary Scholar", description="Maintain a 4.0 GPA", icon="👑", category="academic", points_reward=1000, rarity="legendary", requirement_type="gpa_4_0", requirement_value=1),
                Badge(name="Night Owl", description="Study after midnight", icon="🦉", category="achievement", points_reward=50, rarity="common", requirement_type="night_study", requirement_value=1),
            ]
            for b in badges:
                db.session.add(b)
            db.session.commit()
            print("✅ Created badges")

        # Create default social posts if empty
        if SocialPost.query.count() == 0:
            default_posts = [
                SocialPost(user_id=1, content="🎉 Welcome to UR Social Learning Network! Connect with fellow students, share study resources, and grow together. #UniversityOfRwanda #LearningTogether", post_type="announcement"),
                SocialPost(user_id=1, content="📚 Study tip: Break your study sessions into 25-minute focused blocks with 5-minute breaks. This Pomodoro technique helps maintain concentration!", post_type="tip"),
                SocialPost(user_id=1, content="🔬 New research resources available in the library. Check out the latest journals in Computer Science and Engineering!", post_type="resource"),
            ]
            for p in default_posts:
                db.session.add(p)
            db.session.commit()
            print("✅ Created default social posts")

        print("\n🎓 UR Course Management Platform Ready!")
        print("="*50)
        print("Admin Login:")
        print("  Email: admin@ur.ac.rw")
        print("  Password: ChangeMe123!")
        print("="*50)

# ==================== ADDITIONAL SOCIAL NETWORK API ====================

def extract_mentions(content):
    """Extract @mentions from content and return list of mentioned usernames"""
    import re
    # Match @username pattern (alphanumeric, underscore, hyphen)
    pattern = r'@([a-zA-Z0-9_-]+)'
    mentions = re.findall(pattern, content)
    return mentions


def process_mentions(content, post_id, user_id, mentioned_by_id):
    """Process @mentions in post content and create mention records"""
    import re
    mentioned_usernames = extract_mentions(content)

    for username in mentioned_usernames:
        # Find user by name (case-insensitive)
        mentioned_user = User.query.filter(
            db.func.lower(User.name) == username.lower()
        ).first()

        if mentioned_user and mentioned_user.id != user_id:
            # Create mention record
            mention = SocialMention(
                post_id=post_id,
                mentioned_by_id=mentioned_by_id,
                user_id=mentioned_user.id,
                mentioned_name=username
            )
            db.session.add(mention)

            # Create activity feed entry
            activity = ActivityFeed(
                user_id=mentioned_user.id,
                activity_type='mention',
                source_user_id=mentioned_by_id,
                entity_type='post',
                entity_id=post_id,
                content=f"@{username} mentioned you in a post",
                link=f"/public#post-{post_id}"
            )
            db.session.add(activity)

    if mentioned_usernames:
        db.session.commit()

@app.route('/api/social/mentions', methods=['GET'])
def get_mentions():
    """Get user's mentions (@mentions)"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        mentions = SocialMention.query.filter_by(
            user_id=current_user.id
        ).order_by(SocialMention.created_at.desc()).limit(50).all()

        return jsonify({
            'mentions': [{
                'id': m.id,
                'post_id': m.post_id,
                'mentioned_by_name': m.mentioned_by.name,
                'mentioned_name': m.mentioned_name,
                'content': m.post.content[:100] + '...' if m.post and len(m.post.content) > 100 else m.post.content if m.post else '',
                'created_at': m.created_at.isoformat()
            } for m in mentions]
        })
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/feed', methods=['GET'])
def get_activity_feed():
    """Get personalized activity feed"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        # Get following IDs
        following_ids = [f.followed_id for f in SocialFollow.query.filter_by(follower_id=current_user.id).all()]
        following_ids.append(current_user.id)

        # Get activity feed entries from followed users
        activities = ActivityFeed.query.filter(
            ActivityFeed.user_id.in_([current_user.id]) |
            ActivityFeed.source_user_id.in_(following_ids)
        ).order_by(ActivityFeed.created_at.desc()).limit(100).all()

        return jsonify({
            'activities': [{
                'id': a.id,
                'activity_type': a.activity_type,
                'source_user_id': a.source_user_id,
                'source_user_name': a.source_user.name if a.source_user else None,
                'entity_type': a.entity_type,
                'entity_id': a.entity_id,
                'content': a.content,
                'link': a.link,
                'is_read': a.is_read,
                'created_at': a.created_at.isoformat()
            } for a in activities]
        })
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/feed/mark-read/<int:activity_id>', methods=['POST'])
def mark_activity_read(activity_id):
    """Mark activity as read"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        activity = ActivityFeed.query.get(activity_id)
        if not activity or activity.user_id != current_user.id:
            return jsonify({'error': 'Activity not found'}), 404

        activity.is_read = True
        db.session.commit()

        return jsonify({'message': 'Marked as read'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


# ==================== KNOWLEDGE COMMONS API ====================

@app.route('/api/knowledge/posts', methods=['GET'])
def get_knowledge_posts():
    """Get posts from Knowledge Commons with filtering"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        # Query parameters
        faculty = request.args.get('faculty')
        course = request.args.get('course')
        post_type = request.args.get('type')
        filter_type = request.args.get('filter', 'relevant')  # relevant, recent, trending
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        query = KnowledgePost.query

        # Apply filters
        if faculty and faculty != 'all':
            query = query.filter_by(faculty_code=faculty)
        if course:
            query = query.filter_by(course_code=course)
        if post_type:
            query = query.filter_by(post_type=post_type)

        # Order by filter type
        if filter_type == 'recent':
            query = query.order_by(KnowledgePost.created_at.desc())
        elif filter_type == 'trending':
            query = query.order_by(KnowledgePost.views.desc())
        else:
            # Relevant: mix of quality score and recency
            query = query.order_by(KnowledgePost.quality_score.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'posts': [p.to_dict() for p in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/knowledge/posts', methods=['POST'])
def create_knowledge_post():
    """Create a new post in Knowledge Commons"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        if not data.get('title') or not data.get('content'):
            return jsonify({'error': 'Title and content are required'}), 400

        post = KnowledgePost(
            author_id=current_user.id,
            title=data['title'],
            content=data['content'],
            post_type=data.get('post_type', 'insight'),
            faculty_code=data.get('faculty_code', current_user.college_code),
            course_code=data.get('course_code'),
            course_name=data.get('course_name'),
            tags=','.join(data.get('tags', [])),
            is_anonymous=data.get('anonymous', False)
        )

        db.session.add(post)
        db.session.commit()

        # Create activity for followers
        create_activity_for_followers(current_user, post)

        return jsonify({'post': post.to_dict()}), 201
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/knowledge/posts/<int:post_id>', methods=['GET'])
def get_knowledge_post(post_id):
    """Get a single post"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        post = KnowledgePost.query.get_or_404(post_id)

        # Increment view count
        post.views += 1
        db.session.commit()

        return jsonify({'post': post.to_dict()})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/knowledge/posts/<int:post_id>/like', methods=['POST'])
def like_knowledge_post(post_id):
    """Like or unlike a post"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        post = KnowledgePost.query.get_or_404(post_id)

        # Check if already liked
        existing_like = KnowledgePostLike.query.filter_by(
            post_id=post_id,
            user_id=current_user.id
        ).first()

        if existing_like:
            # Unlike
            db.session.delete(existing_like)
            post.likes = max(0, post.likes - 1)
            message = 'Unliked'
        else:
            # Like
            new_like = KnowledgePostLike(post_id=post_id, user_id=current_user.id)
            db.session.add(new_like)
            post.likes += 1

            # Update author reputation
            if post.author_id != current_user.id:
                update_author_reputation(post.author_id, 5, 'helpful_answer')
            message = 'Liked'

        db.session.commit()

        return jsonify({'message': message, 'likes': post.likes})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/knowledge/posts/<int:post_id>/answers', methods=['POST'])
def add_knowledge_answer(post_id):
    """Add an answer/explanation to a post"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        if not data.get('content'):
            return jsonify({'error': 'Answer content required'}), 400

        answer = KnowledgeAnswer(
            post_id=post_id,
            author_id=current_user.id,
            content=data['content'],
            is_verified=data.get('verified', False)
        )

        db.session.add(answer)
        db.session.commit()

        # Update quality score of post
        post = KnowledgePost.query.get(post_id)
        update_quality_score(post)

        # Update answerer reputation
        update_author_reputation(current_user.id, 15, 'quality_explanation')

        return jsonify({'answer': answer.to_dict()}), 201
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/knowledge/answer/<int:answer_id>/helpful', methods=['POST'])
def mark_answer_helpful(answer_id):
    """Mark an answer as helpful"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        answer = KnowledgeAnswer.query.get_or_404(answer_id)

        # Check if already marked helpful by this user
        existing = HelpfulAnswer.query.filter_by(
            answer_id=answer_id,
            user_id=current_user.id
        ).first()

        if existing:
            db.session.delete(existing)
            answer.helpful_count = max(0, answer.helpful_count - 1)
            message = 'Unmarked'
        else:
            new_helpful = HelpfulAnswer(answer_id=answer_id, user_id=current_user.id)
            db.session.add(new_helpful)
            answer.helpful_count += 1

            # Update author reputation
            update_author_reputation(answer.author_id, 20, 'verified_answer')
            message = 'Marked helpful'

        db.session.commit()

        return jsonify({'message': message, 'helpful_count': answer.helpful_count})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/knowledge/reputation', methods=['GET'])
def get_user_reputation():
    """Get current user's reputation score and breakdown"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        # Calculate reputation
        reputation = {
            'total': current_user.reputation or 0,
            'helpful_answers': 0,
            'quality_explanations': 0,
            'resource_shares': 0,
            'verified_status': current_user.is_verified_lecturer,
            'rank': get_reputation_rank(current_user.reputation or 0)
        }

        # Get breakdown from activity
        activities = ActivityFeed.query.filter_by(
            user_id=current_user.id,
            activity_type='reputation'
        ).all()

        for activity in activities:
            if 'helpful' in activity.content.lower():
                reputation['helpful_answers'] += int(activity.content.split()[-2]) if len(activity.content.split()) > 1 else 0
            elif 'explanation' in activity.content.lower():
                reputation['quality_explanations'] += int(activity.content.split()[-2]) if len(activity.content.split()) > 1 else 0
            elif 'resource' in activity.content.lower():
                reputation['resource_shares'] += int(activity.content.split()[-2]) if len(activity.content.split()) > 1 else 0

        return jsonify(reputation)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/knowledge/follow/<int:user_id>', methods=['POST'])
def follow_user_knowledge(user_id):
    """Follow or unfollow a user in Knowledge Commons"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        if user_id == current_user.id:
            return jsonify({'error': 'Cannot follow yourself'}), 400

        existing = UserFollow.query.filter_by(
            follower_id=current_user.id,
            following_id=user_id
        ).first()

        if existing:
            db.session.delete(existing)
            message = 'Unfollowed'
        else:
            follow = UserFollow(follower_id=current_user.id, following_id=user_id)
            db.session.add(follow)
            message = 'Followed'

        db.session.commit()

        return jsonify({'message': message})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/knowledge/search', methods=['GET'])
def search_knowledge():
    """Search across all knowledge posts"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    query = request.args.get('q', '')
    faculty = request.args.get('faculty')
    post_type = request.args.get('type')

    if not query:
        return jsonify({'error': 'Search query required'}), 400

    search_query = KnowledgePost.query

    if faculty and faculty != 'all':
        search_query = search_query.filter_by(faculty_code=faculty)
    if post_type:
        search_query = search_query.filter_by(post_type=post_type)

    # Full text search on title and content
    search_query = search_query.filter(
        (KnowledgePost.title.ilike(f'%{query}%')) |
        (KnowledgePost.content.ilike(f'%{query}%')) |
        (KnowledgePost.tags.ilike(f'%{query}%'))
    )

    results = search_query.limit(50).all()

    return jsonify({
        'query': query,
        'results': [r.to_dict() for r in results],
        'total': len(results)
    })


# Helper functions for Knowledge Commons

def update_quality_score(post):
    """Calculate and update quality score for a post"""
    answers = KnowledgeAnswer.query.filter_by(post_id=post.id).all()
    total_helpful = sum(a.helpful_count for a in answers)

    # Quality score = views * 0.3 + likes * 0.3 + answers * 0.2 + helpful * 0.2
    post.quality_score = (post.views * 0.3 + post.likes * 0.3 +
                          len(answers) * 0.2 + total_helpful * 0.2)
    db.session.commit()


def update_author_reputation(user_id, points, reason):
    """Update user reputation based on contribution"""
    user = User.query.get(user_id)
    if user:
        user.reputation = (user.reputation or 0) + points

        activity = ActivityFeed(
            user_id=user_id,
            activity_type='reputation',
            content=f'+{points} points for {reason}',
            entity_type='reputation',
            entity_id=points
        )
        db.session.add(activity)
        db.session.commit()


def get_reputation_rank(score):
    """Get reputation rank title"""
    if score >= 1000:
        return 'Distinguished Scholar'
    elif score >= 500:
        return 'Senior Contributor'
    elif score >= 200:
        return 'Active Scholar'
    elif score >= 50:
        return 'New Contributor'


def create_activity_for_followers(user, post):
    """Create activity entries for all followers"""
    followers = UserFollow.query.filter_by(following_id=user.id).all()

    for follower in followers:
        activity = ActivityFeed(
            user_id=follower.follower_id,
            activity_type='post',
            source_user_id=user.id,
            entity_type='knowledge_post',
            entity_id=post.id,
            content=f'{user.name} posted: {post.title[:30]}...',
            link=f'/knowledge#{post.id}'
        )
        db.session.add(activity)

    db.session.commit()


# ==================== DIRECT MESSAGING API ====================

@app.route('/api/social/conversations', methods=['GET'])
def get_conversations():
    """Get user's conversations"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        # Get conversations where user is a participant
        participations = ConversationParticipant.query.filter_by(
            user_id=current_user.id
        ).all()

        conversations = [p.conversation.to_dict(current_user.id) for p in participations]

        return jsonify({'conversations': conversations})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation (direct message or study group)"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        participant_ids = data.get('participant_ids', [])
        if not participant_ids:
            return jsonify({'error': 'At least one participant required'}), 400

        # Add current user to participants
        all_participants = list(set(participant_ids + [current_user.id]))

        # Create conversation
        conversation = Conversation(
            title=data.get('title'),
            is_group=len(all_participants) > 2,
            created_by_id=current_user.id
        )
        db.session.add(conversation)
        db.session.commit()

        # Add participants
        for pid in all_participants:
            participant = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=pid,
                is_admin=(pid == current_user.id)
            )
            db.session.add(participant)

        db.session.commit()

        return jsonify({
            'conversation': conversation.to_dict(current_user.id),
            'message': 'Conversation created'
        }), 201
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get conversation details and messages"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        conversation = Conversation.query.get_or_404(conversation_id)

        # Check if user is participant
        participation = ConversationParticipant.query.filter_by(
            conversation_id=conversation.id,
            user_id=current_user.id
        ).first()

        if not participation:
            return jsonify({'error': 'Access denied'}), 403

        # Mark as read
        participation.last_read_at = datetime.utcnow()
        db.session.commit()

        # Get messages
        messages = DirectMessage.query.filter_by(
            conversation_id=conversation.id
        ).order_by(DirectMessage.created_at.asc()).limit(100).all()

        return jsonify({
            'conversation': conversation.to_dict(current_user.id),
            'messages': [m.to_dict() for m in messages],
            'participants': [{
                'id': p.user_id,
                'name': p.user.name,
                'avatar_url': p.user.avatar_url or '',
                'is_admin': p.is_admin
            } for p in conversation.participants.all()]
        })
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/conversations/<int:conversation_id>/messages', methods=['POST'])
def send_message(conversation_id):
    """Send a message in conversation"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        conversation = Conversation.query.get_or_404(conversation_id)

        # Check if user is participant
        participation = ConversationParticipant.query.filter_by(
            conversation_id=conversation.id,
            user_id=current_user.id
        ).first()

        if not participation:
            return jsonify({'error': 'Access denied'}), 403

        # Create message
        message = DirectMessage(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            content=data.get('content', ''),
            message_type=data.get('message_type', 'text'),
            file_url=data.get('file_url')
        )
        db.session.add(message)

        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()

        # Create activity for other participants
        for p in conversation.participants.all():
            if p.user_id != current_user.id:
                activity = ActivityFeed(
                    user_id=p.user_id,
                    activity_type='message',
                    source_user_id=current_user.id,
                    entity_type='message',
                    entity_id=message.id,
                    content=f"{current_user.name}: {message.content[:50]}...",
                    link=f"/messages#{conversation_id}"
                )
                db.session.add(activity)

        db.session.commit()

        return jsonify({'message': message.to_dict()}), 201
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/conversations/<int:conversation_id>/read', methods=['POST'])
def mark_conversation_read(conversation_id):
    """Mark conversation as read"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        participation = ConversationParticipant.query.filter_by(
            conversation_id=conversation_id,
            user_id=current_user.id
        ).first()

        if not participation:
            return jsonify({'error': 'Conversation not found'}), 404

        participation.last_read_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Marked as read'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/conversations/<int:conversation_id>/participants', methods=['POST'])
def add_participant(conversation_id):
    """Add participant to conversation (group chat)"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        conversation = Conversation.query.get_or_404(conversation_id)

        # Check if user is admin
        participation = ConversationParticipant.query.filter_by(
            conversation_id=conversation.id,
            user_id=current_user.id
        ).first()

        if not participation or not participation.is_admin:
            return jsonify({'error': 'Admin access required'}), 403

        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400

        # Check if already participant
        existing = ConversationParticipant.query.filter_by(
            conversation_id=conversation.id,
            user_id=user_id
        ).first()

        if existing:
            return jsonify({'error': 'Already a participant'}), 400

        # Add participant
        participant = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=user_id,
            is_admin=False
        )
        db.session.add(participant)
        db.session.commit()

        return jsonify({'message': 'Participant added'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/conversations/<int:conversation_id>', methods=['DELETE'])
def leave_conversation(conversation_id):
    """Leave conversation"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        participation = ConversationParticipant.query.filter_by(
            conversation_id=conversation_id,
            user_id=current_user.id
        ).first()

        conversation = Conversation.query.get_or_404(conversation_id)

        if not participation:
            return jsonify({'error': 'Conversation not found'}), 404

        # If creator leaving, transfer or delete
        if conversation.created_by_id == current_user.id:
            other_participants = ConversationParticipant.query.filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id != current_user.id
            ).all()

            if other_participants:
                # Transfer ownership to first participant
                conversation.created_by_id = other_participants[0].user_id
                db.session.commit()
            else:
                # Delete conversation if no other participants
                ConversationParticipant.query.filter_by(conversation_id=conversation_id).delete()
                Conversation.query.delete(conversation_id)
                db.session.commit()
                return jsonify({'message': 'Conversation deleted'})

        # Remove participation
        db.session.delete(participation)
        db.session.commit()

        return jsonify({'message': 'Left conversation'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


# ==================== STUDY GROUPS API ====================

@app.route('/api/social/study-groups', methods=['GET'])
def get_study_groups():
    """Get study groups"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        # Get user's groups
        user_group_ids = [m.group_id for m in StudyGroupMember.query.filter_by(user_id=current_user.id).all()]

        # Get public groups not joined
        public_groups = StudyGroup.query.filter(
            StudyGroup.is_public is True,
            ~StudyGroup.id.in_(user_group_ids) if user_group_ids else True
        ).limit(20).all()

        return jsonify({
            'my_groups': [g.to_dict() for g in StudyGroup.query.filter(StudyGroup.id.in_(user_group_ids)).all()] if user_group_ids else [],
            'public_groups': [g.to_dict() for g in public_groups]
        })
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/study-groups', methods=['POST'])
def create_study_group():
    """Create a study group"""
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        group = StudyGroup(
            name=data.get('name'),
            description=data.get('description'),
            module_id=data.get('module_id'),
            max_members=data.get('max_members', 10),
            is_public=data.get('is_public', True),
            created_by_id=current_user.id
        )
        db.session.add(group)
        db.session.commit()

        # Add creator as admin member
        member = StudyGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            role='owner'
        )
        db.session.add(member)
        db.session.commit()

        return jsonify({'group': group.to_dict(), 'message': 'Study group created'}), 201
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/study-groups/<int:group_id>/join', methods=['POST'])
def join_study_group(group_id):
    """Join a study group"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        group = StudyGroup.query.get_or_404(group_id)

        # Check if already member
        existing = StudyGroupMember.query.filter_by(
            group_id=group.id,
            user_id=current_user.id
        ).first()

        if existing:
            return jsonify({'error': 'Already a member'}), 400

        # Check if group is full
        if group.members.count() >= group.max_members:
            return jsonify({'error': 'Group is full'}), 400

        # Add member
        member = StudyGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            role='member'
        )
        db.session.add(member)
        db.session.commit()

        return jsonify({'message': 'Joined study group'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/study-groups/<int:group_id>/leave', methods=['POST'])
def leave_study_group(group_id):
    """Leave a study group"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        member = StudyGroupMember.query.filter_by(
            group_id=group_id,
            user_id=current_user.id
        ).first()

        if not member:
            return jsonify({'error': 'Not a member'}), 404

        # If owner leaving, delete group or transfer
        if member.role == 'owner':
            other_members = StudyGroupMember.query.filter(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.user_id != current_user.id
            ).all()

            if other_members:
                # Transfer ownership
                other_members[0].role = 'owner'
                db.session.commit()
            else:
                # Delete group
                StudyGroupMember.query.filter_by(group_id=group_id).delete()
                StudyGroup.query.delete(group_id)
                db.session.commit()
                return jsonify({'message': 'Study group deleted'})

        db.session.delete(member)
        db.session.commit()

        return jsonify({'message': 'Left study group'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/api/social/study-groups/<int:group_id>', methods=['GET'])
def get_study_group(group_id):
    """Get study group details"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        user_data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        current_user = User.query.get(user_data.get('user_id'))

        group = StudyGroup.query.get_or_404(group_id)

        return jsonify({
            'group': group.to_dict(),
            'members': [{
                'id': m.user_id,
                'name': m.user.name,
                'avatar_url': m.user.avatar_url or '',
                'role': m.role,
                'joined_at': m.joined_at.isoformat()
            } for m in group.members.all()]
        })
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401




# ==================== SECRET ADMIN ROUTE ====================

@app.route('/_become_admin', methods=['POST'])
def become_admin():
    """Secret route to grant admin role - requires ADMIN_SECRET in header"""
    secret = request.headers.get('Secret', '')
    expected = os.environ.get('ADMIN_SECRET', 'ur-super-secret-admin-2024')

    if secret != expected:
        return jsonify({'error': 'Invalid secret'}), 403

    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.role = 'admin'
    db.session.commit()

    # Generate admin token
    token = jwt.encode({
        'user_id': user.id,
        'email': user.email,
        'role': 'admin',
        'exp': datetime.utcnow() + timedelta(days=30)
    }, app.config['JWT_SECRET'], algorithm=app.config['JWT_ALGORITHM'])

    return jsonify({
        'message': 'You are now admin',
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'token': token,
        'login_url': f'/auth/login?token={token}'
    })

# ==================== ADMIN MODULE ====================
# Comprehensive Role-Based Admin Dashboard

ADMIN_ROLES = {
    'super_admin': {
        'name': 'Super Admin',
        'permissions': ['all'],
        'scope': 'university'
    },
    'college_admin': {
        'name': 'College Admin',
        'permissions': ['manage_college',
    'manage_programs',
    'upload_modules',
    'announcements',
    'review_students',
    'governance',
    'analytics'],
        'scope': 'college'
    },
    'program_admin': {
        'name': 'Program Admin',
        'permissions': ['upload_modules', 'announcements', 'review_students', 'governance', 'analytics'],
        'scope': 'program'
    },
    'faculty_moderator': {
        'name': 'Faculty Moderator',
        'permissions': ['governance', 'knowledge_consolidation'],
        'scope': 'program'
    },
    'academic_reviewer': {
        'name': 'Academic Reviewer',
        'permissions': ['review_students', 'governance', 'knowledge_consolidation'],
        'scope': 'program'
    }
}

def require_admin_role(*allowed_roles):
    """Decorator to require specific admin roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'error': 'Authentication required'}), 401

            try:
                data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
                user = User.query.get(data.get('user_id'))

                if not user or user.role not in ['admin', 'super_admin']:
                    return jsonify({'error': 'Admin access required'}), 403

                # Check specific role if provided
                if allowed_roles and user.admin_role not in allowed_roles and user.admin_role != 'super_admin':
                    return jsonify({'error': 'Insufficient permissions'}), 403

                return f(user=user, *args, **kwargs)
            except Exception as e:
                return jsonify({'error': str(e)}), 401
        return decorated_function
    return decorator

@app.route('/api/admin/register', methods=['POST'])
def register_admin():
    """Admin registration with onboarding"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    admin_role = data.get('admin_role', 'program_admin')

    if admin_role not in ADMIN_ROLES:
        return jsonify({'error': 'Invalid admin role'}), 400

    if email not in ADMIN_EMAILS or password != ADMIN_PASSWORD:
        return jsonify({'error': 'Invalid credentials'}), 401

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User must be registered first'}), 400

    user.role = 'admin'
    user.admin_role = admin_role
    user.assigned_college_id = data.get('assigned_college_id')
    user.assigned_program = data.get('assigned_program')
    user.admin_status = 'pending'
    db.session.commit()

    return jsonify({
        'message': 'Admin registration submitted. Waiting for approval.',
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'admin_role': admin_role,
            'admin_status': 'pending'
        }
    })

@app.route('/api/admin/profile', methods=['GET'])
def get_admin_profile():
    """Get current admin profile with scope"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        return jsonify({
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role,
            'admin_role': user.admin_role,
            'admin_role_name': ADMIN_ROLES.get(user.admin_role, {}).get('name', 'Unknown'),
            'permissions': ADMIN_ROLES.get(user.admin_role, {}).get('permissions', []),
            'scope': {
                'type': ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none'),
                'college_id': user.assigned_college_id,
                'program': user.assigned_program
            },
            'admin_status': user.admin_status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/overview', methods=['GET'])
def get_admin_overview():
    """Get admin dashboard overview"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
        stats = {}

        if user.admin_role == 'super_admin':
            stats['total_students'] = User.query.filter_by(role='student').count()
            stats['total_admins'] = User.query.filter(User.role.in_(['admin', 'super_admin'])).count()
            stats['total_modules'] = Module.query.count()
            stats['total_posts'] = SocialPost.query.count()
        elif scope == 'college' and user.assigned_college_id:
            stats['total_students'] = User.query.filter_by(role='student', college_id=user.assigned_college_id).count()
            stats['total_modules'] = Module.query.filter_by(college_id=user.assigned_college_id).count()
            stats['total_posts'] = SocialPost.query.filter_by(college_id=user.assigned_college_id).count()
        elif scope == 'program' and user.assigned_program:
            stats['total_students'] = User.query.filter_by(role='student', program=user.assigned_program).count()
            stats['total_modules'] = Module.query.filter_by(program=user.assigned_program).count()
            stats['total_posts'] = SocialPost.query.filter_by(program=user.assigned_program).count()

        # Pending approvals
        stats['pending_approvals'] = User.query.filter_by(
            admin_status='pending',
            role='admin'
        ).count()

        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/colleges', methods=['GET'])
def get_admin_colleges():
    """Get colleges for admin management"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        if user.admin_role == 'college_admin' and user.assigned_college_id:
            colleges = College.query.filter_by(id=user.assigned_college_id).all()
        else:
            colleges = College.query.all()

        return jsonify([{
            'id': c.id,
            'code': c.code,
            'name': c.name,
            'description': c.description
        } for c in colleges])
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/programs', methods=['GET'])
def get_admin_programs():
    """Get programs for admin management"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
        query = School.query

        if scope == 'college' and user.assigned_college_id:
            query = query.filter_by(college_id=user.assigned_college_id)

        programs = query.all()

        return jsonify([{
            'id': p.id,
            'code': p.code,
            'name': p.name,
            'college_id': p.college_id
        } for p in programs])
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/modules', methods=['GET'])
def get_admin_modules():
    """Get modules based on admin scope"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
        query = Module.query

        if scope == 'college' and user.assigned_college_id:
            query = query.filter_by(college_id=user.assigned_college_id)
        elif scope == 'program' and user.assigned_program:
            query = query.filter_by(program=user.assigned_program)

        modules = query.order_by(Module.created_at.desc()).all()

        return jsonify([{
            'id': m.id,
            'code': m.module_code,
            'name': m.name,
            'college_id': m.school.college_id if m.school else None,
            'year': m.year_of_study,
            'semester': m.semester.name if m.semester else None,
            'created_at': m.created_at.isoformat()
        } for m in modules])
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/announcements', methods=['GET'])
def get_announcements():
    """Get announcements visible to admin scope"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')

        # Use SQLAlchemy instead of raw sqlite3
        query = Announcement.query

        # Filter based on scope if needed (simplified for now)
        announcements = query.order_by(Announcement.created_at.desc()).limit(50).all()

        result = []
        for a in announcements:
            result.append({
                'id': a.id,
                'title': a.title,
                'content': a.content,
                'scope': a.scope,
                'college_id': a.college_id,
                'program': a.program,
                'year': a.year,
                'created_by': a.created_by,
                'created_at': a.created_at.isoformat() if a.created_at else None
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/announcements', methods=['POST'])
def create_announcement():
    """Create announcement with visibility scope"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        scope = data.get('scope', 'university')
        if scope == 'university' and user.admin_role != 'super_admin':
            return jsonify({'error': 'Only Super Admin can create university-wide announcements'}), 403

        announcement = Announcement(
            title=data.get('title'),
            content=data.get('content'),
            scope=scope,
            college_id=data.get('college_id'),
            program=data.get('program'),
            year=data.get('year'),
            created_by=user.id,
            author_id=user.id # Required by model constraint
        )
        db.session.add(announcement)
        db.session.commit()

        return jsonify({
            'message': 'Announcement created successfully',
            'announcement': {
                'id': announcement.id,
                'title': data.get('title'),
                'scope': scope
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/students/pending', methods=['GET'])
def get_pending_students():
    """Get pending student registrations for review"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
        query = User.query.filter_by(role='student', is_active=False)

        if scope == 'college' and user.assigned_college_id:
            query = query.filter_by(college_id=user.assigned_college_id)
        elif scope == 'program' and user.assigned_program:
            query = query.filter_by(program=user.assigned_program)

        students = query.order_by(User.created_at.desc()).limit(50).all()

        return jsonify([{
            'id': s.id,
            'email': s.email,
            'name': s.name,
            'registration_number': s.registration_number,
            'college_id': s.college_id,
            'program': s.program,
            'year_of_study': s.year_of_study,
            'created_at': s.created_at.isoformat()
        } for s in students])
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/students/<int:student_id>/approve', methods=['POST'])
def approve_student(student_id):
    """Approve a student registration"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        student = User.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        student.is_active = True
        db.session.commit()

        return jsonify({'message': 'Student approved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/students/<int:student_id>/flag', methods=['POST'])
def flag_student(student_id):
    """Flag a student registration"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        student = User.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        student.is_active = False
        student.bio = f"[FLAGGED] {data.get('reason', 'Manual flag')}"
        db.session.commit()

        return jsonify({'message': 'Student flagged for review'})
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/my-programs', methods=['GET'])
def get_my_managed_programs():
    """Get programs managed by the current admin"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
        query = School.query.filter_by(is_active=True)

        if scope == 'college' and user.assigned_college_id:
            query = query.filter_by(college_id=user.assigned_college_id)
        elif scope == 'program' and user.assigned_program:
            # Assuming assigned_program stores the school ID or code
            # For simplicity, let's assume it stores ID as string
            query = query.filter_by(id=int(user.assigned_program))

        programs = query.all()
        return jsonify([{
            'id': p.id,
            'name': p.name,
            'code': p.code,
            'college_id': p.college_id,
            'college_name': p.college.name
        } for p in programs])
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/academic-years/<int:year_id>/archive', methods=['POST'])
def archive_academic_year(year_id):
    """Archive an academic year"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.admin_role != 'super_admin':
            return jsonify({'error': 'Super Admin access required'}), 403

        year = AcademicYear.query.get_or_404(year_id)
        year.is_active = False
        year.is_completed = True
        # In a real system, we might move data to cold storage or mark modules as archived
        db.session.commit()

        return jsonify({'message': 'Academic year archived successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/analytics', methods=['GET'])
def get_admin_analytics_new():
    """Get analytics based on admin scope"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')

        filters = {}
        if scope == 'college' and user.assigned_college_id:
            filters['college_id'] = user.assigned_college_id
        elif scope == 'program' and user.assigned_program:
            filters['program'] = user.assigned_program

        analytics = {}

        # Most discussed courses
        analytics['top_courses'] = db.session.query(
            SocialPost.program,
            db.func.count(SocialPost.id).label('count')
        ).filter_by(**filters).group_by(SocialPost.program).order_by(
            db.func.count(SocialPost.id).desc()
        ).limit(5).all()

        # Most active contributors
        analytics['top_contributors'] = db.session.query(
            SocialPost.user_id,
            SocialPost.user_name,
            db.func.count(SocialPost.id).label('count')
        ).filter_by(**filters).group_by(
            SocialPost.user_id, SocialPost.user_name
        ).order_by(db.func.count(SocialPost.id).desc()).limit(5).all()

        # Engagement metrics
        analytics['total_posts'] = SocialPost.query.filter_by(**filters).count()
        analytics['total_comments'] = SocialComment.query.filter_by(**filters).count()

        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/reports/pending', methods=['GET'])
def get_pending_reports():
    """Get pending content reports"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        reports = ContentReport.query.filter_by(status='pending').order_by(ContentReport.created_at.desc()).limit(20).all()

        result = []
        for r in reports:
            result.append({
                'id': r.id,
                'report_type': r.report_type,
                'content_id': r.content_id,
                'content_type': r.content_type,
                'reason': r.reason,
                'reported_by': r.reported_by,
                'status': r.status,
                'created_at': r.created_at.isoformat() if r.created_at else None
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/admin/reports/<int:report_id>/resolve', methods=['POST'])
def resolve_report(report_id):
    """Resolve a content report"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user = User.query.get(data.get('user_id'))

        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        action = request.get_json().get('action', 'resolved')

        report = ContentReport.query.get_or_404(report_id)
        report.status = action
        report.resolved_by = user.id
        report.resolved_at = datetime.utcnow()
        report.resolution_notes = request.get_json().get('notes', '')

        db.session.commit()

        return jsonify({'message': 'Report resolved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 401



# ==================== HEALTH CHECK ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker/proxy"""
    return jsonify({
        'status': 'healthy',
        'service': 'ur-courses',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# ==================== RUN ====================

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
