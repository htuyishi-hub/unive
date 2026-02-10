"""
RESTful API Endpoints for UR Course Management Platform
Hierarchy: College → School → Academic Year → Semester → Module → Documents
"""
import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import (
    db, User, College, School, Module, Document, 
    AcademicYear, Semester, Announcement, Enrollment,
    module_students
)
from auth import log_activity, decode_token, JWT_SECRET, JWT_ALGORITHM
import jwt

api_bp = Blueprint('api', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 
                      'txt', 'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def token_required(f):
    """Decorator for JWT-protected routes"""
    def decorator(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
        
        if not token:
            return jsonify({'error': 'Token missing'}), 401
        
        result = decode_token(token)
        if not result['success']:
            return jsonify({'error': result['error']}), 401
        
        current_user_id = result['payload']['user_id']
        current_api_user = User.query.get(current_user_id)
        
        if not current_api_user:
            return jsonify({'error': 'User not found'}), 401
        
        return f(current_api_user, *args, **kwargs)
    
    decorator.__name__ = f.__name__
    return decorator


def admin_required(f):
    """Decorator for admin-only routes"""
    @token_required
    def decorator(user, *args, **kwargs):
        if not user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        return f(user, *args, **kwargs)
    
    decorator.__name__ = f.__name__
    return decorator


def instructor_or_admin_required(f):
    """Decorator for instructor or admin routes"""
    @token_required
    def decorator(user, *args, **kwargs):
        if not user.is_instructor():
            return jsonify({'error': 'Instructor access required'}), 403
        return f(user, *args, **kwargs)
    
    decorator.__name__ = f.__name__
    return decorator


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    """Get file type category"""
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


# ==================== COLLEGES ====================

@api_bp.route('/colleges', methods=['GET'])
def get_colleges():
    """Get all colleges"""
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


@api_bp.route('/colleges/<int:college_id>', methods=['GET'])
def get_college(college_id):
    """Get college details with schools"""
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


# ==================== SCHOOLS ====================

@api_bp.route('/schools', methods=['GET'])
def get_schools():
    """Get all schools, optionally filtered by college"""
    college_id = request.args.get('college_id')
    query = School.query.filter_by(is_active=True)
    
    if college_id:
        query = query.filter_by(college_id=college_id)
    
    schools = query.all()
    return jsonify({
        'schools': [{
            'id': s.id,
            'code': s.code,
            'name': s.name,
            'college_id': s.college_id,
            'college_name': s.college.name,
            'module_count': s.modules.count()
        } for s in schools]
    }), 200


@api_bp.route('/schools/<int:school_id>', methods=['GET'])
def get_school(school_id):
    """Get school details"""
    school = School.query.get_or_404(school_id)
    return jsonify({
        'school': {
            'id': school.id,
            'code': school.code,
            'name': school.name,
            'college_id': school.college_id,
            'college_name': school.college.name
        }
    }), 200


# ==================== ACADEMIC YEARS ====================

@api_bp.route('/academic-years', methods=['GET'])
def get_academic_years():
    """Get all academic years"""
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


@api_bp.route('/academic-years/active', methods=['GET'])
def get_active_academic_year():
    """Get currently active academic year"""
    year = AcademicYear.query.filter_by(is_active=True).first()
    if not year:
        return jsonify({'error': 'No active academic year'}), 404
    
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


@admin_required
def create_academic_year(user, data):
    """Create new academic year"""
    required = ['year_code', 'name', 'start_date', 'end_date']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} required'}), 400
    
    # Check if exists
    if AcademicYear.query.filter_by(year_code=data['year_code']).first():
        return jsonify({'error': 'Academic year already exists'}), 400
    
    year = AcademicYear(
        year_code=data['year_code'],
        name=data['name'],
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
        is_active=False  # New year starts as inactive
    )
    
    db.session.add(year)
    db.session.commit()
    
    # Add default semesters
    sem1 = Semester(
        academic_year_id=year.id,
        name="Semester 1",
        code=f"{data['year_code'][-2:]}S1",
        start_date=year.start_date,
        end_date=datetime.strptime(f"{year.start_date.year}-01-15", '%Y-%m-%d').date()
    )
    sem2 = Semester(
        academic_year_id=year.id,
        name="Semester 2",
        code=f"{data['year_code'][-2:]}S2",
        start_date=datetime.strptime(f"{year.start_date.year}-01-16", '%Y-%m-%d').date(),
        end_date=year.end_date
    )
    
    db.session.add_all([sem1, sem2])
    db.session.commit()
    
    log_activity(user.id, 'create_academic_year', request.remote_addr)
    
    return jsonify({
        'message': 'Academic year created',
        'academic_year': {
            'id': year.id,
            'year_code': year.year_code,
            'name': year.name
        }
    }), 201


@admin_required
def complete_academic_year(user, year_id):
    """Mark academic year as completed"""
    year = AcademicYear.query.get_or_404(year_id)
    year.is_completed = True
    year.is_active = False
    db.session.commit()
    
    log_activity(user.id, 'complete_academic_year', request.remote_addr)
    
    return jsonify({'message': 'Academic year completed'}), 200


@admin_required
def activate_academic_year(user, year_id):
    """Activate an academic year"""
    # Deactivate current active year
    current = AcademicYear.query.filter_by(is_active=True).first()
    if current:
        current.is_active = False
    
    year = AcademicYear.query.get_or_404(year_id)
    year.is_active = True
    db.session.commit()
    
    log_activity(user.id, 'activate_academic_year', request.remote_addr)
    
    return jsonify({'message': 'Academic year activated'}), 200


# ==================== MODULES ====================

@api_bp.route('/modules', methods=['GET'])
def get_modules():
    """Get modules with filters"""
    # Filters
    school_id = request.args.get('school_id')
    semester_id = request.args.get('semester_id')
    academic_year_id = request.args.get('academic_year_id')
    search = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Module.query.filter_by(is_active=True)
    
    if school_id:
        query = query.filter_by(school_id=school_id)
    if semester_id:
        query = query.filter_by(semester_id=semester_id)
    if academic_year_id:
        # Get modules from the semester of that academic year
        semesters = Semester.query.filter_by(academic_year_id=academic_year_id).all()
        semester_ids = [s.id for s in semesters]
        query = query.filter(Module.semester_id.in_(semester_ids))
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Module.name.ilike(search_term)) | 
            (Module.module_code.ilike(search_term))
        )
    
    pagination = query.order_by(Module.name).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'modules': [{
            'id': m.id,
            'module_code': m.module_code,
            'name': m.name,
            'description': m.description,
            'school_id': m.school_id,
            'school_name': m.school.name,
            'semester_id': m.semester_id,
            'semester_name': m.semester.name,
            'credits': m.credits,
            'lecturer_name': m.lecturer_name,
            'tags': m.get_tags_list(),
            'student_count': m.student_count,
            'document_count': m.document_count,
            'is_enrollment_open': m.is_enrollment_open
        } for m in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@api_bp.route('/modules/<int:module_id>', methods=['GET'])
def get_module(module_id):
    """Get module details"""
    module = Module.query.get_or_404(module_id)
    
    return jsonify({
        'module': {
            'id': module.id,
            'module_code': module.module_code,
            'name': module.name,
            'description': module.description,
            'school_id': module.school_id,
            'school_name': module.school.name,
            'college_id': module.school.college.id,
            'college_name': module.school.college.name,
            'semester_id': module.semester_id,
            'semester_name': module.semester.name,
            'academic_year_id': module.semester.academic_year.id,
            'academic_year': module.semester.academic_year.name,
            'credits': module.credits,
            'lecturer_name': module.lecturer_name,
            'lecturer_email': module.lecturer_email,
            'tags': module.get_tags_list(),
            'module_type': module.module_type,
            'max_students': module.max_students,
            'student_count': module.student_count,
            'is_enrollment_open': module.is_enrollment_open
        },
        'documents': [{
            'id': d.id,
            'title': d.title,
            'file_type': d.file_type,
            'file_size': d.file_size,
            'category': d.category,
            'uploaded_by': d.uploaded_by,
            'uploaded_at': d.created_at.isoformat()
        } for d in module.documents.filter_by(is_published=True).all()]
    }), 200


@instructor_or_admin_required
def create_module(user, data):
    """Create new module"""
    required = ['module_code', 'name', 'school_id', 'semester_id']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} required'}), 400
    
    # Check if module code exists in same school
    existing = Module.query.filter_by(
        school_id=data['school_id'], 
        module_code=data['module_code']
    ).first()
    if existing:
        return jsonify({'error': 'Module code already exists in this school'}), 400
    
    module = Module(
        module_code=data['module_code'],
        name=data['name'],
        description=data.get('description'),
        school_id=data['school_id'],
        semester_id=data['semester_id'],
        credits=data.get('credits', 0),
        lecturer_name=data.get('lecturer_name'),
        lecturer_email=data.get('lecturer_email'),
        tags=data.get('tags', ''),
        module_type=data.get('module_type', 'core'),
        max_students=data.get('max_students', 100)
    )
    
    db.session.add(module)
    db.session.commit()
    
    log_activity(user.id, 'create_module', request.remote_addr)
    
    return jsonify({
        'message': 'Module created',
        'module': {
            'id': module.id,
            'module_code': module.module_code,
            'name': module.name
        }
    }), 201


