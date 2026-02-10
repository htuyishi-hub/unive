# Deployment Guide - Railway (Recommended)

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
