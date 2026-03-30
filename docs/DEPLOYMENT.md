# Mitchell Technology Group Portal - Production Deployment Guide

## Pre-Deployment Checklist

### Security
- [ ] Generate a new SECRET_KEY (50+ characters)
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS with your domain(s)
- [ ] Set CSRF_TRUSTED_ORIGINS
- [ ] Set up SSL/TLS certificates
- [ ] Enable HSTS headers
- [ ] Configure secure cookies
- [ ] Review and restrict Django admin access

### Database
- [ ] Set up PostgreSQL production database
- [ ] Create database user with limited permissions
- [ ] Configure strong database password
- [ ] Set up database backups
- [ ] Run migrations: `python manage.py migrate`

### Files & Storage
- [ ] Configure static file serving (WhiteNoise or S3)
- [ ] Configure media file storage (local or S3)
- [ ] Run collectstatic: `python manage.py collectstatic --noinput`

### Email
- [ ] Configure SMTP settings
- [ ] Test email sending
- [ ] Set up email templates

### Payments
- [ ] Switch to live Stripe keys
- [ ] Configure Stripe webhook endpoint
- [ ] Test payment flow in test mode first

### Monitoring
- [ ] Set up error logging
- [ ] Configure admin email notifications
- [ ] (Optional) Set up Sentry or similar
- [ ] Set up uptime monitoring

---

## Deployment Options

### Option 1: Docker Deployment (Recommended)

1. **Clone and configure:**
   ```bash
   git clone <repository>
   cd mtg_portal
   cp .env.production.example .env.production
   # Edit .env.production with your values
   ```

2. **Set up SSL certificates:**
   ```bash
   # Using Let's Encrypt (recommended)
   # Create directory for Certbot
   mkdir -p nginx/certbot
   
   # Generate certificates (replace with your domain)
   docker run -it --rm -v $(pwd)/nginx/ssl:/etc/letsencrypt \
     -v $(pwd)/nginx/certbot:/var/www/certbot \
     certbot/certbot certonly --webroot \
     -w /var/www/certbot -d yourdomain.com
   ```

3. **Start services:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Run initial migrations:**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
   docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
   ```

5. **Verify deployment:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   docker-compose -f docker-compose.prod.yml logs web
   ```

---

### Option 2: Render Deployment

1. **Create a new Web Service on Render**
   - Connect your GitHub repository
   - Set build command: `./build.sh`
   - Set start command: `gunicorn mtg_portal.wsgi:application`

2. **Create build.sh:**
   ```bash
   #!/usr/bin/env bash
   set -o errexit
   pip install -r requirements.txt
   python manage.py collectstatic --noinput
   python manage.py migrate
   ```

3. **Environment Variables on Render:**
   - `DJANGO_SETTINGS_MODULE=mtg_portal.settings.production`
   - `SECRET_KEY=<your-secret-key>`
   - `ALLOWED_HOSTS=your-app.onrender.com`
   - `DATABASE_URL=<from-render-postgres>`
   - `REDIS_URL=<from-render-redis>`
   - All other env vars from `.env.production.example`

4. **Add PostgreSQL and Redis:**
   - Create a PostgreSQL database on Render
   - Create a Redis instance on Render
   - Connect them to your web service

---

### Option 3: DigitalOcean App Platform

1. **Create App from GitHub:**
   - Connect repository
   - Select Python runtime

2. **Configure App:**
   ```yaml
   # app.yaml
   name: mtg-portal
   services:
   - name: web
     source_dir: /
     github:
       repo: your-org/mtg_portal
       branch: main
     run_command: gunicorn mtg_portal.wsgi:application
     envs:
     - key: DJANGO_SETTINGS_MODULE
       value: mtg_portal.settings.production
     - key: DATABASE_URL
       scope: RUN_AND_BUILD_TIME
       value: ${db.DATABASE_URL}
   databases:
   - name: db
     engine: PG
   ```

3. **Add managed database and Redis**

---

### Option 4: AWS Deployment

#### Using Elastic Beanstalk:

1. **Install EB CLI:**
   ```bash
   pip install awsebcli
   ```

2. **Initialize EB:**
   ```bash
   eb init -p python-3.12 mtg-portal
   ```

3. **Create environment:**
   ```bash
   eb create mtg-portal-prod
   ```

4. **Configure environment variables:**
   ```bash
   eb setenv SECRET_KEY=<key> ALLOWED_HOSTS=<domain> ...
   ```

#### Using ECS/Fargate:

1. **Push Docker image to ECR:**
   ```bash
   aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   docker build -t mtg-portal .
   docker tag mtg-portal:latest <account>.dkr.ecr.<region>.amazonaws.com/mtg-portal:latest
   docker push <account>.dkr.ecr.<region>.amazonaws.com/mtg-portal:latest
   ```

2. **Create ECS task definition and service**
3. **Set up RDS PostgreSQL and ElastiCache Redis**
4. **Configure Application Load Balancer with SSL**

---

## Post-Deployment Tasks

1. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

2. **Load initial data (if any):**
   ```bash
   python manage.py loaddata initial_data.json
   ```

3. **Set up Site in Django admin:**
   - Go to admin > Sites
   - Update domain to your production domain

4. **Configure Stripe webhook:**
   - Go to Stripe Dashboard > Developers > Webhooks
   - Add endpoint: `https://yourdomain.com/billing/webhook/`
   - Select events: `invoice.paid`, `payment_intent.succeeded`, etc.

5. **Test critical paths:**
   - User registration/login
   - Create ticket
   - Create invoice
   - Process payment
   - Schedule meeting

---

## Maintenance

### Database Backups
```bash
# Manual backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U mtg_user mtg_portal > backup.sql

# Automated backups (add to crontab)
0 3 * * * /path/to/backup-script.sh
```

### Updating Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### Monitoring Logs
```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service
docker-compose -f docker-compose.prod.yml logs -f web
```

---

## Troubleshooting

### Common Issues

1. **Static files not loading:**
   - Ensure `collectstatic` ran successfully
   - Check nginx configuration
   - Verify `STATIC_ROOT` and `STATIC_URL` settings

2. **Database connection errors:**
   - Verify database credentials
   - Check if database service is running
   - Ensure network connectivity

3. **Celery tasks not running:**
   - Check Celery worker logs
   - Verify Redis connection
   - Ensure beat scheduler is running

4. **Email not sending:**
   - Test SMTP credentials
   - Check email logs
   - Verify firewall allows outbound SMTP

### Getting Help
- Check Django documentation: https://docs.djangoproject.com/
- Review deployment logs: `docker-compose logs`
- Contact support if needed