@instructor_or_admin_required
def update_module(user, module_id, data):
    """Update module"""
    module = Module.query.get_or_404(module_id)
    
    updatable = ['name', 'description', 'credits', 'lecturer_name', 
                 'lecturer_email', 'tags', 'module_type', 'max_students',
                 'is_enrollment_open', 'is_active']
    
    for field in updatable:
        if field in data:
            setattr(module, field, data[field])
    
    db.session.commit()
    
    log_activity(user.id, 'update_module', request.remote_addr)
    
    return jsonify({'message': 'Module updated'}), 200


@instructor_or_admin_required
def delete_module(user, module_id):
    """Soft delete module"""
    module = Module.query.get_or_404(module_id)
    module.is_active = False
    db.session.commit()
    
    log_activity(user.id, 'delete_module', request.remote_addr)
    
    return jsonify({'message': 'Module deleted'}), 200


# ==================== STUDENT ENROLLMENT (One-time selection) ====================

@token_required
def enroll_in_module(user, module_id):
    """Enroll student in module (one-time selection)"""
    module = Module.query.get_or_404(module_id)
    
    # Check if already enrolled
    if user in module.students:
        return jsonify({'error': 'Already enrolled in this module'}), 400
    
    # Check if enrollment is open
    if not module.is_enrollment_open:
        return jsonify({'error': 'Enrollment is not open for this module'}), 400
    
    # Check max students
    if module.student_count >= module.max_students:
        return jsonify({'error': 'Module is full'}), 400
    
    # Enroll student
    module.enroll_student(user)
    
    # Create enrollment record
    enrollment = Enrollment(
        student_id=user.id,
        module_id=module.id,
        academic_year_id=module.semester.academic_year.id
    )
    db.session.add(enrollment)
    db.session.commit()
    
    log_activity(user.id, 'enroll_module', request.remote_addr)
    
    return jsonify({
        'message': 'Successfully enrolled in module',
        'module': {
            'id': module.id,
            'module_code': module.module_code,
            'name': module.name
        }
    }), 200


