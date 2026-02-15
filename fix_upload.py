#!/usr/bin/env python3
"""
Fix for the module upload endpoint to handle FormData (multipart/form-data)
The issue is that the frontend sends FormData but the backend expects JSON.
"""

import re

# Read the app.py file
with open('app.py', 'r') as f:
    content = f.read()

# The old create_module function (first occurrence around line 3602)
old_create_module1 = '''@app.route('/api/admin/modules', methods=['POST'])
def create_module():
    """Create a new module"""
    user = get_current_user()
    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()

    # Check if module code exists
    existing = Module.query.filter_by(module_code=data.get('module_code')).first()
    if existing:
        return jsonify({'error': 'Module code already exists'}), 400

    module = Module(
        module_code=data.get('module_code'),
        name=data.get('name'),
        description=data.get('description'),
        school_id=data.get('school_id'),
        semester_id=data.get('semester_id'),
        credits=data.get('credits', 0),
        lecturer_name=data.get('lecturer_name'),
        lecturer_email=data.get('lecturer_email'),
        tags=','.join(data.get('tags', [])),
        module_type=data.get('module_type', 'core'),
        max_students=data.get('max_students', 100),
        is_enrollment_open=data.get('is_enrollment_open', False)
    )
    db.session.add(module)
    db.session.commit()

    return jsonify({'message': 'Module created', 'id': module.id}), 201'''

# The new create_module function with FormData support
new_create_module = '''@app.route('/api/admin/modules', methods=['POST'])
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

    return jsonify({'message': 'Module created successfully', 'id': module.id}), 201'''

# Replace the first occurrence
content = content.replace(old_create_module1, new_create_module, 1)

# Now the second occurrence (around line 5491) - need to find and replace it too
# This one is slightly different - it's in the admin blueprint section
old_create_module2 = '''@app.route('/api/admin/modules', methods=['POST'])
def upload_module():
    """Upload module with academic path selection"""
    from app import Module, College, AcademicYear, db
    
    data = request.get_json()
    
    # Validate academic path
    college_id = data.get('college_id')
    program_code = data.get('program_code')
    year_of_study = data.get('year_of_study')
    semester = data.get('semester')
    academic_year_id = data.get('academic_year_id')
    
    # Validate scope
    scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
    if scope == 'college' and user.assigned_college_id != college_id:
        return jsonify({'error': 'Access denied to this college'}), 403
    if scope == 'program' and user.assigned_program != program_code:
        return jsonify({'error': 'Access denied to this program'}), 403
    
    module = Module(
        code=data.get('course_code'),
        name=data.get('course_name'),
        description=data.get('description'),
        lecturer=data.get('lecturer_name'),
        module_type=data.get('module_type', 'Lecture Notes'),
        college_id=college_id,
        program=program_code,
        year=year_of_study,
        semester=semester,
        academic_year_id=academic_year_id,
        created_by=user.id
    )
    
    db.session.add(module)
    db.session.commit()
    
    return jsonify({
        'message': 'Module uploaded successfully',
        'module': {
            'id': module.id,
            'code': module.code,
            'name': module.name
        }
    })'''

new_upload_module = '''@app.route('/api/admin/modules', methods=['POST'])
def upload_module():
    """Upload module with academic path selection and optional file upload"""
    from app import Module, College, AcademicYear, db
    
    # Check content type to handle both JSON and FormData
    content_type = request.content_type or ''
    
    if 'multipart/form-data' in content_type:
        # Handle FormData (file upload)
        data = request.form
        file = request.files.get('file')
    else:
        # Handle JSON
        data = request.get_json()
        file = None
    
    # Validate academic path
    college_id = data.get('college_id')
    program_code = data.get('program_code') or data.get('program_name')
    year_of_study = data.get('year_of_study')
    semester = data.get('semester')
    academic_year_id = data.get('academic_year_id')
    
    # Get course info
    course_code = data.get('course_code')
    course_name = data.get('course_name')
    description = data.get('description')
    lecturer_name = data.get('lecturer_name')
    module_type = data.get('module_type', 'Lecture Notes')
    
    # Validate required fields
    if not course_code or not course_name:
        return jsonify({'error': 'Course code and name are required'}), 400
    
    # Validate scope
    scope = ADMIN_ROLES.get(user.admin_role, {}).get('scope', 'none')
    if scope == 'college' and user.assigned_college_id and int(user.assigned_college_id) != int(college_id):
        return jsonify({'error': 'Access denied to this college'}), 403
    if scope == 'program' and user.assigned_program and user.assigned_program != program_code:
        return jsonify({'error': 'Access denied to this program'}), 403
    
    # Parse IDs
    try:
        if college_id:
            college_id = int(college_id)
        if year_of_study:
            year_of_study = int(year_of_study)
        if academic_year_id:
            academic_year_id = int(academic_year_id)
    except (ValueError, TypeError):
        pass
    
    # Get school_id from program_code (school code)
    school_id = None
    if program_code:
        school = School.query.filter_by(code=program_code).first()
        if school:
            school_id = school.id
    
    # Get semester_id from academic_year_id if not provided
    semester_id = data.get('semester_id')
    if not semester_id and academic_year_id:
        semester = Semester.query.filter_by(academic_year_id=academic_year_id, name='Semester 1').first()
        if semester:
            semester_id = semester.id
    
    module = Module(
        module_code=course_code,
        name=course_name,
        description=description,
        lecturer_name=lecturer_name,
        module_type=module_type,
        school_id=school_id,
        semester_id=semester_id,
        program=program_code,
        year_of_study=year_of_study,
        external_link=data.get('external_link')
    )
    
    db.session.add(module)
    db.session.flush()
    
    # Handle file upload if present
    if file and file.filename:
        original_filename = secure_filename(file.filename)
        ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        unique_filename = f"{course_code}_{uuid.uuid4().hex[:8]}.{ext}"
        
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
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
    
    return jsonify({
        'message': 'Module uploaded successfully',
        'module': {
            'id': module.id,
            'code': module.module_code,
            'name': module.name
        }
    })'''

# Replace the second occurrence
content = content.replace(old_create_module2, new_upload_module)

# Write the fixed content back
with open('app.py', 'w') as f:
    f.write(content)

print("✅ Fixed the create_module and upload_module functions!")
print("The endpoints now handle both JSON and FormData (multipart/form-data) requests")

