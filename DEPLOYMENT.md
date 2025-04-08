# AI Yoga Instructor - Deployment Guide

## Prerequisites

- Python 3.8 or higher
- MySQL Server
- Web server (Nginx/Apache)
- SSL certificate
- Domain name

## Environment Setup

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd YogaInstructor
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install gunicorn  # For production WSGI server
   ```

4. **Environment Variables**
   - Copy `.env.example` to `.env`
   - Update the following variables:
     ```
     FLASK_ENV=production
     FLASK_DEBUG=0
     DATABASE_URL=mysql://user:password@localhost/yoga_db
     GROQ_API_KEY=your_groq_api_key
     GEMINI_API_KEY=your_gemini_api_key
     SECRET_KEY=your_secure_secret_key
     ```

## Database Setup

1. **Create Production Database**
   ```sql
   CREATE DATABASE yoga_db;
   CREATE USER 'yoga_user'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT ALL PRIVILEGES ON yoga_db.* TO 'yoga_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. **Initialize Database**
   ```bash
   flask db upgrade
   ```

## Web Server Configuration

### Nginx Configuration

1. **Create Nginx Configuration**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /static {
           alias /path/to/your/static/;
       }
   }
   ```

2. **SSL Configuration**
   ```nginx
   server {
       listen 443 ssl;
       server_name yourdomain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       # SSL configurations
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers HIGH:!aNULL:!MD5;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Application Deployment

1. **Start Gunicorn**
   ```bash
   gunicorn -w 4 -b 127.0.0.1:8000 app:app
   ```

2. **Setup Systemd Service**
   Create `/etc/systemd/system/yoga-instructor.service`:
   ```ini
   [Unit]
   Description=AI Yoga Instructor
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/path/to/YogaInstructor
   Environment="PATH=/path/to/venv/bin"
   ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

   [Install]
   WantedBy=multi-user.target
   ```

3. **Start Service**
   ```bash
   sudo systemctl start yoga-instructor
   sudo systemctl enable yoga-instructor
   ```

## Monitoring Setup

1. **Install Monitoring Tools**
   ```bash
   pip install prometheus_client
   pip install flask_prometheus_metrics
   ```

2. **Setup Basic Monitoring**
   - CPU usage
   - Memory usage
   - Request latency
   - Error rates
   - API endpoint metrics

3. **Configure Logging**
   ```python
   import logging
   logging.basicConfig(
       filename='yoga_instructor.log',
       level=logging.INFO,
       format='%(asctime)s %(levelname)s: %(message)s'
   )
   ```

## Security Checklist

- [ ] SSL/TLS enabled
- [ ] Secure headers configured
- [ ] Rate limiting implemented
- [ ] Input validation
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF protection
- [ ] Regular security updates

## Backup Strategy

1. **Database Backup**
   ```bash
   mysqldump -u username -p yoga_db > backup.sql
   ```

2. **Application Backup**
   ```bash
   tar -czf yoga_instructor_backup.tar.gz /path/to/YogaInstructor
   ```

## Troubleshooting

1. **Check Application Status**
   ```bash
   sudo systemctl status yoga-instructor
   ```

2. **View Logs**
   ```bash
   tail -f yoga_instructor.log
   journalctl -u yoga-instructor
   ```

3. **Common Issues**
   - Database connection errors
   - Permission issues
   - SSL certificate problems
   - Memory/CPU constraints

## Performance Optimization

1. **Enable Caching**
   - Implement Redis for session storage
   - Cache API responses
   - Static file caching

2. **Database Optimization**
   - Index frequently queried columns
   - Optimize slow queries
   - Regular maintenance

## Maintenance Procedures

1. **Regular Updates**
   ```bash
   git pull origin main
   pip install -r requirements.txt
   flask db upgrade
   sudo systemctl restart yoga-instructor
   ```

2. **Monitoring Checks**
   - Review error logs daily
   - Monitor system resources
   - Check backup integrity
   - Update SSL certificates

## Support

For issues and support:
- Create an issue in the repository
- Contact the development team
- Check documentation for common solutions