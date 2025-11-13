# 🏗️ Architecture Documentation - Combo Tool System

## 📖 Overview

This document describes the architecture of the Combo Tool system after the frontend-backend separation refactoring.

## 🎯 System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Layer                                  │
│  (Browser, Mobile App, API Clients)                                  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTPS/HTTP
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Nginx Reverse Proxy                              │
│  - Serve static files (Vue frontend)                                 │
│  - Proxy API requests to backend                                     │
│  - SSL termination                                                    │
│  - Gzip compression                                                   │
│  - Security headers                                                   │
└─────────┬───────────────────────────────────────┬───────────────────┘
          │                                       │
          │ /api/*                                │ Static Files
          ▼                                       ▼
┌─────────────────────────┐           ┌──────────────────────────┐
│   FastAPI Backend        │           │   Vue 3 Frontend         │
│   (Port 8000)            │           │   (SoybeanAdmin)         │
│                          │           │                          │
│  - REST API endpoints    │           │  - Admin UI              │
│  - Business logic        │           │  - Vite 7 + TypeScript   │
│  - Data validation       │           │  - Naive UI components   │
│  - Template management   │           │  - Pinia state mgmt      │
│  - Combo generation      │           │  - Vue Router            │
│  - Caching layer         │           │  - i18n support          │
│  - Structured logging    │           │  - Responsive design     │
└────┬──────────────┬─────┘           └──────────────────────────┘
     │              │
     │ SQLAlchemy   │ Redis
     ▼              ▼
┌──────────────┐   ┌──────────────┐
│ MySQL 8.0    │   │  Redis 7     │
│              │   │              │
│ - Templates  │   │ - Cache      │
│ - Combos     │   │ - Sessions   │
│ - Items      │   │ - Rate limit │
│ - Logs       │   │              │
└──────────────┘   └──────────────┘
```

## 🔧 Component Details

### 1. Frontend (Vue 3 + Vite)

**Technology Stack**:
- Vue 3.5.22
- Vite 7.1.12
- TypeScript 5.9.3
- Naive UI 2.43.1
- UnoCSS 66.5.4
- Pinia 3.0.3
- Vue Router 4.6.3
- Vue I18n 11.1.12

**Key Features**:
- Modern admin template with multiple layouts
- Responsive design with mobile support
- Multi-language support (i18n)
- Theme customization
- Component auto-import
- Route generation
- Authentication & authorization
- State management with Pinia

**Directory Structure**:
```
src/
├── assets/          # Static assets
├── components/      # Reusable components
├── layouts/         # Layout templates
├── locales/         # i18n translations
├── router/          # Route configuration
├── service/         # API service layer
├── store/           # Pinia stores
├── styles/          # Global styles
├── views/           # Page components
└── main.ts          # Application entry
```

### 2. Backend (FastAPI + Python)

**Technology Stack**:
- FastAPI 0.115.0
- Python 3.11
- SQLAlchemy 2.0.36
- Pydantic 2.10.3
- Redis 5.2.0
- Uvicorn 0.32.0
- Structlog 24.4.0

**Architecture Patterns**:
- **Layered Architecture**: API → Service → Repository → Database
- **Dependency Injection**: FastAPI's built-in DI system
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic encapsulation
- **DTO Pattern**: Pydantic schemas for data transfer

**Directory Structure**:
```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   └── v1/          # API version 1
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── utils/           # Utilities
│   ├── config.py        # Configuration
│   ├── database.py      # DB connection
│   └── main.py          # Application entry
├── migrations/          # Database migrations
└── tests/              # Test suite
```

### 3. Database (MySQL 8.0)

**Schema Design**:

```sql
templates
├── id (PK)
├── name (UNIQUE)
├── description
├── created_at
├── updated_at
└── is_active

template_combos
├── id (PK)
├── template_id (FK → templates.id)
├── prefix
└── sort_order

combo_items
├── id (PK)
├── combo_id (FK → template_combos.id)
├── product_code
├── quantity
├── sale_price
├── base_price
└── cost_price

operation_logs
├── id (PK)
├── user_id
├── action
├── resource_type
├── resource_id
├── details
└── created_at
```

**Relationships**:
- Template 1:N Combos
- Combo 1:N Items
- Cascading deletes enabled

**Indexes**:
- Primary keys on all tables
- Unique index on templates.name
- Foreign key indexes
- Search indexes on frequently queried columns

### 4. Cache (Redis 7)

**Usage**:
- **Template Caching**: Hot templates cached for 1 hour
- **Result Caching**: Combo generation results
- **Session Storage**: User sessions (future)
- **Rate Limiting**: API request throttling (future)

**Key Patterns**:
```
template:{id}              # Template details
combo_result:{hash}        # Cached combo generation results
session:{token}           # User sessions (future)
rate_limit:{ip}:{endpoint} # Rate limiting (future)
```

**Configuration**:
- Max memory: 256MB
- Eviction policy: allkeys-lru
- Persistence: AOF enabled
- TTL: 3600 seconds (1 hour)

## 🔄 Data Flow

### Template CRUD Operations

```
1. Client Request
   └─→ Nginx
       └─→ Backend API
           ├─→ Check Redis cache (for GET)
           ├─→ Validate input (Pydantic)
           ├─→ Service layer
           │   └─→ Database operations (SQLAlchemy)
           ├─→ Update cache
           └─→ Return response

2. Response
   ├─→ Structured logging
   ├─→ Error handling
   └─→ Client receives JSON
```

### Combo Generation Flow

```
1. Client submits generation request
   └─→ POST /api/v1/combos/generate

2. Backend processing
   ├─→ Validate input (Pydantic schema)
   ├─→ Fetch template from DB/cache
   ├─→ Convert template to combo format
   ├─→ Process main products
   ├─→ Apply simplification rules
   ├─→ Generate combo rows
   └─→ Return results

3. Optional: Cache results
   └─→ Redis (if same request repeats)
```

## 🔐 Security Architecture

### Authentication & Authorization (Future)

```
Client → JWT Token → API Gateway → Backend
                      ↓
                 Verify Token
                      ↓
              Extract User Claims
                      ↓
            Check Permissions
                      ↓
          Allow/Deny Request
```

### Current Security Measures

1. **Input Validation**: Pydantic schemas
2. **SQL Injection Protection**: SQLAlchemy ORM
3. **CORS Configuration**: Controlled origins
4. **Rate Limiting**: Planned with Redis
5. **Secure Headers**: Nginx configuration
6. **Environment Variables**: Sensitive data isolation

## 📊 Scalability Considerations

### Horizontal Scaling

**Backend**:
```
Load Balancer
├─→ Backend Instance 1
├─→ Backend Instance 2
├─→ Backend Instance 3
└─→ Backend Instance N

docker-compose up -d --scale backend=3
```

**Database**:
- Master-slave replication
- Read replicas for heavy read loads
- Connection pooling (20 connections)

**Cache**:
- Redis Cluster for high availability
- Redis Sentinel for automatic failover

### Vertical Scaling

- **Backend**: Increase worker count
- **Database**: Upgrade instance size, add memory
- **Redis**: Increase memory allocation

### Performance Optimization

1. **Caching Strategy**:
   - Hot data in Redis
   - TTL-based expiration
   - Cache invalidation on updates

2. **Database Optimization**:
   - Proper indexing
   - Query optimization
   - Connection pooling

3. **API Optimization**:
   - Async endpoints
   - Batch operations
   - Pagination for large datasets

4. **Frontend Optimization**:
   - Code splitting
   - Lazy loading
   - CDN for static assets
   - Gzip compression

## 🐳 Containerization

### Docker Architecture

```
docker-compose.yml
├── backend service
│   ├── Build: ./backend/Dockerfile
│   ├── Port: 8000
│   └── Depends: mysql, redis
├── mysql service
│   ├── Image: mysql:8.0
│   ├── Port: 3306
│   └── Volume: mysql_data
├── redis service
│   ├── Image: redis:7-alpine
│   ├── Port: 6379
│   └── Volume: redis_data
└── frontend service
    ├── Image: nginx:alpine
    ├── Port: 80, 443
    └── Volume: ./dist, ./nginx/nginx.conf
```

### Multi-stage Build (Backend)

```dockerfile
Stage 1: Builder
├── Install build dependencies
├── Install Python packages
└── Optimize dependencies

Stage 2: Runtime
├── Copy dependencies from builder
├── Copy application code
├── Create non-root user
└── Run application
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

```
Trigger: Push/PR to main or feature branch
│
├─→ Build Backend Job
│   ├── Checkout code
│   ├── Setup Docker Buildx
│   ├── Login to GHCR
│   ├── Build image
│   ├── Run tests
│   └── Push to registry
│
├─→ Build Frontend Job
│   ├── Checkout code
│   ├── Setup Node.js & pnpm
│   ├── Install dependencies
│   ├── Build frontend
│   ├── Create Nginx image
│   └── Push to registry
│
└─→ Test Backend Job
    ├── Start MySQL & Redis
    ├── Setup Python
    ├── Run tests
    └── Generate coverage
```

## 📈 Monitoring & Observability

### Logging

**Backend**:
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request/response logging
- Error tracking with stack traces

**Components**:
- FastAPI request logging
- Database query logging (debug mode)
- Redis operation logging
- Exception tracking

### Health Checks

**Endpoints**:
- `/api/health` - Full health check (DB + Redis)
- `/api/health/ping` - Simple ping

**Docker Health Checks**:
- Backend: HTTP request to /api/health/ping
- MySQL: mysqladmin ping
- Redis: redis-cli ping
- Frontend: nginx status

### Metrics (Future)

- Request rate
- Response times
- Error rates
- Database query performance
- Cache hit/miss ratio
- Resource utilization

## 🔮 Future Enhancements

### Short-term

1. **Authentication System**:
   - JWT-based auth
   - User management
   - Role-based access control

2. **API Rate Limiting**:
   - Redis-based rate limiter
   - Per-user/IP limits

3. **Advanced Caching**:
   - Smart cache invalidation
   - Cache warming strategies

### Medium-term

4. **Asynchronous Processing**:
   - Celery task queue
   - Background jobs
   - Large batch processing

5. **Monitoring & Alerting**:
   - Prometheus metrics
   - Grafana dashboards
   - Alert rules

6. **Testing**:
   - Unit tests (pytest)
   - Integration tests
   - E2E tests (Playwright)

### Long-term

7. **Microservices**:
   - Split into domain services
   - API Gateway (Kong, Traefik)
   - Service mesh (Istio)

8. **Advanced Features**:
   - GraphQL API
   - WebSocket support
   - Event sourcing
   - CQRS pattern

9. **Infrastructure**:
   - Kubernetes deployment
   - Auto-scaling
   - Multi-region support
   - Disaster recovery

## 📚 Technology Decisions

### Why FastAPI?

✅ High performance (async support)
✅ Automatic API documentation
✅ Type safety with Pydantic
✅ Modern Python features
✅ Easy to learn and use
✅ Great for microservices

### Why MySQL?

✅ ACID compliance
✅ Mature and stable
✅ Good performance for relational data
✅ Rich ecosystem
✅ Excellent for structured data

### Why Redis?

✅ In-memory speed
✅ Simple to use
✅ Multiple data structures
✅ Pub/Sub capabilities
✅ Clustering support

### Why Docker?

✅ Consistent environments
✅ Easy deployment
✅ Isolation
✅ Scalability
✅ DevOps friendly

## 🤝 Contributing

See [DEPLOYMENT.md](./DEPLOYMENT.md) for development setup and [backend/README.md](./backend/README.md) for backend-specific guidelines.

## 📄 License

MIT License
