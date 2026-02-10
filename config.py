"""
Application Configuration
"""
import os

class Config:
    """Base configuration"""
    # Secret keys
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET = os.environ.get('JWT_SECRET', 'jwt-secret-change-in-production')
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 24  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRES = 7 * 24 * 60 * 60  # 7 days
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI', 
        'sqlite:///ur_courses.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300
    }
    
    # File uploads
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'txt', 'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar'
    }
    
    # Security
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = False
    
    # CORS
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5000',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5000'
    ]
    
    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'
    
    # Use simpler secret for development
    SECRET_KEY = 'dev-secret-key-do-not-use-in-production'
    JWT_SECRET = 'dev-jwt-key-do-not-use-in-production'
    
    # Disable CSRF for API testing
    WTF_CSRF_ENABLED = False
    
    # More permissive CORS
    CORS_ORIGINS = ['*']
    
    # Less restrictive rate limiting
    RATELIMIT_DEFAULT = "1000 per day"


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'
    
    # Enforce security
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    
    # Restrict CORS
    CORS_ORIGINS = [
        'https://ur-courses.ac.rw',
        'https://www.ur-courses.ac.rw'
    ]
    
    # Production rate limiting
    RATELIMIT_DEFAULT = "100 per day"
    
    # Use database for rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')


# Configuration dictionary
config_dict = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
