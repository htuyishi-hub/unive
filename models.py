"""
Database Models for University of Rwanda Course Management Platform
Restructured for: College → School → Academic Year → Module → Documents
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association table for Many-to-Many relationship between Modules and Students
module_students = db.Table('module_students',
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('module_id', db.Integer, db.ForeignKey('module.id'), primary_key=True),
    db.Column('enrolled_at', db.DateTime, default=datetime.utcnow),
    db.Column('status', db.String(20), default='active')  # active, completed, dropped
)

class User(UserMixin, db.Model):
    """User model with Google OAuth support"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(256))
    google_id = db.Column(db.String(100), unique=True, index=True)
    role = db.Column(db.String(20), default='student')  # student, instructor, admin
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Academic info
    college_code = db.Column(db.String(20))
    program_code = db.Column(db.String(50))
    program_name = db.Column(db.String(200))
    year_of_study = db.Column(db.Integer, default=1)
    registration_number = db.Column(db.String(50))
    
    # Profile
    bio = db.Column(db.Text)
    profile_photo = db.Column(db.String(500))
    preferences = db.Column(db.Text)  # JSON preferences
    
    # Knowledge Commons specific
    reputation = db.Column(db.Integer, default=0)
    is_verified_lecturer = db.Column(db.Boolean, default=False)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy='dynamic')
    uploaded_documents = db.relationship('Document', backref='uploader', lazy='dynamic')
    announcements = db.relationship('Announcement', backref='author', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_instructor(self):
        return self.role in ['instructor', 'admin']
    
    def get_reputation_rank(self):
        """Get reputation rank title"""
        score = self.reputation or 0
        if score >= 1000:
            return 'Distinguished Scholar'
        elif score >= 500:
            return 'Senior Contributor'
        elif score >= 200:
            return 'Active Scholar'
        elif score >= 50:
            return 'Promising Member'
        else:
            return 'New Contributor'
    
    def __repr__(self):
        return f'<User {self.email}>'


class AcademicYear(db.Model):
    """Academic Year model - admins can create new academic years"""
    id = db.Column(db.Integer, primary_key=True)
    year_code = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "2025-2026"
    name = db.Column(db.String(100), nullable=False)  # e.g., "Academic Year 2025-2026"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    semesters = db.relationship('Semester', backref='academic_year', lazy='dynamic')
    
    def __repr__(self):
        return f'<AcademicYear {self.year_code}>'
    
    @property
    def duration(self):
        return f"{self.start_date.strftime('%B %d, %Y')} - {self.end_date.strftime('%B %d, %Y')}"


class Semester(db.Model):
    """Semester within an Academic Year"""
    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Semester 1", "Semester 2"
    code = db.Column(db.String(20), nullable=False)  # e.g., "S1", "S2"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    modules = db.relationship('Module', backref='semester', lazy='dynamic')
    
    def __repr__(self):
        return f'<Semester {self.code}>'


class College(db.Model):
    """College model - top level organization"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "CASS", "CBE"
    name = db.Column(db.String(200), nullable=False)  # e.g., "College of Arts and Social Sciences"
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    schools = db.relationship('School', backref='college', lazy='dynamic')
    
    def __repr__(self):
        return f'<College {self.code}>'


class School(db.Model):
    """School model - under College"""
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    code = db.Column(db.String(20), nullable=False)  # e.g., "SICT" for School of ICT
    name = db.Column(db.String(200), nullable=False)  # e.g., "School of ICT"
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    modules = db.relationship('Module', backref='school', lazy='dynamic')
    
    def __repr__(self):
        return f'<School {self.code}>'


class Module(db.Model):
    """Module/Course model - main learning unit"""
    id = db.Column(db.Integer, primary_key=True)
    module_code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., "BH8CSC"
    name = db.Column(db.String(300), nullable=False)  # e.g., "BSc (Hons) in Computer Science"
    description = db.Column(db.Text)
    
    # Foreign Keys
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semester.id'), nullable=False)
    
    # Module Details
    credits = db.Column(db.Integer, default=0)
    lecturer_name = db.Column(db.String(200))
    lecturer_email = db.Column(db.String(120))
    tags = db.Column(db.String(500))  # Comma-separated tags: "Core, Theory, Practical"
    module_type = db.Column(db.String(50), default='core')  # core, elective, compulsory
    
    # Enrollment Settings
    max_students = db.Column(db.Integer, default=100)
    is_enrollment_open = db.Column(db.Boolean, default=False)
    
    # Legacy fields (for backward compatibility with admin.py)
    # These fields may be used by older admin interfaces
    program = db.Column(db.String(200))  # Program name (legacy)
    year_of_study = db.Column(db.Integer)  # Year of study (legacy)
    external_link = db.Column(db.String(500))  # External link (legacy)
    year = db.Column(db.Integer)  # Shortcut for year_of_study (legacy)
    semester = db.Column(db.String(50))  # Semester name (legacy)
    code = db.Column(db.String(50))  # Module code alias (legacy)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = db.relationship('Document', backref='module', lazy='dynamic')
    students = db.relationship('User', secondary=module_students, 
                               backref=db.backref('modules', lazy='dynamic'),
                               lazy='subquery')
    announcements = db.relationship('Announcement', backref='module', lazy='dynamic')
    
    # Composite unique constraint
    __table_args__ = (
        db.UniqueConstraint('school_id', 'module_code', name='_school_module_uc'),
    )
    
    def __repr__(self):
        return f'<Module {self.module_code}: {self.name}>'
    
    @property
    def student_count(self):
        return len(self.students)
    
    @property
    def document_count(self):
        return self.documents.count()
    
    def enroll_student(self, student):
        """Enroll a student in this module (one-time selection)"""
        if student not in self.students:
            self.students.append(student)
            db.session.commit()
            return True
        return False
    
    def remove_student(self, student):
        """Remove a student from this module"""
        if student in self.students:
            self.students.remove(student)
            db.session.commit()
            return True
        return False
    
    def get_tags_list(self):
        return [t.strip() for t in self.tags.split(',')] if self.tags else []


class Document(db.Model):
    """Document model - uploaded materials organized by module"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # pdf, docx, xlsx, pptx, txt, etc.
    file_size = db.Column(db.Integer)  # Size in bytes
    file_path = db.Column(db.String(500), nullable=False)
    
    # Organization
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    category = db.Column(db.String(50), default='general')  # lecture, assignment, notes, exam, etc.
    
    # Metadata
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_published = db.Column(db.Boolean, default=True)
    download_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Document {self.title}>'
    
    @property
    def formatted_size(self):
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
    def increment_download(self):
        self.download_count += 1
        db.session.commit()


class Announcement(db.Model):
    """Announcements for modules"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Announcement {self.title}>'


class Enrollment(db.Model):
    """Student enrollment records"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, completed, dropped, expelled
    
    grade = db.Column(db.Float, nullable=True)
    comments = db.Column(db.Text)
    
    # Unique constraint for student-module-year combination
    __table_args__ = (
        db.UniqueConstraint('student_id', 'module_id', 'academic_year_id', 
                          name='_student_module_year_uc'),
    )
    
    def __repr__(self):
        return f'<Enrollment {self.student_id} - {self.module_id}>'


class SystemLog(db.Model):
    """System activity logs"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Log {self.action}>'


# Database initialization functions
def init_academic_years(db):
    """Initialize default academic years"""
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
    
    for year in years:
        existing = AcademicYear.query.filter_by(year_code=year.year_code).first()
        if not existing:
            db.session.add(year)
    
    db.session.commit()
    
    # Add semesters for active year
    active_year = AcademicYear.query.filter_by(is_active=True).first()
    if active_year:
        semesters = [
            Semester(
                academic_year_id=active_year.id,
                name="Semester 1",
                code="S1",
                start_date=active_year.start_date,
                end_date=datetime(current_year, 1, 15)
            ),
            Semester(
                academic_year_id=active_year.id,
                name="Semester 2",
                code="S2",
                start_date=datetime(current_year, 1, 16),
                end_date=active_year.end_date
            ),
        ]
        for sem in semesters:
            existing = Semester.query.filter_by(code=sem.code, academic_year_id=active_year.id).first()
            if not existing:
                db.session.add(sem)
        db.session.commit()


def init_colleges(db):
    """Initialize UR colleges"""
    colleges = [
        College(code="CASS", name="College of Arts and Social Sciences",
                description="Arts, Humanities, and Social Sciences programs"),
        College(code="CBE", name="College of Business and Economics",
                description="Business and Economics programs"),
        College(code="CAFF", name="College of Agriculture and Food Sciences",
                description="Agriculture, Food Science, and related programs"),
        College(code="CE", name="College of Education",
                description="Education and Teacher Training programs"),
        College(code="CMHS", name="College of Medicine and Health Sciences",
                description="Medical and Health Sciences programs"),
        College(code="CST", name="College of Science and Technology",
                description="Science, Technology, and Engineering programs"),
        College(code="CVAS", name="College of Veterinary and Animal Sciences",
                description="Veterinary and Animal Sciences programs"),
    ]
    
    for college in colleges:
        existing = College.query.filter_by(code=college.code).first()
        if not existing:
            db.session.add(college)
    
    db.session.commit()


def init_schools(db):
    """Initialize schools under each college"""
    schools = [
        # CASS Schools
        School(college_id=1, code="SAH", name="School of Arts and Humanities"),
        School(college_id=1, code="SSH", name="School of Social Sciences"),
        
        # CBE Schools
        School(college_id=2, code="SOB", name="School of Business"),
        School(college_id=2, code="SOE", name="School of Economics"),
        
        # CAFF Schools
        School(college_id=3, code="SAG", name="School of Agriculture"),
        School(college_id=3, code="SFS", name="School of Food Sciences"),
        
        # CE Schools
        School(college_id=4, code="STE", name="School of Teacher Education"),
        
        # CMHS Schools
        School(college_id=5, code="SMED", name="School of Medicine"),
        School(college_id=5, code="SNUR", name="School of Nursing"),
        
        # CST Schools
        School(college_id=6, code="SICT", name="School of ICT"),
        School(college_id=6, code="SEN", name="School of Engineering"),
        School(college_id=6, code="SNS", name="School of Natural Sciences"),
        
        # CVAS Schools
        School(college_id=7, code="SVS", name="School of Veterinary Sciences"),
    ]
    
    for school in schools:
        existing = School.query.filter_by(code=school.code).first()
        if not existing:
            db.session.add(school)
    
    db.session.commit()


def create_default_admin(db):
    """Create default admin user"""
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
        print("Default admin created: admin@ur.ac.rw / password123")
    else:
        # Ensure admin has password set
        if not admin.password_hash:
            admin.set_password('password123')
            db.session.commit()
            print("Admin password reset to: password123")


# ==================== KNOWLEDGE COMMONS MODELS ====================

class KnowledgePost(db.Model):
    """Knowledge Commons posts - structured intellectual discussions"""
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Post content
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(20), default='insight')  # question, explanation, resource, insight
    
    # Academic categorization
    faculty_code = db.Column(db.String(20))  # CASS, CBE, etc.
    course_code = db.Column(db.String(50))
    course_name = db.Column(db.String(200))
    tags = db.Column(db.String(500))  # Comma-separated
    
    # Moderation and quality
    is_anonymous = db.Column(db.Boolean, default=False)
    is_flagged = db.Column(db.Boolean, default=False)
    quality_score = db.Column(db.Float, default=0.0)
    
    # Engagement metrics
    likes = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = db.relationship('User', backref='knowledge_posts')
    answers = db.relationship('KnowledgeAnswer', backref='post', lazy='dynamic')
    likes_relation = db.relationship('KnowledgePostLike', backref='post', lazy='dynamic')
    
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
            'answers_count': self.answers.count(),
            'created_at': self.created_at.isoformat(),
            'quality_score': self.quality_score
        }


class KnowledgePostLike(db.Model):
    """Likes on Knowledge Commons posts"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('knowledge_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('post_id', 'user_id', name='_post_user_like_uc'),
    )


class KnowledgeAnswer(db.Model):
    """Answers/explanations to Knowledge Commons posts"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('knowledge_post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    content = db.Column(db.Text, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)  # Verified by instructor/admin
    helpful_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = db.relationship('User', backref='knowledge_answers')
    helpfuls = db.relationship('HelpfulAnswer', backref='answer', lazy='dynamic')
    
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
    """Users marking answers as helpful"""
    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('knowledge_answer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('answer_id', 'user_id', name='_answer_user_helpful_uc'),
    )


class UserFollow(db.Model):
    """User follows for activity feed"""
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('follower_id', 'following_id', name='_user_follow_uc'),
    )
    
    # Relationships
    follower = db.relationship('User', foreign_keys=[follower_id], 
                               backref=db.backref('following', lazy='dynamic'))
    following = db.relationship('User', foreign_keys=[following_id],
                                 backref=db.backref('followers', lazy='dynamic'))
