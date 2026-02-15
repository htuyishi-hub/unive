"""
UR Hub Admin Module
Comprehensive role-based admin dashboard with:
- Role hierarchy: Super Admin, College Admin, Program Admin, Faculty Moderator, Academic Reviewer
- Module upload with academic path selection
- Announcements with visibility scope
- Student onboarding review
- Governance and moderation
- Knowledge consolidation
- Analytics
"""

from functools import wraps
from flask import Blueprint, request, jsonify, send_from_directory
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# ==================== ROLE DEFINITIONS ====================

ADMIN_ROLES = {
    'super_admin': {
        'name': 'Super Admin',
        'permissions': ['all'],
        'scope': 'university'
    },
    'college_admin': {
        'name': 'College Admin',
        'permissions': ['manage_college', 'manage_programs', 'upload_modules', 'announcements', 'review_students', 'governance', 'analytics'],
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

# ==================== DECORATORS ====================

def require_admin_role(*allowed_roles):
    """Decorator to require specific admin roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'error': 'Authentication required'}), 401
            
            from app import jwt, User, app
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

# ==================== ADMIN AUTH ====================

@admin_bp.route('/api/admin/register', methods=['POST'])
def register_admin():
    """Admin registration with onboarding"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    admin_role = data.get('admin_role', 'program_admin')  # Default role
    assigned_college_id = data.get('assigned_college_id')
    assigned_program = data.get('assigned_program')
    reg_number = data.get('registration_number')
    full_name = data.get('full_name')
    
    # Validate role
    if admin_role not in ADMIN_ROLES:
        return jsonify({'error': 'Invalid admin role'}), 400
    
    # Check if already registered admin
    from app import User, db, ADMIN_EMAILS, ADMIN_PASSWORD
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'error': 'User must be registered first'}), 400
    
    # Check password
    if email not in ADMIN_EMAILS or password != ADMIN_PASSWORD:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Update user as admin
    user.role = 'admin'
    user.admin_role = admin_role
    user.assigned_college_id = assigned_college_id
    user.assigned_program = assigned_program
    user.admin_status = 'pending'  # Requires approval
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

# ==================== ADMIN PROFILE ====================

@admin_bp.route('/api/admin/profile', methods=['GET'])
@require_admin_role()
def get_admin_profile(user):
    """Get current admin profile with scope"""
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

# ==================== DASHBOARD OVERVIEW ====================

@admin_bp.route('/api/admin/overview', methods=['GET'])
@require_admin_role()
def get_overview(user):
    """Get admin dashboard overview based on role"""
    from app import User, Module, SocialPost, db, College
    
    scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
    
    stats = {}
    
    if scope in ['university', 'college']:
        # Can see college-level stats
        if user.assigned_college_id:
            stats['total_students'] = User.query.filter_by(
                role='student', 
                college_id=user.assigned_college_id
            ).count()
            stats['total_modules'] = Module.query.filter_by(
                college_id=user.assigned_college_id
            ).count()
        else:
            stats['total_students'] = User.query.filter_by(role='student').count()
            stats['total_modules'] = Module.query.count()
            stats['total_colleges'] = College.query.count()
    
    if scope in ['program', 'college', 'university']:
        if user.assigned_program:
            stats['total_posts'] = SocialPost.query.filter_by(
                program=user.assigned_program
            ).count()
        else:
            stats['total_posts'] = SocialPost.query.count()
    
    # Pending approvals
    stats['pending_approvals'] = User.query.filter_by(
        admin_status='pending',
        role='admin'
    ).count()
    
    # Recent activity
    stats['recent_posts'] = SocialPost.query.order_by(
        SocialPost.created_at.desc()
    ).limit(5).all()
    
    return jsonify(stats)

# ==================== MODULE MANAGEMENT ====================

@admin_bp.route('/api/admin/modules', methods=['GET'])
@require_admin_role('super_admin', 'college_admin', 'program_admin')
def get_admin_modules(user):
    from app import Module, School
    
    scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
    query = Module.query
    
    if scope == 'college' and user.assigned_college_id:
        query = query.join(School).filter(School.college_id == user.assigned_college_id)
    elif scope == 'program' and user.assigned_program:
        query = query.filter(Module.program == user.assigned_program)
    
    modules = query.order_by(Module.created_at.desc()).all()
    
    return jsonify([{
        'id': m.id,
        'module_code': m.module_code,
        'name': m.name,
        'school_id': m.school_id,
        'school_name': m.school.name if m.school else None,
        'semester_id': m.semester_id,
        'semester_name': m.semester.name if m.semester else None,
        'program': m.program,
        'year_of_study': m.year_of_study,
        'external_link': m.external_link,
        'created_at': m.created_at.isoformat() if m.created_at else None
    } for m in modules])

