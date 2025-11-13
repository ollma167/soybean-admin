# 🚀 Deployment Guide - Combo Tool System

Complete deployment guide for the frontend-backend separated Combo Tool system.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Database Management](#database-management)
- [Monitoring and Logs](#monitoring-and-logs)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx (Port 80/443)                    │
│              Frontend + API Reverse Proxy                 │
└───────────────────────┬─────────────────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
         ▼                             ▼
┌─────────────────┐          ┌──────────────────┐
│   Vue Frontend   │          │  FastAPI Backend │
│  (Static Files)  │          │   (Port 8000)    │
└─────────────────┘          └────────┬─────────┘
                                      │
                        ┌─────────────┴──────────────┐
                        │                            │
                        ▼                            ▼
              ┌──────────────┐           ┌────────────────┐
              │ MySQL:3306   │           │  Redis:6379    │
              │ (Database)   │           │  (Cache)       │
              └──────────────┘           └────────────────┘
```

## 📦 Prerequisites

### Required Software

- **Docker**: 20.10+ & Docker Compose 2.0+
- **Git**: 2.30+

### Optional (for local development)

- **Node.js**: 20.19.0+
- **pnpm**: 10.5.0+
- **Python**: 3.11+
- **MySQL**: 8.0+
- **Redis**: 7.0+

## ⚡ Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd <repository-name>
git checkout feat-split-front-back-python-docker-mysql-redis
```

### 2. Configure Environment

```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit configuration (optional)
nano backend/.env
```

### 3. Start All Services

```bash
# Production mode
docker-compose up -d

# Development mode
docker-compose -f docker-compose.dev.yml up -d
```

### 4. Initialize Database

```bash
# Wait for MySQL to be ready (check logs)
docker-compose logs -f mysql

# Migrate templates from JSON
docker-compose exec backend python /app/../scripts/migrate_templates.py /app/../tool/templates.json
```

### 5. Access Services

- **Frontend**: http://localhost
- **Backend API Docs**: http://localhost/docs
- **Backend Health**: http://localhost/api/health
- **MySQL**: localhost:3306
- **Redis**: localhost:6379

## 🛠️ Development Setup

### Frontend Development

```bash
# Install dependencies
pnpm install

# Start dev server
pnpm run dev

# Build for production
pnpm run build
```

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Using Docker Compose (Recommended)

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Restart specific service
docker-compose -f docker-compose.dev.yml restart backend

# Stop all services
docker-compose -f docker-compose.dev.yml down
```

## 🏭 Production Deployment

### Option 1: Docker Compose (Recommended)

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
nano backend/.env  # Update with production values

# 2. Build and start services
docker-compose up -d --build

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f

# 5. Migrate data
docker-compose exec backend python /app/../scripts/migrate_templates.py /app/../tool/templates.json
```

### Option 2: Kubernetes (Advanced)

```bash
# TODO: Add Kubernetes manifests
kubectl apply -f k8s/
```

### Option 3: Manual Deployment

#### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/combo_db"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="your-secret-key"

# Run with Gunicorn (production)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Frontend

```bash
# Build
pnpm run build

# Serve with Nginx
cp -r dist/* /var/www/html/
cp nginx/nginx.conf /etc/nginx/sites-available/combo-tool
ln -s /etc/nginx/sites-available/combo-tool /etc/nginx/sites-enabled/
nginx -s reload
```

## 🗄️ Database Management

### Initialize Database

```bash
# Using Docker
docker-compose exec mysql mysql -u combo_user -pcombo_password combo_db < backend/migrations/init.sql

# Or locally
mysql -u combo_user -pcombo_password combo_db < backend/migrations/init.sql
```

### Migrate Templates

```bash
# From Docker
docker-compose exec backend python /app/../scripts/migrate_templates.py /app/../tool/templates.json

# Or locally
cd scripts
python migrate_templates.py ../tool/templates.json
```

### Backup Database

```bash
# Backup
docker-compose exec mysql mysqldump -u combo_user -pcombo_password combo_db > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T mysql mysql -u combo_user -pcombo_password combo_db < backup_20240101.sql
```

### Database Maintenance

```bash
# Connect to MySQL
docker-compose exec mysql mysql -u combo_user -pcombo_password combo_db

# Check tables
SHOW TABLES;

# Check template count
SELECT COUNT(*) FROM templates;

# Check recent logs
SELECT * FROM operation_logs ORDER BY created_at DESC LIMIT 10;
```

## 📊 Monitoring and Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f mysql
docker-compose logs -f redis

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Health Checks

```bash
# Backend health
curl http://localhost/api/health

# Quick ping
curl http://localhost/api/health/ping

# Frontend health
curl http://localhost/health
```

### Redis Monitoring

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Check keys
KEYS *

# Monitor commands
MONITOR

# Get info
INFO
```

### MySQL Monitoring

```bash
# Connect to MySQL
docker-compose exec mysql mysql -u root -p

# Show processes
SHOW PROCESSLIST;

# Check database size
SELECT 
    table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.tables
WHERE table_schema = 'combo_db'
GROUP BY table_schema;
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)

```env
# Application
APP_NAME=Combo Tool API
DEBUG=false
ENVIRONMENT=production

# Database
DATABASE_URL=mysql+pymysql://combo_user:combo_password@mysql:3306/combo_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600

# Security
SECRET_KEY=change-this-to-a-random-secret-key
CORS_ORIGINS=http://localhost,https://yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### Docker Compose (.env)

```env
# MySQL
MYSQL_ROOT_PASSWORD=strongrootpassword
MYSQL_DATABASE=combo_db
MYSQL_USER=combo_user
MYSQL_PASSWORD=combo_password

# Security
SECRET_KEY=your-secret-key-change-in-production
```

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Database not ready
docker-compose logs mysql | grep "ready for connections"

# 2. Port conflict
lsof -i :8000
# Kill process using the port

# 3. Rebuild container
docker-compose up -d --build backend
```

### Database connection errors

```bash
# Check MySQL is running
docker-compose ps mysql

# Check MySQL logs
docker-compose logs mysql

# Test connection
docker-compose exec mysql mysql -u combo_user -pcombo_password -e "SELECT 1"

# Restart MySQL
docker-compose restart mysql
```

### Redis connection errors

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

### Frontend not loading

```bash
# Check Nginx logs
docker-compose logs frontend

# Check if dist folder exists
ls -la dist/

# Rebuild frontend
pnpm run build
docker-compose restart frontend
```

### Performance issues

```bash
# Check resource usage
docker stats

# Scale backend
docker-compose up -d --scale backend=3

# Check database slow queries
docker-compose exec mysql mysql -u root -p -e "SHOW PROCESSLIST"

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHDB
```

## 🔐 Security Checklist

- [ ] Change default passwords in .env
- [ ] Generate secure SECRET_KEY
- [ ] Configure CORS origins properly
- [ ] Enable HTTPS in production
- [ ] Set up firewall rules
- [ ] Regular database backups
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated
- [ ] Use secrets management (Vault, AWS Secrets Manager)

## 📈 Performance Optimization

### Backend

- Use Redis caching for hot templates
- Enable connection pooling (already configured)
- Use async endpoints
- Scale with multiple workers

### Database

- Add indexes on frequently queried columns
- Regular VACUUM/ANALYZE
- Monitor slow queries
- Use read replicas for heavy loads

### Frontend

- Enable Gzip compression (already configured)
- Use CDN for static assets
- Implement code splitting
- Cache API responses

## 🔄 Updates and Maintenance

### Update Backend

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose up -d --build backend
```

### Update Database Schema

```bash
# Create migration
# Add SQL to backend/migrations/

# Apply migration
docker-compose exec mysql mysql -u combo_user -pcombo_password combo_db < backend/migrations/new_migration.sql
```

### Update Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt --upgrade

# Frontend
pnpm update
```

## 📞 Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Review this guide
3. Check API documentation: http://localhost/docs
4. Review GitHub issues
5. Contact the development team

## 📚 Additional Resources

- [Backend README](backend/README.md)
- [Frontend README](README.md)
- [API Documentation](http://localhost/docs)
- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