@token_required
def drop_module(user, module_id):
    """Drop from module"""
    module = Module.query.get_or_404(module_id)
    
    if user not in module.students:
        return jsonify({'error': 'Not enrolled in this module'}), 400
    
    module.remove_student(user)
    
    # Remove enrollment record
    enrollment = Enrollment.query.filter_by(
        student_id=user.id,
        module_id=module.id
    ).first()
    if enrollment:
        enrollment.status = 'dropped'
        db.session.commit()
    
    log_activity(user.id, 'drop_module', request.remote_addr)
    
    return jsonify({'message': 'Successfully dropped from module'}), 200


@token_required
def get_enrolled_modules(user):
    """Get student's enrolled modules"""
    enrolled = Enrollment.query.filter_by(
        student_id=user.id, 
        status='active'
    ).all()
    
    modules = []
    for e in enrolled:
        module = Module.query.get(e.module_id)
        if module:
            modules.append({
                'id': module.id,
                'module_code': module.module_code,
                'name': module.name,
                'school_name': module.school.name,
                'college_name': module.school.college.name,
                'semester': module.semester.name,
                'academic_year': module.semester.academic_year.name,
                'enrolled_at': e.enrolled_at.isoformat(),
                'document_count': module.document_count,
                'student_count': module.student_count
            })
    
    return jsonify({'modules': modules}), 200


