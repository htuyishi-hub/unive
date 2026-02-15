# Deployment Guide - Render

## Why Render?

- ✅ Free tier available
- ✅ Easy GitHub integration
- ✅ PostgreSQL included
- ✅ Docker support built-in
- ✅ Automatic deployments from git

## Quick Deploy to Render

### Option 1: Using render.yaml (Recommended)

#### Step 1: Push Code to GitHub

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial UR Courses deployment"
git branch -M main

# Create GitHub repository and push
# (Do this on GitHub.com first, then:)
git remote add origin https://github.com/YOUR_USERNAME/ur-courses.git
git push -u origin main
```

#### Step 2: Deploy on Render

1. **Go to [Render Dashboard](https://dashboard.render.com)** and sign up/login with GitHub

2. **Click "New +"** and select **"Blueprint"**

3. **Connect your GitHub repository**

4. Render will auto-detect the `render.yaml` file

5. **Review the configuration** and click "Apply"

6. Render will create:
   - Web service (Python/Docker)
   - PostgreSQL database
   - Persistent disk for uploads

7. **Configure Environment Variables:**

   The render.yaml includes automatic env vars, but add these manually:
   ```
   FLASK_ENV=production
   SECRET_KEY= (auto-generated)
   JWT_SECRET= (auto-generated)
   ```

#### Step 3: Access Your App

1. Once deployment completes, click on your web service

2. Find the URL (e.g., `https://ur-courses.onrender.com`)

3. Open in browser to verify

---

### Option 2: Manual Deployment

#### Step 1: Push Code to GitHub

Same as Option 1 (Steps 1-5)

#### Step 2: Create Web Service

