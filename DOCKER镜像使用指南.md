# Docker 镜像使用指南

## 📦 镜像说明

GitHub Actions 工作流会自动构建并推送两个 Docker 镜像到 GitHub Container Registry (ghcr.io)：

1. **后端镜像**: `ghcr.io/<你的用户名>/soybean-admin/backend:latest`
2. **前端镜像**: `ghcr.io/<你的用户名>/soybean-admin/frontend:latest`

> 注意：将 `<你的用户名>` 替换为实际的 GitHub 用户名（例如：ollma167）

## 🏷️ 镜像标签说明

工作流会为每个镜像生成多个标签：

- `latest` - 最新版本（main分支）
- `feat-split-front-back-python-docker-mysql-redis` - 功能分支名称
- `sha-<commit>` - Git提交的SHA值
- `v1.0.0` - 版本标签（如果有tag）

## 🔐 镜像访问权限

### 公开镜像（推荐用于演示）

如果镜像设为公开，可以直接拉取：

```bash
docker pull ghcr.io/<你的用户名>/soybean-admin/backend:latest
docker pull ghcr.io/<你的用户名>/soybean-admin/frontend:latest
```

### 私有镜像（需要认证）

如果镜像是私有的，需要先登录：

```bash
# 创建 GitHub Personal Access Token (PAT)
# 访问：https://github.com/settings/tokens
# 权限：read:packages

# 登录到 GitHub Container Registry
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# 拉取镜像
docker pull ghcr.io/<你的用户名>/soybean-admin/backend:latest
docker pull ghcr.io/<你的用户名>/soybean-admin/frontend:latest
```

## 🚀 快速开始

### 方式一：使用 Docker Compose（推荐）

创建 `docker-compose.prod.yml` 文件：

```yaml
version: '3.8'

services:
  # 后端服务
  backend:
    image: ghcr.io/<你的用户名>/soybean-admin/backend:latest
    container_name: combo-tool-backend
    ports:
      - "8000:8000"
    environment:
      - APP_NAME=Combo Tool API
      - DEBUG=false
      - ENVIRONMENT=production
      - DATABASE_URL=mysql+pymysql://combo_user:combo_password@mysql:3306/combo_db
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY:-your-secret-key-change-in-production}
      - CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:80
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - combo-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/api/health/ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # MySQL 数据库
  mysql:
    image: mysql:8.0
    container_name: combo-tool-mysql
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpassword}
      MYSQL_DATABASE: combo_db
      MYSQL_USER: combo_user
      MYSQL_PASSWORD: combo_password
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped
    networks:
      - combo-network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD:-rootpassword}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    command: --default-authentication-plugin=mysql_native_password --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  # Redis 缓存
  redis:
    image: redis:7-alpine
    container_name: combo-tool-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - combo-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

  # 前端服务（可选，如果已构建前端镜像）
  frontend:
    image: ghcr.io/<你的用户名>/soybean-admin/frontend:latest
    container_name: combo-tool-frontend
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - combo-network
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mysql_data:
    driver: local
  redis_data:
    driver: local

networks:
  combo-network:
    driver: bridge
```

**启动服务：**

```bash
# 创建 .env 文件配置密码
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
MYSQL_ROOT_PASSWORD=$(openssl rand -hex 16)
EOF

# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 方式二：单独运行容器

#### 1. 启动 MySQL

```bash
docker run -d \
  --name combo-mysql \
  --network combo-network \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=combo_db \
  -e MYSQL_USER=combo_user \
  -e MYSQL_PASSWORD=combo_password \
  -p 3306:3306 \
  -v mysql_data:/var/lib/mysql \
  mysql:8.0 \
  --default-authentication-plugin=mysql_native_password \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci
```

#### 2. 启动 Redis

```bash
docker run -d \
  --name combo-redis \
  --network combo-network \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine \
  redis-server --appendonly yes
```

#### 3. 启动后端

```bash
# 创建网络（如果还没创建）
docker network create combo-network

# 运行后端容器
docker run -d \
  --name combo-backend \
  --network combo-network \
  -p 8000:8000 \
  -e DATABASE_URL=mysql+pymysql://combo_user:combo_password@combo-mysql:3306/combo_db \
  -e REDIS_URL=redis://combo-redis:6379/0 \
  -e SECRET_KEY=your-secret-key \
  -e CORS_ORIGINS=http://localhost:3000,http://localhost:5173 \
  ghcr.io/<你的用户名>/soybean-admin/backend:latest