@token_required
def get_available_modules(user):
    """Get modules available for enrollment"""
    # Get active academic year
    year = AcademicYear.query.filter_by(is_active=True).first()
    if not year:
        return jsonify({'modules': []}), 200
    
    # Get modules where enrollment is open
    open_modules = Module.query.filter_by(
        is_active=True,
        is_enrollment_open=True
    ).join(Semester).filter(
        Semester.academic_year_id == year.id
    ).all()
    
    # Filter out already enrolled
    enrolled_ids = [m.id for m in user.modules]
    available = [m for m in open_modules if m.id not in enrolled_ids]
    
    return jsonify({
        'modules': [{
            'id': m.id,
            'module_code': m.module_code,
            'name': m.name,
            'description': m.description,
            'school_name': m.school.name,
            'college_name': m.school.college.name,
            'credits': m.credits,
            'lecturer_name': m.lecturer_name,
            'tags': m.get_tags_list(),
            'spots_left': m.max_students - m.student_count
        } for m in available]
    }), 200


# ==================== DOCUMENTS ====================

@api_bp.route('/modules/<int:module_id>/documents', methods=['GET'])
def get_module_documents(module_id):
    """Get documents for a module"""
    module = Module.query.get_or_404(module_id)
    category = request.args.get('category')
    
    query = module.documents.filter_by(is_published=True)
    if category:
        query = query.filter_by(category=category)
    
    documents = query.order_by(Document.created_at.desc()).all()
    
    return jsonify({
        'documents': [{
            'id': d.id,
            'title': d.title,
            'description': d.description,
            'file_type': d.file_type,
            'file_size': d.file_size,
            'category': d.category,
            'download_count': d.download_count,
            'uploaded_at': d.created_at.isoformat()
        } for d in documents]
    }), 200


@instructor_or_admin_required
def upload_document(user, module_id, data, files):
    """Upload document to module"""
    module = Module.query.get_or_404(module_id)
    
    if 'file' not in files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = files['file']
    
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Generate secure filename
    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_filename = f"{module.module_code}_{uuid.uuid4().hex[:8]}.{ext}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    # Save file
    file.save(file_path)
    
    # Get file size
    file_size = os.path.getsize(file_path)
    
    if file_size > MAX_FILE_SIZE:
        os.remove(file_path)
        return jsonify({'error': f'File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit'}), 400
    
    # Create document record
    document = Document(
        title=data.get('title', original_filename),
        description=data.get('description'),
        filename=original_filename,
        file_type=get_file_type(original_filename),
        file_size=file_size,
        file_path=file_path,
        module_id=module.id,
        category=data.get('category', 'general'),
        uploaded_by=user.id
    )
    
    db.session.add(document)
    db.session.commit()
    
    log_activity(user.id, 'upload_document', request.remote_addr)
    
    return jsonify({
        'message': 'Document uploaded successfully',
        'document': {
            'id': document.id,
            'title': document.title,
            'file_type': document.file_type,
            'category': document.category
        }
    }), 201


@instructor_or_admin_required
def delete_document(user, document_id):
    """Delete document"""
    document = Document.query.get_or_404(document_id)
    
    # Delete file
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    db.session.delete(document)
    db.session.commit()
    
    log_activity(user.id, 'delete_document', request.remote_addr)
    
    return jsonify({'message': 'Document deleted'}), 200


@api_bp.route('/documents/<int:document_id>/download', methods=['GET'])
@token_required
def download_document(user, document_id):
    """Download document"""
    document = Document.query.get_or_404(document_id)
    
    if not document.is_published:
        return jsonify({'error': 'Document not available'}), 404
    
    # Check if user has access
    if not user.is_instructor():
        # Students can only download from enrolled modules
        if document.module not in user.modules:
            return jsonify({'error': 'Access denied'}), 403
    
    document.increment_download()
    
    log_activity(user.id, 'download_document', request.remote_addr)
    
    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.filename
    )


# ==================== ADMIN DASHBOARD ====================

