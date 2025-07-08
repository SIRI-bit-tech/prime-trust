# PrimeTrust Banking Application - Production Deployment Guide

## 🎯 Overview

This guide covers the complete production deployment of the PrimeTrust Banking Application with Bugsnag error monitoring, enhanced security, and performance optimizations.

## 📋 Prerequisites

### System Requirements
- **Python 3.9+**
- **PostgreSQL 12+** (recommended for production)
- **Redis** (optional, for caching)
- **SSL Certificate** (for HTTPS)
- **Domain Name** (for production deployment)

### Required Accounts
- **Bugsnag Account** - For error monitoring
- **Email Service** - SendGrid, AWS SES, or SMTP provider
- **Database Hosting** - PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
- **Server Hosting** - AWS, Google Cloud, Heroku, or DigitalOcean

## 🔧 Production Setup

### 1. Environment Configuration

Copy the environment template and configure your production values:

```bash
cp production.env.example .env
```

Edit `.env` with your production values:

```bash
# Core Settings
SECRET_KEY=your-super-secret-key-here-change-this-in-production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (PostgreSQL recommended)
DATABASE_URL=postgresql://username:password@host:5432/primetrust_db

# Error Monitoring
BUGSNAG_API_KEY=your-bugsnag-api-key-here

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yourmailprovider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email-username
EMAIL_HOST_PASSWORD=your-email-password
```

### 2. Database Setup

#### PostgreSQL Setup
```sql
-- Create database
CREATE DATABASE primetrust_db;

-- Create user
CREATE USER primetrust_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE primetrust_db TO primetrust_user;
```

### 3. Security Configuration

#### SSL/HTTPS Setup
- Obtain SSL certificate from Let's Encrypt or your provider
- Configure your web server (Nginx/Apache) for HTTPS
- Update `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` with HTTPS URLs

#### Firewall Configuration
```bash
# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow SSH (if needed)
sudo ufw allow 22

# Enable firewall
sudo ufw enable
```

## 🚀 Deployment Options

### Option 1: Using Production Scripts (Recommended)

#### Windows
```cmd
# For production
start_production.bat

# For development/testing
start_dev.bat
```

#### Linux/macOS
```bash
# Make script executable
chmod +x start_production.sh

# Run production setup
./start_production.sh
```

### Option 2: Manual Deployment

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create directories
mkdir -p logs media staticfiles backups

# 3. Run migrations
python manage.py migrate

# 4. Create cache tables
python manage.py createcachetable

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Create superuser
python manage.py createsuperuser

# 7. Start production server
gunicorn --bind 0.0.0.0:8000 --workers 4 core.wsgi:application
```

## 🛡️ Security Features

### Implemented Security Measures
- ✅ **HTTPS Enforcement** - All traffic redirected to HTTPS
- ✅ **HSTS Headers** - HTTP Strict Transport Security
- ✅ **Content Security Policy** - XSS protection
- ✅ **CSRF Protection** - Cross-site request forgery protection
- ✅ **Rate Limiting** - API and login attempt limiting
- ✅ **2FA Authentication** - Time-based OTP support
- ✅ **Device Fingerprinting** - Suspicious login detection
- ✅ **Account Lockout** - Brute force protection
- ✅ **Audit Logging** - Security event tracking
- ✅ **Field Encryption** - Sensitive data encryption

### Security Headers
```
Secure-SSL-Redirect: True
Session-Cookie-Secure: True
CSRF-Cookie-Secure: True
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: same-origin
```

## 📊 Monitoring & Error Tracking

### Bugsnag Integration
The application is configured with Bugsnag for comprehensive error monitoring:

- **Real-time Error Alerts**
- **Performance Monitoring**
- **Release Tracking**
- **User Impact Analysis**
- **Error Grouping & Trends**

### Log Files
```
logs/
├── django.log          # General application logs
├── security.log        # Security events
├── errors.log          # Error logs
├── access.log          # HTTP access logs
└── startup.log         # Deployment logs
```

## 🔄 API Documentation

### Available Endpoints

#### Authentication APIs
- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/logout/` - User logout
- `POST /api/v1/auth/refresh/` - Token refresh

#### Banking APIs
- `GET /api/v1/accounts/` - List user accounts
- `POST /api/v1/transactions/` - Create transaction
- `GET /api/v1/transactions/` - List transactions
- `POST /api/v1/transfers/` - Transfer money