```

#### 4. 启动前端（可选）

```bash
docker run -d \
  --name combo-frontend \
  --network combo-network \
  -p 80:80 \
  ghcr.io/<你的用户名>/soybean-admin/frontend:latest
```

## 🔧 配置说明

### 环境变量

后端容器支持以下环境变量：

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `APP_NAME` | 应用名称 | Combo Tool API | 否 |
| `DEBUG` | 调试模式 | false | 否 |
| `ENVIRONMENT` | 环境（production/development） | production | 否 |
| `DATABASE_URL` | 数据库连接URL | - | 是 |
| `REDIS_URL` | Redis连接URL | - | 是 |
| `SECRET_KEY` | 密钥（用于加密） | - | 是 |
| `CORS_ORIGINS` | 允许的跨域源 | - | 是 |
| `LOG_LEVEL` | 日志级别 | INFO | 否 |

### 数据库连接格式

```
mysql+pymysql://用户名:密码@主机:端口/数据库名

例如：
mysql+pymysql://combo_user:combo_password@mysql:3306/combo_db
```

### Redis 连接格式

```
redis://主机:端口/数据库编号

例如：
redis://redis:6379/0
```

## 📊 服务访问

启动成功后，可以访问以下地址：

| 服务 | 地址 | 说明 |
|------|------|------|
| 后端 API | http://localhost:8000 | FastAPI 后端服务 |
| API 文档 | http://localhost:8000/docs | Swagger UI 文档 |
| API 文档 | http://localhost:8000/redoc | ReDoc 文档 |
| 健康检查 | http://localhost:8000/api/health | 健康状态 |
| 前端应用 | http://localhost | Vue 前端（如果启动了） |

## 🛠️ 常用操作

### 查看容器日志

```bash
# 查看后端日志
docker logs -f combo-backend

# 查看最近100行日志
docker logs --tail 100 combo-backend

# 使用 docker-compose
docker-compose -f docker-compose.prod.yml logs -f backend
```

### 进入容器

```bash
# 进入后端容器
docker exec -it combo-backend bash

# 进入MySQL容器
docker exec -it combo-mysql mysql -u combo_user -pcombo_password combo_db
```

### 数据库初始化

```bash
# 方法1：使用 docker exec
docker exec -i combo-mysql mysql -u combo_user -pcombo_password combo_db < backend/migrations/init.sql

# 方法2：进入容器后执行
docker exec -it combo-mysql bash
mysql -u combo_user -pcombo_password combo_db
SOURCE /path/to/init.sql;
```

### 数据迁移

如果需要迁移 templates.json 到数据库：

```bash
# 将迁移脚本和数据文件复制到容器
docker cp scripts/migrate_templates.py combo-backend:/app/migrate_templates.py
docker cp tool/templates.json combo-backend:/app/templates.json

# 执行迁移
docker exec -it combo-backend python migrate_templates.py templates.json
```

### 数据备份

```bash
# 备份 MySQL 数据库
docker exec combo-mysql mysqldump -u combo_user -pcombo_password combo_db > backup_$(date +%Y%m%d).sql

# 备份 Redis 数据
docker exec combo-redis redis-cli --rdb /data/dump.rdb
docker cp combo-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

### 数据恢复

```bash
# 恢复 MySQL 数据库
docker exec -i combo-mysql mysql -u combo_user -pcombo_password combo_db < backup.sql

# 恢复 Redis 数据
docker cp redis_backup.rdb combo-redis:/data/dump.rdb
docker restart combo-redis
```

### 更新镜像

```bash
# 拉取最新镜像
docker pull ghcr.io/<你的用户名>/soybean-admin/backend:latest
docker pull ghcr.io/<你的用户名>/soybean-admin/frontend:latest

# 使用 docker-compose 更新
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 清理旧镜像
docker image prune -a
```

### 停止和删除服务

```bash
# 停止服务
docker-compose -f docker-compose.prod.yml stop

# 停止并删除容器
docker-compose -f docker-compose.prod.yml down

# 停止并删除容器和数据卷（警告：会删除所有数据）
docker-compose -f docker-compose.prod.yml down -v
```

## 🔍 健康检查

### 检查服务状态

```bash
# 检查所有容器状态
docker ps

# 使用 docker-compose 检查
docker-compose -f docker-compose.prod.yml ps

# 检查后端健康
curl http://localhost:8000/api/health

# 检查后端 ping
curl http://localhost:8000/api/health/ping
```

