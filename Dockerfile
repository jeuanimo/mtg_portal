# Production Dockerfile for Mitchell Technology Group Portal
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user for security
RUN groupadd -r mtgportal && useradd -r -g mtgportal mtgportal

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY --chown=mtgportal:mtgportal . .

# Create directories for logs and media
RUN mkdir -p /var/log/mtg_portal /app/media /app/staticfiles \
    && chown -R mtgportal:mtgportal /var/log/mtg_portal /app/media /app/staticfiles

# Collect static files — SECRET_KEY is required by production.py at import time;
# use a dummy value here since collectstatic never touches the database or secrets.
ENV DJANGO_SETTINGS_MODULE=mtg_portal.settings.production
RUN SECRET_KEY=collectstatic-dummy-key \
    DJANGO_ENV=production \
    CLOUDINARY_CLOUD_NAME=dummy \
    CLOUDINARY_API_KEY=dummy \
    CLOUDINARY_API_SECRET=dummy \
    python manage.py collectstatic --noinput --clear

# Switch to non-root user
USER mtgportal

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--worker-class", "gthread", "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "--error-logfile", "-", "mtg_portal.wsgi:application"]