#### Investment APIs
- `GET /api/v1/investments/` - List investments
- `POST /api/v1/investments/` - Create investment
- `GET /api/v1/portfolios/` - View portfolios

### API Documentation Access
- **Swagger UI**: `https://yourdomain.com/api/docs/`
- **ReDoc**: `https://yourdomain.com/api/redoc/`
- **OpenAPI Schema**: `https://yourdomain.com/api/schema/`

## 🌐 Web Application Features

### User Features
- ✅ **Multi-step Registration** with email verification
- ✅ **2FA Setup** with QR codes and backup codes
- ✅ **Transaction PIN** for secure operations
- ✅ **Account Management** - checking, savings accounts
- ✅ **Money Transfers** - internal and external
- ✅ **Bill Payments** - utility and service payments
- ✅ **Investment Management** - portfolio tracking
- ✅ **Loan Applications** - personal and business loans
- ✅ **Insurance Policies** - life and health insurance
- ✅ **Bitcoin Wallet** - cryptocurrency support
- ✅ **Transaction History** - detailed records
- ✅ **Notifications** - real-time alerts

### Admin Features
- ✅ **User Management** - comprehensive admin panel
- ✅ **Transaction Monitoring** - fraud detection
- ✅ **Account Controls** - freeze/unfreeze accounts
- ✅ **Security Dashboard** - threat monitoring
- ✅ **Audit Logs** - compliance reporting

## 🧪 Testing

### Health Check Endpoint
```bash
curl https://yourdomain.com/health/
```

### API Testing
```bash
# Test authentication
curl -X POST https://yourdomain.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Test protected endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://yourdomain.com/api/v1/accounts/
```

## 📱 Performance Optimizations

### Implemented Optimizations
- ✅ **Database Query Optimization** - Efficient ORM usage
- ✅ **Static File Compression** - WhiteNoise with compression
- ✅ **Database Connection Pooling** - Connection reuse
- ✅ **API Response Caching** - Reduced database hits
- ✅ **Pagination** - Large dataset handling
- ✅ **File Upload Optimization** - Efficient media handling

### Gunicorn Configuration
```bash
gunicorn \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class sync \
  --worker-connections 1000 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --timeout 30 \
  --keep-alive 5 \
  --preload \
  core.wsgi:application
```

## 🔐 Backup & Recovery

### Database Backups
```bash
# Create backup
pg_dump -h hostname -U username primetrust_db > backup_$(date +%Y%m%d).sql

# Restore backup
psql -h hostname -U username primetrust_db < backup_file.sql
```

### Media File Backups
```bash
# Backup media files
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/

# Restore media files
tar -xzf media_backup_file.tar.gz
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```bash
# Check database connectivity
python manage.py dbshell

# Verify DATABASE_URL format
echo $DATABASE_URL
```

#### 2. Static Files Not Loading
```bash
# Recollect static files
python manage.py collectstatic --clear --noinput

# Check STATIC_ROOT permissions
ls -la staticfiles/
```

#### 3. Email Configuration Issues
```bash
# Test email settings
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
```

#### 4. SSL/HTTPS Issues
- Verify SSL certificate installation
- Check domain DNS configuration
- Ensure HTTPS redirects are working

### Log Analysis
```bash
# Check error logs
tail -f logs/errors.log

# Monitor security events
tail -f logs/security.log

# View access patterns
tail -f logs/access.log
```

## 📞 Support & Maintenance

### Regular Maintenance Tasks
1. **Security Updates** - Keep dependencies updated
2. **Database Maintenance** - Regular backups and optimization
3. **Log Rotation** - Prevent disk space issues
4. **Performance Monitoring** - Track response times
5. **Security Audits** - Regular security assessments

### Update Deployment
```bash
# Pull latest code
git pull origin main

# Install new dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart server
sudo systemctl restart gunicorn
```

## 🎉 Conclusion

The PrimeTrust Banking Application is now production-ready with:

- ✅ **Enterprise-grade Security**
- ✅ **Comprehensive API Suite**
- ✅ **Real-time Error Monitoring**
- ✅ **High Performance**
- ✅ **Full Banking Features**
- ✅ **Mobile-responsive UI**
- ✅ **Admin Management Tools**

For additional support or questions, refer to the application logs and Bugsnag dashboard for detailed insights.

---

**🔒 Security Notice**: Always use HTTPS in production and keep your secret keys secure. Regularly update dependencies and monitor security logs. 