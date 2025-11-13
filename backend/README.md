# Combo Tool Backend API

Backend API service for the Combo Tool - Product combination generation system.

## 🚀 Tech Stack

- **Framework**: FastAPI 0.115+
- **Database**: MySQL 8.0 with SQLAlchemy ORM
- **Cache**: Redis 7
- **Python**: 3.11+
- **Containerization**: Docker & Docker Compose

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/                 # API routes
│   │   └── v1/             # API version 1
│   │       ├── templates.py  # Template management endpoints
│   │       ├── combos.py     # Combo generation endpoints
│   │       └── health.py     # Health check endpoints
│   ├── models/             # SQLAlchemy models
│   │   └── template.py     # Template, Combo, Item models
│   ├── schemas/            # Pydantic schemas
│   │   ├── template.py     # Template schemas
│   │   └── response.py     # Response schemas
│   ├── services/           # Business logic
│   │   ├── template_service.py
│   │   └── combo_service.py
│   ├── utils/              # Utilities
│   │   ├── redis_client.py
│   │   └── combo_generator.py
│   ├── config.py           # Configuration management
│   ├── database.py         # Database connection
│   └── main.py             # FastAPI application
├── migrations/             # Database migrations
│   └── init.sql           # Initial schema
├── tests/                  # Tests
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
└── .env.example           # Environment variables template
```

## 🛠️ Setup

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Redis 7+
- Docker & Docker Compose (optional)

### Local Development

1. **Clone the repository**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**
   ```bash
   # Run init.sql on your MySQL server
   mysql -u root -p < migrations/init.sql
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health check: http://localhost:8000/api/health

### Docker Development

1. **Start all services**
   ```bash
   cd ..
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **View logs**
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f backend
   ```

3. **Stop services**
   ```bash
   docker-compose -f docker-compose.dev.yml down
   ```

## 📊 Database Migration

### Migrate templates from JSON to MySQL

```bash
cd scripts
python migrate_templates.py ../tool/templates.json
```

Or with custom database URL:
```bash
python migrate_templates.py ../tool/templates.json --database-url mysql+pymysql://user:pass@localhost:3306/combo_db
```

## 🔌 API Endpoints

### Health Check
- `GET /api/health` - Health check with database and Redis status
- `GET /api/health/ping` - Simple ping endpoint

### Templates
- `GET /api/v1/templates` - List all templates (with pagination and filters)
- `GET /api/v1/templates/{id}` - Get template by ID
- `POST /api/v1/templates` - Create new template
- `PUT /api/v1/templates/{id}` - Update template
- `DELETE /api/v1/templates/{id}` - Delete template

### Combos
- `POST /api/v1/combos/generate` - Generate combo products

## 📝 API Examples

### Create a Template

```bash
curl -X POST "http://localhost:8000/api/v1/templates" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Template",
    "description": "Test description",
    "is_active": true,
    "combos": [
      {
        "prefix": "TEST_",
        "sort_order": 0,
        "items": [
          {
            "product_code": "PROD001",
            "quantity": 1,
            "sale_price": 100.0,
            "base_price": 90.0,
            "cost_price": 50.0
          }
        ]
      }
    ]
  }'
```

### Generate Combos

```bash
curl -X POST "http://localhost:8000/api/v1/combos/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "main_product_codes": ["M001", "M002"],
    "main_product_specs": ["Blue-L", "Blue-M"],
    "main_product_quantities": [1, 1],
    "main_product_sale_prices": [100.0, 100.0],
    "main_product_base_prices": [90.0, 90.0],
    "main_product_cost_prices": [50.0, 50.0]
  }'
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## 🔒 Security

- JWT authentication (to be implemented)
- API rate limiting
- Input validation with Pydantic
- SQL injection protection with SQLAlchemy ORM
- CORS configuration
- Secure headers

## 📈 Performance

- **Redis caching**: Hot templates cached for 1 hour
- **Database connection pooling**: 20 connections with 10 overflow
- **Async operations**: FastAPI async endpoints
- **Multi-worker support**: Uvicorn with 4 workers

## 🔧 Configuration

Environment variables in `.env`:

```env
# Application
APP_NAME=Combo Tool API
DEBUG=false
ENVIRONMENT=production

# Database
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/combo_db
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Security
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 📦 Deployment

### Production Deployment

```bash
# Build and start production containers
docker-compose up -d

# Check container status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### CI/CD

GitHub Actions automatically:
- Builds Docker images on push
- Runs tests
- Pushes images to GitHub Container Registry
- Tags images with version/branch/sha

## 📚 Documentation

- API Documentation: `/docs` (Swagger UI)
- Alternative API Docs: `/redoc` (ReDoc)
- OpenAPI Schema: `/openapi.json`

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Submit a pull request

## 📄 License

MIT License

## 🔗 Links

- Frontend Repository: [SoybeanAdmin](../README.md)
- Docker Hub: (to be added)
- Documentation: (to be added)
