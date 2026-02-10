# University of Rwanda - Course Management Platform

A comprehensive course management platform for the University of Rwanda with:

- **College → School → Academic Year → Semester → Module** hierarchy
- **Magic Link Authentication** - email-based login without passwords
- **Student enrollment** system (one-time selection)
- **Document management** organized by module/course
- **Admin dashboard** with academic year management

## 🏗️ Architecture

```
College (7)
├── School (multiple per college)
├── School of ICT
├── School of Engineering
└── Academic Year (2024-2025, 2025-2026, etc.)
    └── Semester (S1, S2)
        └── Module (BH8CSC - BSc Computer Science)
            └── Documents (lectures, notes, exams, etc.)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip or poetry

### Installation

```bash
# Clone the repository
cd ur-courses

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start the server
python app.py
```

The server will start at http://localhost:5000

### Default Admin

- **Email**: admin@ur.ac.rw
- **First Login**: Use magic link (enter email, click link in console)

## 🔐 Magic Link Authentication

### How It Works

1. **Enter Email**: User enters their email address
2. **Magic Link Sent**: System generates a one-time login link
3. **Click Link**: User clicks the link to access their dashboard
4. **Session Active**: User stays logged in for 24 hours

### Benefits

- 🔒 **No passwords to remember** or forget
- ✅ **Secure one-time links** that expire in 1 hour
- 📧 **Email verification** built-in
- 🚀 **Instant access** to personalized dashboard

### Email Configuration

For production, configure SMTP in `.env`:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

For development, magic links are printed to the console.

## 📚 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Send magic link to email |
| GET | `/auth/magic-login` | Handle magic link click |
| POST | `/auth/resend-magic-link` | Resend magic link |
| GET | `/auth/me` | Get current user |
| POST | `/auth/logout` | Logout |

### College & School Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/colleges` | List all colleges |
| GET | `/api/colleges/<id>` | College details with schools |
| GET | `/api/schools` | List schools (filter by college) |
| GET | `/api/schools/<id>` | School details |

### Academic Year Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/academic-years` | List all academic years |
| GET | `/api/academic-years/<id>` | Year details with semesters |
| POST | `/api/academic-years` | Create new academic year (admin) |
| POST | `/api/academic-years/<id>/complete` | Mark year as completed |
| POST | `/api/academic-years/<id>/activate` | Activate academic year |

### Module Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/modules` | List modules (with filters) |
| GET | `/api/modules/<id>` | Module details |
| POST | `/api/modules` | Create module (instructor/admin) |
| PUT | `/api/modules/<id>` | Update module |
| DELETE | `/api/modules/<id>` | Delete module |

### Enrollment Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/enroll/<module_id>` | Enroll in module |
| POST | `/api/drop/<module_id>` | Drop from module |
| GET | `/api/enrolled` | Get enrolled modules |
| GET | `/api/available` | Get available modules |

### Document Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/modules/<id>/documents` | List module documents |
| POST | `/api/modules/<id>/documents` | Upload document |
| DELETE | `/api/documents/<id>` | Delete document |
| GET | `/api/documents/<id>/download` | Download document |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/stats` | Dashboard statistics |
| GET | `/api/admin/users` | List all users |
| PUT | `/api/admin/users/<id>/role` | Update user role |

### Browse Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/browse/colleges` | Browse full hierarchy |

## 🔒 JWT Authentication

Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

Tokens expire after 24 hours.

## 📤 Document Categories

Documents can be organized by category:
- `lecture` - Lecture notes and slides
- `assignment` - Assignment sheets
- `exam` - Past exams and solutions
- `notes` - Study notes
- `general` - General materials

## 🏛️ Colleges

1. **CASS** - College of Arts and Social Sciences
2. **CBE** - College of Business and Economics
3. **CAFF** - College of Agriculture and Food Sciences
4. **CE** - College of Education
5. **CMHS** - College of Medicine and Health Sciences
6. **CST** - College of Science and Technology
7. **CVAS** - College of Veterinary and Animal Sciences

## 🛠️ Development

```bash
# Run with debug mode
python app.py

# Run tests
pytest

# Database migrations
alembic init alembic
alembic revision -m "Initial migration"
alembic upgrade head
```

## 🚀 Production Deployment

1. Set `FLASK_ENV=production`
2. Use a production WSGI server (Gunicorn, uWSGI)
3. Set up PostgreSQL database
4. Configure Redis for rate limiting
5. Set up proper SSL/TLS certificates
6. Configure email/SMTP for magic links

```bash
# Example production command
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📄 License

MIT License

## 👥 Authors

- University of Rwanda IT Team