@admin_required
def get_admin_stats(user):
    """Get admin dashboard statistics"""
    stats = {
        'users': {
            'total': User.query.count(),
            'students': User.query.filter_by(role='student').count(),
            'instructors': User.query.filter_by(role='instructor').count(),
            'admins': User.query.filter_by(role='admin').count()
        },
        'academic_years': {
            'total': AcademicYear.query.count(),
            'active': AcademicYear.query.filter_by(is_active=True).count(),
            'completed': AcademicYear.query.filter_by(is_completed=True).count()
        },
        'colleges': {
            'total': College.query.count()
        },
        'modules': {
            'total': Module.query.count(),
            'active': Module.query.filter_by(is_active=True).count(),
            'enrollment_open': Module.query.filter_by(is_enrollment_open=True).count()
        },
        'documents': {
            'total': Document.query.count()
        },
        'enrollments': {
            'total': Enrollment.query.count(),
            'active': Enrollment.query.filter_by(status='active').count()
        }
    }
    
    return jsonify({'stats': stats}), 200


@admin_required
def get_all_users(user):
    """Get all users (admin only)"""
    role = request.args.get('role')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    query = User.query
    if role:
        query = query.filter_by(role=role)
    
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'users': [{
            'id': u.id,
            'email': u.email,
            'name': u.name,
            'role': u.role,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat(),
            'module_count': u.modules.count()
        } for u in pagination.items],
        'pagination': {
            'page': page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@admin_required
def update_user_role(user, target_user_id, data):
    """Update user role (admin only)"""
    target_user = User.query.get_or_404(target_user_id)
    new_role = data.get('role')
    
    if new_role not in ['student', 'instructor', 'admin']:
        return jsonify({'error': 'Invalid role'}), 400
    
    target_user.role = new_role
    db.session.commit()
    
    log_activity(user.id, 'update_user_role', request.remote_addr)
    
    return jsonify({'message': 'User role updated'}), 200


# ==================== SEARCH ====================

@api_bp.route('/search', methods=['GET'])
@token_required
def search(user):
    """Global search across modules and documents"""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')  # all, modules, documents
    
    results = {'modules': [], 'documents': []}
    
    if len(query) < 2:
        return jsonify(results), 200
    
    if search_type in ['all', 'modules']:
        # Search modules
        modules = Module.query.filter(
            Module.is_active == True
        ).filter(
            (Module.name.ilike(f'%{query}%')) |
            (Module.module_code.ilike(f'%{query}%'))
        ).limit(20).all()
        
        results['modules'] = [{
            'id': m.id,
            'module_code': m.module_code,
            'name': m.name,
            'school_name': m.school.name,
            'college_name': m.school.college.name,
            'document_count': m.document_count
        } for m in modules]
    
    if search_type in ['all', 'documents']:
        # Search documents
        documents = Document.query.filter(
            Document.is_published == True
        ).filter(
            (Document.title.ilike(f'%{query}%')) |
            (Document.description.ilike(f'%{query}%'))
        ).limit(20).all()
        
        results['documents'] = [{
            'id': d.id,
            'title': d.title,
            'file_type': d.file_type,
            'module_id': d.module_id,
            'module_name': d.module.name,
            'category': d.category
        } for d in documents]
    
    return jsonify(results), 200


# ==================== BROWSER ROUTES ====================

@api_bp.route('/browse/colleges', methods=['GET'])
def browse_colleges():
    """Browse structure: Colleges -> Schools -> Academic Years -> Semesters -> Modules"""
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
                'modules': []
            }
            
            # Get modules by academic year
            year_modules = {}
            for module in school.modules.filter_by(is_active=True).all():
                year_name = module.semester.academic_year.name
                semester_name = module.semester.name
                key = f"{year_name} - {semester_name}"
                
                if key not in year_modules:
                    year_modules[key] = {
                        'academic_year': year_name,
                        'semester': semester_name,
                        'modules': []
                    }
                
                year_modules[key]['modules'].append({
                    'id': module.id,
                    'module_code': module.module_code,
                    'name': module.name,
                    'credits': module.credits,
                    'student_count': module.student_count
                })
            
            school_data['modules_by_year'] = list(year_modules.values())
            college_data['schools'].append(school_data)
        
        result.append(college_data)
    
    return jsonify({'structure': result}), 200