1. **Go to [Render Dashboard](https://dashboard.render.com)**

2. **Click "New +"** and select **"Web Service"**

3. **Connect your GitHub repository**

4. **Configure the service:**
   - Name: `ur-courses`
   - Environment: `Python 3` or `Docker`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
   - Plan: `Free`

5. **Add Environment Variables:**
   - `FLASK_ENV=production`
   - `SECRET_KEY=your-secure-random-key-here`
   - `JWT_SECRET=your-jwt-secret-key-here`
   - `PORT=5000`

6. **Click "Create Web Service"**

#### Step 3: Create PostgreSQL Database

1. **Click "New +"** and select **"PostgreSQL"**

2. **Configure:**
   - Name: `ur_courses_db`
   - Plan: `Free`
   - PostgreSQL Version: `15`

3. **Click "Create Database"**

4. Once created, copy the `Internal Database URL`

5. **Add to your web service** Environment Variables:
   - `DATABASE_URI=postgresql://user:password@hostname:5432/database`

#### Step 4: Add Persistent Disk (for uploads)

1. **Click "New +"** and select **"Disk"**

2. **Configure:**
   - Name: `uploads`
   - Size: `1 GB`
   - Mount Path: `/app/uploads`

3. **Click "Create Disk"**

4. **Attach to your web service** in the service settings

---

## Managing Your Deployment

### View Logs

1. Go to your service in Render dashboard
2. Click "Logs" tab

### Restart App

1. Click "Manual Deploy" dropdown
2. Select "Deploy latest commit"

### Scale Resources

1. Go to Settings → Plan
2. Select paid plan if needed

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_ENV` | Yes | Set to `production` |
| `SECRET_KEY` | Yes | Generate a secure random key |
| `JWT_SECRET` | Yes | Generate a secure random key |
| `DATABASE_URI` | Yes | PostgreSQL connection string |
| `PORT` | Yes | Set to `5000` |

### Generate Secure Keys

```bash
# Generate random secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Troubleshooting

### App Won't Start

1. Check "Logs" for errors
2. Common issues:
   - Missing environment variables
   - Database connection failed
   - Port not set to 5000

### Database Connection Issues

1. Verify `DATABASE_URI` is correct
2. Ensure PostgreSQL service is running
3. Check that the database user has proper permissions

### Static Files Not Loading

1. Ensure `static/` folder exists in the container
2. Check that Flask is configured to serve static files

### Uploaded Files Not Persisting

1. Ensure persistent disk is attached
2. Verify mount path is `/app/uploads`

---

## Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Use PostgreSQL (not SQLite) for production
- [ ] Set strong `SECRET_KEY` and `JWT_SECRET`
- [ ] Configure custom domain (optional)
- [ ] Set up regular backups (Render handles this for PostgreSQL)
- [ ] Monitor logs for errors

---

## Cost Estimation

- **Free Tier:**
  - Web Service: 500 hours/month
  - PostgreSQL: 256 MB storage
  - Disk: $0.10/GB/month
- **Paid Plans:**
  - Starter: $25/month

---

## Next Steps After Deployment

1. Test the app at your Render URL
2. Login as admin: `admin@ur.ac.rw` (password: `admin123`)
3. Configure colleges and schools
4. Add sample modules
5. Share with users

---

## Railway Deployment (Alternative)

If you prefer Railway, see [Railway Deployment Guide](#railway-deployment-guide)

## Why Railway?

- ✅ Free tier ($5/month credit)
- ✅ Easy GitHub integration
- ✅ PostgreSQL included
- ✅ Docker support built-in
- ✅ No CLI required for basic deployment

## Quick Deploy to Railway

### Step 1: Push Code to GitHub

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial UR Courses deployment"
git branch -M main

# Create GitHub repository and push
# (Do this on GitHub.com first, then:)
git remote add origin https://github.com/YOUR_USERNAME/ur-courses.git
git push -u origin main
```

### Step 2: Deploy on Railway

1. **Go to Railway.app** and sign up/login with GitHub

2. **Click "New Project"**

3. **Select "Deploy from GitHub repo"**

4. **Choose your repository** (ur-courses)

5. **Railway will auto-detect** the Dockerfile or Python app

6. **Configure Environment Variables:**

   Click "Variables" tab and add:
   ```
   FLASK_ENV=production
   SECRET_KEY=your-secure-random-key-here
   JWT_SECRET=your-jwt-secret-key-here
   DATABASE_URI=postgresql://...  # Railway will provide this
   ```

7. **Click "Deploy"**

### Step 3: Add PostgreSQL (Optional but Recommended)

1. In your Railway project dashboard, click **"New"** → **"Database"** → **"PostgreSQL"**

2. Wait for PostgreSQL to provision

3. Click on the PostgreSQL service to view connection string

4. Copy the `DATABASE_URL` and add it to your web service variables

### Step 4: Configure Domain (Optional)

1. Go to Settings → Networking

2. Click "Generate Domain" for a free *.railway.app domain

3. Or add your custom domain

## Managing Your Deployment

### View Logs

1. Go to your service in Railway dashboard
2. Click "Logs" tab

### Restart App

1. Click the "..." menu on your service
2. Select "Restart"

### Scale Resources

1. Go to Settings → Resources
2. Adjust plan as needed

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_ENV` | Yes | Set to `production` |
| `SECRET_KEY` | Yes | Generate a secure random key |
| `JWT_SECRET` | Yes | Generate a secure random key |
| `DATABASE_URI` | No | PostgreSQL connection string (auto-added if using Railway DB) |

### Generate Secure Keys

```bash
# Generate random secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

## Troubleshooting

### App Won't Start

1. Check "Logs" for errors
2. Common issues:
   - Missing environment variables
   - Database connection failed
   - Port not set to 5000

### Database Connection Issues

1. Verify `DATABASE_URI` is correct
2. Ensure PostgreSQL service is running
3. Check that the database user has proper permissions

### Static Files Not Loading

1. Ensure `static/` folder exists in the container
2. Check that Flask is configured to serve static files

## Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Use PostgreSQL (not SQLite) for production
- [ ] Set strong `SECRET_KEY` and `JWT_SECRET`
- [ ] Configure custom domain (optional)
- [ ] Set up regular backups (Railway handles this)
- [ ] Monitor logs for errors

## Cost Estimation

- **Free Tier:** $5/month credit (enough for small app)
- **Starter Plan:** $5/month (if exceeding free tier)
- **PostgreSQL:** Free on all plans

## Next Steps After Deployment

1. Test the app at your Railway URL
2. Login as admin: admin@ur.ac.rw
3. Configure colleges and schools
4. Add sample modules
5. Share with users
