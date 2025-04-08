# Cloud Deployment Guide

## Render Deployment

### Prerequisites
- A Render account (https://render.com)
- Git repository of your project
- Requirements.txt file

### Steps for Render Deployment

1. **Sign up and Connect Repository**
   - Create a Render account
   - Connect your GitHub/GitLab repository

2. **Create New Web Service**
   - Click "New +" > "Web Service"
   - Select your repository
   - Configure service:
     - Name: `ai-yoga-instructor`
     - Environment: `Python 3`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn app:app`

3. **Environment Variables**
   Add these in Render dashboard:
   ```
   FLASK_ENV=production
   FLASK_DEBUG=0
   DATABASE_URL=your_render_postgres_url
   GROQ_API_KEY=your_groq_api_key
   GEMINI_API_KEY=your_gemini_api_key
   SECRET_KEY=your_secure_secret_key
   ```

4. **Database Setup**
   - Create a new PostgreSQL database in Render
   - Render will provide the DATABASE_URL
   - Update your app's database connection to use PostgreSQL

## PythonAnywhere Deployment

### Prerequisites
- A PythonAnywhere account (https://www.pythonanywhere.com)
- Git repository of your project

### Steps for PythonAnywhere Deployment

1. **Create PythonAnywhere Account**
   - Sign up for a PythonAnywhere account
   - Choose a plan that suits your needs

2. **Clone Repository**
   ```bash
   # In PythonAnywhere bash console
   git clone <your-repository-url>
   cd YogaInstructor
   ```

3. **Setup Virtual Environment**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.8 yogaenv
   pip install -r requirements.txt
   ```

4. **Configure Web App**
   - Go to Web tab in PythonAnywhere dashboard
   - Create new web app
   - Choose Manual Configuration
   - Select Python version

5. **Configure WSGI File**
   Edit the WSGI configuration file:
   ```python
   import sys
   path = '/home/yourusername/YogaInstructor'
   if path not in sys.path:
       sys.path.append(path)

   from app import app as application
   ```

6. **Environment Variables**
   Add to WSGI file or use environment variables panel:
   ```python
   import os
   os.environ['FLASK_ENV'] = 'production'
   os.environ['FLASK_DEBUG'] = '0'
   os.environ['DATABASE_URL'] = 'mysql://username:password@yourusername.mysql.pythonanywhere-services.com/yourusername$yoga_db'
   os.environ['GROQ_API_KEY'] = 'your_groq_api_key'
   os.environ['GEMINI_API_KEY'] = 'your_gemini_api_key'
   os.environ['SECRET_KEY'] = 'your_secure_secret_key'
   ```

7. **Database Setup**
   - Create MySQL database from PythonAnywhere dashboard
   - Update DATABASE_URL with PythonAnywhere MySQL credentials

8. **Static Files**
   Configure static files in Web app configuration:
   - URL: /static/
   - Directory: /home/yourusername/YogaInstructor/static

## Important Notes

1. **Database Migration**
   - For both platforms, run migrations after deployment:
     ```bash
     flask db upgrade
     ```

2. **Environment Variables**
   - Never commit sensitive information to Git
   - Use platform-specific environment variable management

3. **Static Files**
   - Both platforms handle static files automatically
   - Ensure proper configuration in Flask app

4. **Debugging**
   - Check platform-specific logs for troubleshooting
   - Use platform's built-in console for direct access

5. **SSL/HTTPS**
   - Both platforms provide SSL certificates automatically
   - No additional configuration needed

6. **Performance**
   - Monitor application performance using platform metrics
   - Configure proper worker processes based on plan limits

7. **Maintenance**
   - Regular updates through git pull
   - Monitor resource usage
   - Keep dependencies updated