# Django Print Estimation - Render.com Deployment Guide

## Prerequisites
1. A Render.com account (free tier available)
2. GitHub account with your code repository
3. Your Django project pushed to GitHub

## Step-by-Step Deployment Process

### 1. Prepare Your Repository
Ensure these files are in your repository:
- `requirements.txt` - Python dependencies
- `build.sh` - Build script for Render
- `render.yaml` - Render configuration
- `fixtures/initial_data.json` - Your database data
- `.env.example` - Environment variables template

### 2. Create Database on Render
1. Log into Render.com
2. Click "New +" → "PostgreSQL"
3. Name: `printestimation-db`
4. Database Name: `printing_estimation`
5. User: `printing_user`
6. Plan: Free tier
7. Click "Create Database"
8. Note down the connection details

### 3. Deploy Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Select your PrintEstimation repository
4. Configuration:
   - Name: `printestimation-web`
   - Runtime: `Python 3`
   - Build Command: `./build.sh`
   - Start Command: `gunicorn PrintEstimation.wsgi:application`

### 4. Set Environment Variables
In your web service settings, add these environment variables:
- `SECRET_KEY`: Generate a new Django secret key
- `DEBUG`: `false`
- `ALLOWED_HOSTS`: `your-app-name.onrender.com`
- `DATABASE_URL`: (Auto-filled from your database)

### 5. Deploy and Monitor
1. Click "Create Web Service"
2. Render will automatically build and deploy
3. Monitor the deployment logs for any errors
4. Your app will be available at: `https://your-app-name.onrender.com`

## Post-Deployment Tasks

### 1. Create Superuser (if needed)
Connect to your web service shell:
```bash
python manage.py createsuperuser
```

### 2. Verify Data Migration
Check that your data was loaded correctly:
- Visit `/admin/` to verify users and data
- Test your application functionality

### 3. Configure Custom Domain (Optional)
- In Render dashboard, go to Settings → Custom Domains
- Add your domain and configure DNS

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | Debug mode | `false` |
| `ALLOWED_HOSTS` | Allowed hostnames | `myapp.onrender.com` |
| `DATABASE_URL` | Database connection | Auto-provided by Render |

## File Structure for Deployment
```
PrintEstimation/
├── requirements.txt        # Python dependencies
├── build.sh               # Build script
├── render.yaml           # Render configuration
├── fixtures/
│   └── initial_data.json # Database fixtures
├── .env.example          # Environment template
├── manage.py
├── PrintEstimation/
│   ├── settings.py       # Updated for production
│   ├── wsgi.py
│   └── ...
└── ...
```

## Troubleshooting

### Common Issues:
1. **Build fails**: Check `requirements.txt` for correct package versions
2. **Database connection errors**: Verify `DATABASE_URL` in environment variables
3. **Static files not loading**: Ensure `whitenoise` is in `MIDDLEWARE`
4. **Migration errors**: Check if fixture data conflicts with migrations

### Debug Steps:
1. Check Render deployment logs
2. Verify environment variables are set correctly
3. Test database connection in Render shell
4. Ensure all required files are committed to Git

## Cost Considerations
- **Free Tier Limitations**: 
  - 750 hours/month (app sleeps after 15 min of inactivity)
  - PostgreSQL: 1GB storage, 1 month retention
- **Paid Plans**: Available for production apps with guaranteed uptime

## Security Notes
- Never commit `.env` files with real secrets
- Use strong passwords for database
- Consider enabling 2FA on Render account
- Regularly update dependencies

---
*Generated for Print Estimation Django Application*