@admin_bp.route('/api/admin/modules', methods=['POST'])
@require_admin_role('super_admin', 'college_admin', 'program_admin')
def upload_module(user):
    from app import Module, db
    
    # Handle both JSON and FormData
    content_type = request.content_type or ''
    if 'multipart/form-data' in content_type:
        data = request.form
    else:
        data = request.get_json() or {}
    
    # Get form data
    college_id = data.get('college_id')
    school_id = data.get('school_id')
    year_of_study = data.get('year_of_study')
    semester_id = data.get('semester_id')
    
    # Validate scope
    scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
    if scope == 'college' and user.assigned_college_id:
        if str(college_id) != str(user.assigned_college_id):
            return jsonify({'error': 'Access denied to this college'}), 403
    
    # Parse IDs
    try:
        if school_id: school_id = int(school_id)
        if semester_id: semester_id = int(semester_id)
        if year_of_study: year_of_study = int(year_of_study)
    except (ValueError, TypeError):
        pass

    try:
        # Create module with correct field mappings
        module = Module(
            module_code=data.get('course_code'),
            name=data.get('course_name'),
            description=data.get('description'),
            lecturer_name=data.get('lecturer_name'),
            module_type=data.get('module_type', 'Lecture Notes'),
            school_id=school_id,
            semester_id=semester_id,
            program=data.get('program_name'),
            year_of_study=year_of_study,
            external_link=data.get('external_link')
        )
        
        db.session.add(module)
        db.session.commit()
        
        return jsonify({
            'message': 'Module uploaded successfully',
            'module': {
                'id': module.id,
                'module_code': module.module_code,
                'name': module.name
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== ANNOUNCEMENTS ====================

@admin_bp.route('/api/admin/announcements', methods=['GET'])
@require_admin_role()
def get_announcements(user):
    """Get announcements visible to admin scope"""
    from app import Announcement
    from sqlalchemy import or_
    
    scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
    query = Announcement.query
    
    # Filter by scope
    if scope == 'college' and user.assigned_college_id:
        query = query.filter(
            or_(
                Announcement.scope.in_(['university', 'college']),
                (Announcement.college_id == user.assigned_college_id) | (Announcement.college_id == None)
            )
        )
    elif scope == 'program' and user.assigned_program:
        query = query.filter(
            or_(
                Announcement.scope.in_(['university', 'college', 'program', 'year']),
                (Announcement.program == user.assigned_program) | 
                (Announcement.program == None)
            )
        )
    
    announcements = query.order_by(Announcement.created_at.desc()).all()
    
    return jsonify([{
        'id': a.id,
        'title': a.title,
        'content': a.content,
        'scope': a.scope,
        'college_id': a.college_id,
        'program': a.program,
        'year': a.year if hasattr(a, 'year') else None,
        'created_by': a.created_by,
        'created_at': a.created_at.isoformat()
    } for a in announcements])

@admin_bp.route('/api/admin/announcements', methods=['POST'])
@require_admin_role()
def create_announcement(user):
    """Create announcement with visibility scope"""
    from app import Announcement, db
    
    data = request.get_json()
    
    # Validate scope
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
        author_id=user.id
    )
    
    db.session.add(announcement)
    db.session.commit()
    
    return jsonify({
        'message': 'Announcement created successfully',
        'announcement': {
            'id': announcement.id,
            'title': announcement.title,
            'scope': announcement.scope
        }
    })

# ==================== STUDENT ONBOARDING REVIEW ====================

@admin_bp.route('/api/admin/students/pending', methods=['GET'])
@require_admin_role('super_admin', 'college_admin', 'program_admin', 'academic_reviewer')
def get_pending_students(user):
    """Get pending student registrations for review"""
    from app import User, db
    
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

@admin_bp.route('/api/admin/students/<int:student_id>/approve', methods=['POST'])
@require_admin_role('super_admin', 'college_admin', 'program_admin', 'academic_reviewer')
def approve_student(user, student_id):
    """Approve a student registration"""
    from app import User, db
    
    student = User.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    student.is_active = True
    db.session.commit()
    
    return jsonify({'message': 'Student approved successfully'})

@admin_bp.route('/api/admin/students/<int:student_id>/flag', methods=['POST'])
@require_admin_role('super_admin', 'college_admin', 'program_admin', 'academic_reviewer')
def flag_student(user, student_id):
    """Flag a student registration for review"""
    from app import User, db
    
    data = request.get_json()
    student = User.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    student.is_active = False
    student.bio = f"[FLAGGED] {data.get('reason', 'Manual flag')}"
    db.session.commit()
    
    return jsonify({'message': 'Student flagged for review'})

# ==================== GOVERNANCE & MODERATION ====================

@admin_bp.route('/api/admin/reports/pending', methods=['GET'])
@require_admin_role('super_admin', 'college_admin', 'program_admin', 'faculty_moderator')
def get_pending_reports(user):
    """Get pending content reports"""
    from app import ContentReport, db
    
    reports = ContentReport.query.filter_by(status='pending').order_by(
        ContentReport.created_at.desc()
    ).limit(20).all()
    
    return jsonify([{
        'id': r.id,
        'report_type': r.report_type,
        'content_id': r.content_id,
        'content_type': r.content_type,
        'reason': r.reason,
        'reported_by': r.reported_by,
        'created_at': r.created_at.isoformat()
    } for r in reports])

@admin_bp.route('/api/admin/reports/<int:report_id>/resolve', methods=['POST'])
@require_admin_role('super_admin', 'college_admin', 'program_admin', 'faculty_moderator')
def resolve_report(user, report_id):
    """Resolve a content report"""
    from app import ContentReport, db
    
    data = request.get_json()
    report = ContentReport.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    report.status = data.get('action', 'resolved')
    report.resolved_by = user.id
    report.resolved_at = datetime.utcnow()
    report.resolution_notes = data.get('notes', '')
    db.session.commit()
    
    return jsonify({'message': 'Report resolved successfully'})

# ==================== KNOWLEDGE CONSOLIDATION ====================

@admin_bp.route('/api/admin/knowledge/merge', methods=['POST'])
@require_admin_role('super_admin', 'college_admin', 'program_admin', 'faculty_moderator')
def merge_posts():
    """Merge duplicate posts into a master thread"""
    from app import SocialPost, db
    
    data = request.get_json()
    post_ids = data.get('post_ids', [])
    master_title = data.get('master_title')
    
    posts = SocialPost.query.filter(SocialPost.id.in_(post_ids)).all()
    
    # Create master post
    master = SocialPost(
        content=data.get('master_content'),
        program=data.get('program'),
        is_knowledge_article=True,
        created_by=data.get('created_by')
    )
    
    db.session.add(master)
    
    # Mark others as merged
    for post in posts:
        post.is_merged = True
        post.merged_into = master.id
    
    db.session.commit()
    
    return jsonify({
        'message': 'Posts merged successfully',
        'master_post_id': master.id
    })

# ==================== ANALYTICS ====================

@admin_bp.route('/api/admin/analytics', methods=['GET'])
@require_admin_role()
def get_analytics(user):
    """Get analytics based on admin scope"""
    from app import User, SocialPost, Module, SocialComment, db, College
    
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

# ==================== COLLEGE & PROGRAM MANAGEMENT ====================

@admin_bp.route('/api/admin/colleges', methods=['GET'])
@require_admin_role('super_admin', 'college_admin')
def get_colleges_admin(user):
    """Get colleges for admin management"""
    from app import College
    
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

@admin_bp.route('/api/admin/programs', methods=['GET'])
@require_admin_role('super_admin', 'college_admin', 'program_admin')
def get_programs_admin(user):
    """Get programs for admin management"""
    from app import School
    
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

# ==================== SETTINGS ====================

@admin_bp.route('/api/admin/settings', methods=['GET'])
@require_admin_role()
def get_admin_settings(user):
    """Get admin settings"""
    from app import db
    
    return jsonify({
        'admin_role': user.admin_role,
        'admin_status': user.admin_status,
        'assigned_college_id': user.assigned_college_id,
        'assigned_program': user.assigned_program
    })

@admin_bp.route('/api/admin/settings', methods=['PUT'])
@require_admin_role()
def update_admin_settings(user):
    """Update admin settings"""
    from app import db
    
    data = request.get_json()
    
    if 'notification_preferences' in data:
        user.notification_preferences = data['notification_preferences']
    
    db.session.commit()
    
    return jsonify({'message': 'Settings updated successfully'})