### 检查数据库连接

```bash
# 测试 MySQL 连接
docker exec combo-mysql mysqladmin ping -h localhost -u combo_user -pcombo_password

# 查看数据库表
docker exec combo-mysql mysql -u combo_user -pcombo_password combo_db -e "SHOW TABLES;"
```

### 检查 Redis 连接

```bash
# 测试 Redis 连接
docker exec combo-redis redis-cli ping

# 查看 Redis 信息
docker exec combo-redis redis-cli INFO
```

## 🐛 故障排除

### 问题1：容器无法启动

**症状**：容器启动后立即退出

**解决方案**：

```bash
# 查看容器日志
docker logs combo-backend

# 检查环境变量
docker inspect combo-backend | grep -A 20 Env

# 尝试交互式运行
docker run -it --rm ghcr.io/<你的用户名>/soybean-admin/backend:latest bash
```

### 问题2：数据库连接失败

**症状**：后端日志显示数据库连接错误

**解决方案**：

```bash
# 1. 检查 MySQL 是否运行
docker ps | grep mysql

# 2. 检查 MySQL 日志
docker logs combo-mysql

# 3. 测试数据库连接
docker exec combo-mysql mysqladmin ping -h localhost -u combo_user -pcombo_password

# 4. 确保网络配置正确
docker network inspect combo-network

# 5. 重启 MySQL
docker restart combo-mysql

# 等待 MySQL 完全启动后重启后端
sleep 30
docker restart combo-backend
```

### 问题3：Redis 连接失败

**症状**：后端日志显示 Redis 连接错误

**解决方案**：

```bash
# 1. 检查 Redis 是否运行
docker ps | grep redis

# 2. 测试 Redis 连接
docker exec combo-redis redis-cli ping

# 3. 重启 Redis
docker restart combo-redis
docker restart combo-backend
```

### 问题4：端口被占用

**症状**：启动时提示端口已被使用

**解决方案**：

```bash
# 查看端口占用
lsof -i :8000  # 后端
lsof -i :3306  # MySQL
lsof -i :6379  # Redis

# 停止占用端口的进程
kill -9 <PID>

# 或者修改端口映射
# 编辑 docker-compose.prod.yml，将端口改为其他值
# 例如：-p 8001:8000
```

### 问题5：镜像拉取失败

**症状**：无法拉取镜像

**解决方案**：

```bash
# 1. 检查镜像是否存在
# 访问：https://github.com/<你的用户名>?tab=packages

# 2. 确保已登录（私有镜像）
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# 3. 检查网络连接
ping ghcr.io

# 4. 使用国内镜像加速（可选）
# 配置 Docker daemon.json
```

## 📝 最佳实践

### 1. 生产环境部署

```bash
# 使用强密码
SECRET_KEY=$(openssl rand -hex 32)
MYSQL_ROOT_PASSWORD=$(openssl rand -hex 32)

# 限制端口暴露（不要暴露 MySQL 和 Redis）
# 在 docker-compose.yml 中删除端口映射

# 使用 HTTPS
# 配置 SSL 证书和 Nginx 反向代理
```

### 2. 资源限制

在 `docker-compose.prod.yml` 中添加资源限制：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 3. 日志管理

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. 自动重启

```yaml
services:
  backend:
    restart: unless-stopped
```

### 5. 健康检查

确保所有服务都配置了健康检查：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/ping"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## 🔗 相关链接

- **GitHub Container Registry**: https://github.com/<你的用户名>?tab=packages
- **Docker Hub**: https://hub.docker.com/
- **项目仓库**: https://github.com/<你的用户名>/soybean-admin
- **问题反馈**: https://github.com/<你的用户名>/soybean-admin/issues

## 📞 获取帮助

如果遇到问题：

1. 查看日志：`docker logs -f <容器名>`
2. 检查健康状态：`curl http://localhost:8000/api/health`
3. 查看详细文档：[QUICK_START.md](QUICK_START.md)
4. 提交 Issue：GitHub Issues

## 🎉 总结

使用 GitHub Actions 自动构建的 Docker 镜像，您可以：

- ✅ **快速部署**：无需本地构建，直接拉取使用
- ✅ **版本管理**：通过标签管理不同版本
- ✅ **持续集成**：代码推送后自动构建新镜像
- ✅ **多平台支持**：支持 amd64 架构
- ✅ **生产就绪**：经过优化的多阶段构建

祝使用愉快！🚀
