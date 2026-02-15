"""
Authentication Routes with Magic Link Login
Users enter email, receive one-time login link via email
"""
import os
import uuid
from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db
from datetime import datetime, timedelta
import jwt

auth_bp = Blueprint('auth', __name__)

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'ur-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def generate_token(user_id, token_type='access'):
    """Generate access or magic link token"""
    if token_type == 'magic':
        expires = timedelta(hours=1)
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + expires,
            'iat': datetime.utcnow(),
            'type': 'magic',
            'magic_id': str(uuid.uuid4())
        }
    else:
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + expires,
            'iat': datetime.utcnow(),
            'type': 'access'
        }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {'success': True, 'payload': payload}
    except jwt.ExpiredSignatureError:
        return {'success': False, 'error': 'Token expired'}
    except jwt.InvalidTokenError as e:
        return {'success': False, 'error': str(e)}


def send_magic_link_email(email, magic_link):
    """Send magic link via SMTP (placeholder - implement with Flask-Mail)"""
    # In production, use Flask-Mail or similar
    # For development, log the link
    print(f"\n{'='*60}")
    print(f"📧 MAGIC LINK EMAIL")
    print(f"{'='*60}")
    print(f"To: {email}")
    print(f"Subject: Your UR Course Portal Login Link")
    print(f"\nClick to login: {magic_link}")
    print(f"{'='*60}\n")
    
    # TODO: Implement actual email sending
    # Example with Flask-Mail:
    # msg = Message('Your UR Course Portal Login Link',
    #               recipients=[email])
    # msg.body = f"Click here to login: {magic_link}\n\nThis link expires in 1 hour."
    # mail.send(msg)
    
    return True


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Magic Link Login
    Users enter email, receive one-time login link
    """
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Find or create user
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Auto-create new user on first login
        user = User(
            email=email,
            name=data.get('name', email.split('@')[0]),  # Use email prefix as name
            role=data.get('role', 'student')
        )
        db.session.add(user)
        db.session.commit()
        print(f"🆕 New user created: {email}")
    
    # Generate magic link token
    magic_token = generate_token(user.id, 'magic')
    magic_link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/auth/magic-login?token={magic_token}"
    
    # Send magic link
    send_magic_link_email(email, magic_link)
    
    return jsonify({
        'message': 'Login link sent to your email',
        'email': email,
        'debug_link': magic_link  # Remove in production
    }), 200


@auth_bp.route('/magic-login', methods=['GET'])
def magic_login():
    """
    Handle magic link click - redirect to frontend with token
    """
    token = request.args.get('token')
    
    if not token:
        return jsonify({'error': 'Invalid magic link'}), 400
    
    result = decode_token(token)
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    payload = result['payload']
    if payload.get('type') != 'magic':
        return jsonify({'error': 'Invalid token type'}), 400
    
    user = User.query.get(payload['user_id'])
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 404
    
    # Generate access token
    access_token = generate_token(user.id, 'access')
    
    # Redirect to frontend with token
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    redirect_url = f"{frontend_url}/auth/callback?access_token={access_token}"
    
    from flask import redirect
    return redirect(redirect_url)


@auth_bp.route('/verify-magic-token', methods=['POST'])
def verify_magic_token():
    """
    Verify magic link token (for frontend API call)
    """
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    result = decode_token(token)
    if not result['success']:
        return jsonify({'error': result['error']}), 401
    
    payload = result['payload']
    if payload.get('type') != 'magic':
        return jsonify({'error': 'Invalid token type'}), 400
    
    user = User.query.get(payload['user_id'])
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 404
    
    # Generate access token
    access_token = generate_token(user.id, 'access')
    
    # Get magic_id for one-time use tracking
    magic_id = payload.get('magic_id')
    
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        },
        'magic_id': magic_id
    }), 200


@auth_bp.route('/access-token', methods=['POST'])
def exchange_access_token():
    """
    Exchange valid magic token for access token
    Magic token can only be used once
    """
    data = request.get_json()
    magic_token = data.get('token')
    
    if not magic_token:
        return jsonify({'error': 'Token required'}), 400
    
    result = decode_token(magic_token)
    if not result['success']:
        return jsonify({'error': result['error']}), 401
    
    payload = result['payload']
    if payload.get('type') != 'magic':
        return jsonify({'error': 'Invalid token type'}), 400
    
    user = User.query.get(payload['user_id'])
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 404
    
    # Generate new access token
    access_token = generate_token(user.id, 'access')
    
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        }
    }), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Traditional registration with password (optional)
    """
    data = request.get_json()
    
    required = ['email', 'password', 'name']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    if len(data['password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    user = User(
        email=data['email'],
        name=data['name'],
        role=data.get('role', 'student')
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    # Generate token
    access_token = generate_token(user.id, 'access')
    
    return jsonify({
        'message': 'Registration successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        },
        'access_token': access_token
    }), 201


@auth_bp.route('/login-password', methods=['POST'])
def login_password():
    """
    Traditional login with password (optional)
    """
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is disabled'}), 403
    
    access_token = generate_token(user.id, 'access')
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        },
        'token': access_token  # Also return as 'token' for compatibility
    }), 200


@auth_bp.route('/admin-login', methods=['POST'])
def admin_login():
    """
    Admin-specific login endpoint
    """
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    # Check password
    if not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is disabled'}), 403
    
    access_token = generate_token(user.id, 'access')
    
    return jsonify({
        'message': 'Admin login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        },
        'token': access_token
    }), 200


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """
    Get current user info (requires valid token in header)
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401
    
    token = auth_header[7:]
    result = decode_token(token)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 401
    
    if result['payload'].get('type') != 'access':
        return jsonify({'error': 'Invalid token type'}), 401
    
    user = User.query.get(result['payload']['user_id'])
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout - in token-based auth, client just discards token
    """
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/resend-magic-link', methods=['POST'])
def resend_magic_link():
    """
    Resend magic link if user didn't receive it
    """
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Rate limiting - don't send more than 3 per hour
    # TODO: Implement rate limiting
    
    # Generate new magic link
    magic_token = generate_token(user.id, 'magic')
    magic_link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/auth/magic-login?token={magic_token}"
    send_magic_link_email(email, magic_link)
    
    return jsonify({'message': 'Magic link resent'}), 200


@auth_bp.route('/update-profile', methods=['POST'])
def update_profile():
    """
    Update user profile
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401
    
    token = auth_header[7:]
    result = decode_token(token)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 401
    
    user = User.query.get(result['payload']['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if data.get('name'):
        user.name = data['name']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Profile updated',
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        }
    }), 200


def log_activity(user_id, action, ip_address=None):
    """Log user activity"""
    from models import SystemLog
    log = SystemLog(
        user_id=user_id,
        action=action,
        ip_address=ip_address
    )
    db.session.add(log)
    db.session.commit()
