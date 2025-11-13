# 🚀 Quick Start Guide - Combo Tool System

## 📋 目录

- [快速启动](#快速启动)
- [手动部署](#手动部署)
- [访问服务](#访问服务)
- [常见命令](#常见命令)
- [故障排除](#故障排除)

## ⚡ 快速启动

### 方式一：使用自动化脚本（推荐）

```bash
# 1. 克隆项目并切换分支
git clone <repository-url>
cd <project-directory>
git checkout feat-split-front-back-python-docker-mysql-redis

# 2. 运行自动化设置脚本
chmod +x scripts/setup.sh
./scripts/setup.sh

# 脚本会自动：
# - 检查 Docker 和 Docker Compose
# - 配置环境变量
# - 启动所有服务
# - 等待服务就绪
# - 迁移模板数据
```

### 方式二：使用 Docker Compose

```bash
# 1. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env 文件（可选）

# 2. 启动所有服务（生产模式）
docker-compose up -d

# 或启动开发模式
docker-compose -f docker-compose.dev.yml up -d

# 3. 查看日志
docker-compose logs -f

# 4. 等待服务就绪（查看健康检查）
docker-compose ps

# 5. 迁移模板数据
docker-compose exec backend python /app/../scripts/migrate_templates.py /app/../tool/templates.json
```

## 🖥️ 手动部署

### 后端部署

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 5. 确保 MySQL 和 Redis 正在运行
# MySQL: localhost:3306
# Redis: localhost:6379

# 6. 初始化数据库
mysql -u combo_user -p combo_db < migrations/init.sql

# 7. 启动后端服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端部署

```bash
# 1. 安装依赖
pnpm install

# 2. 开发模式
pnpm run dev

# 3. 生产构建
pnpm run build

# 4. 预览生产构建
pnpm run preview
```

## 🌐 访问服务

启动成功后，您可以访问以下地址：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端应用 | http://localhost | Vue 3 管理后台 |
| 后端 API | http://localhost:8000 | FastAPI 后端服务 |
| API 文档 (Swagger) | http://localhost/docs | 交互式 API 文档 |
| API 文档 (ReDoc) | http://localhost/redoc | 另一种 API 文档样式 |
| 健康检查 | http://localhost/api/health | 服务健康状态 |
| MySQL | localhost:3306 | 数据库（用户: combo_user） |
| Redis | localhost:6379 | 缓存服务 |

### 开发模式端口

使用 `docker-compose.dev.yml` 时的端口：

- MySQL: localhost:3307
- Redis: localhost:6380
- Backend: localhost:8000

## 📝 常见命令

### Docker Compose 命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 重启特定服务
docker-compose restart backend
docker-compose restart mysql

# 查看日志
docker-compose logs -f          # 所有服务
docker-compose logs -f backend  # 后端服务
docker-compose logs -f mysql    # MySQL
docker-compose logs -f redis    # Redis

# 查看服务状态
docker-compose ps

# 进入容器
docker-compose exec backend bash
docker-compose exec mysql mysql -u combo_user -pcombo_password combo_db
docker-compose exec redis redis-cli

# 重新构建镜像
docker-compose build
docker-compose up -d --build

# 扩展后端服务
docker-compose up -d --scale backend=3
```

### 数据库命令

```bash
# 连接到 MySQL
docker-compose exec mysql mysql -u combo_user -pcombo_password combo_db

# 在 MySQL 中执行查询
docker-compose exec mysql mysql -u combo_user -pcombo_password combo_db -e "SHOW TABLES;"
docker-compose exec mysql mysql -u combo_user -pcombo_password combo_db -e "SELECT COUNT(*) FROM templates;"

# 备份数据库
docker-compose exec mysql mysqldump -u combo_user -pcombo_password combo_db > backup.sql

# 恢复数据库
docker-compose exec -T mysql mysql -u combo_user -pcombo_password combo_db < backup.sql

# 查看数据库日志
docker-compose logs mysql | tail -100
```

### Redis 命令

```bash
# 连接到 Redis
docker-compose exec redis redis-cli

# 在 Redis CLI 中：
# 查看所有键
KEYS *

# 查看特定键
GET template:1

# 清空所有缓存
FLUSHDB

# 查看 Redis 信息
INFO

# 监控命令
MONITOR
```

### 后端开发命令

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 启动开发服务器（带自动重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试（未来）
pytest tests/ -v
pytest tests/ --cov=app --cov-report=html

# 迁移模板数据
python ../scripts/migrate_templates.py ../tool/templates.json
```

### 前端开发命令

```bash
# 安装依赖
pnpm install

# 开发模式
pnpm run dev

# 构建生产版本
pnpm run build

# 预览生产构建
pnpm run preview

# 类型检查
pnpm run typecheck

# 代码检查和修复
pnpm run lint

# 生成路由
pnpm run gen-route
```

## 🐛 故障排除

### 后端无法启动

**问题**：后端容器启动失败

**解决方案**：
```bash
# 1. 查看日志
docker-compose logs backend

# 2. 检查数据库是否就绪
docker-compose logs mysql | grep "ready for connections"

# 3. 检查环境变量
docker-compose exec backend env | grep DATABASE_URL

# 4. 重新构建镜像
docker-compose build backend
docker-compose up -d backend

# 5. 检查端口占用
lsof -i :8000
# 如果端口被占用，停止占用进程或更改端口
```

### 数据库连接错误

**问题**：无法连接到 MySQL

**解决方案**：
```bash
# 1. 检查 MySQL 状态
docker-compose ps mysql

# 2. 检查 MySQL 日志
docker-compose logs mysql

# 3. 测试连接
docker-compose exec mysql mysqladmin ping -h localhost -u combo_user -pcombo_password

# 4. 重启 MySQL
docker-compose restart mysql

# 5. 等待 MySQL 完全启动（约30秒）
docker-compose logs -f mysql
```

### Redis 连接错误

**问题**：无法连接到 Redis

**解决方案**：
```bash
# 1. 检查 Redis 状态
docker-compose ps redis

# 2. 测试连接
docker-compose exec redis redis-cli ping

# 3. 重启 Redis
docker-compose restart redis
```

### 前端无法访问

**问题**：访问 http://localhost 失败

**解决方案**：
```bash
# 1. 检查 Nginx 状态
docker-compose ps frontend

# 2. 检查 Nginx 日志
docker-compose logs frontend

# 3. 确认 dist 目录存在
ls -la dist/

# 4. 如果 dist 不存在，构建前端
pnpm run build

# 5. 重启 frontend 服务
docker-compose restart frontend
```

### 端口冲突

**问题**：端口已被占用

**解决方案**：
```bash
# 查看端口占用
lsof -i :3306  # MySQL
lsof -i :6379  # Redis
lsof -i :8000  # Backend
lsof -i :80    # Frontend

# 方法1：停止占用端口的进程
kill -9 <PID>

# 方法2：修改 docker-compose.yml 中的端口映射
# 例如：将 "3306:3306" 改为 "3307:3306"
```

### 权限问题

**问题**：文件或目录权限错误

**解决方案**：
```bash
# 修复脚本权限
chmod +x scripts/setup.sh
chmod +x scripts/migrate_templates.py

# 修复 Docker volumes 权限
docker-compose down -v
docker-compose up -d
```

### 数据迁移失败

**问题**：模板数据迁移失败

**解决方案**：
```bash
# 1. 检查 JSON 文件
cat tool/templates.json | jq .

# 2. 检查数据库连接
docker-compose exec backend python -c "from app.database import engine; print(engine.connect())"

# 3. 手动运行迁移脚本
docker-compose exec backend python /app/../scripts/migrate_templates.py /app/../tool/templates.json

# 4. 检查迁移日志
docker-compose logs backend | grep migrate
```

### Docker 空间不足

**问题**：Docker 磁盘空间不足

**解决方案**：
```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷
docker volume prune

# 清理所有未使用的资源
docker system prune -a --volumes

# 查看 Docker 磁盘使用
docker system df
```

## 📚 更多文档

- [完整部署指南](DEPLOYMENT.md) - 详细的部署说明
- [架构文档](ARCHITECTURE.md) - 系统架构设计
- [项目总结](PROJECT_SUMMARY.md) - 项目重构总结
- [后端文档](backend/README.md) - 后端 API 文档

## 💡 提示

1. **首次启动**：第一次启动可能需要几分钟来下载镜像和初始化数据库
2. **健康检查**：使用 `docker-compose ps` 查看所有服务的健康状态
3. **开发模式**：使用 `docker-compose.dev.yml` 获得更好的开发体验（热重载）
4. **日志查看**：使用 `docker-compose logs -f <service>` 实时查看特定服务的日志
5. **数据持久化**：MySQL 和 Redis 数据会持久化到 Docker volumes 中

## 🆘 获取帮助

如果遇到问题：

1. 查看日志：`docker-compose logs -f`
2. 检查健康状态：`docker-compose ps`
3. 访问 API 文档：http://localhost/docs
4. 查看故障排除部分
5. 查看详细文档：[DEPLOYMENT.md](DEPLOYMENT.md)

## 🎉 验证安装

运行以下命令验证所有服务是否正常：

```bash
# 1. 检查所有服务状态
docker-compose ps

# 2. 测试后端 API
curl http://localhost/api/health/ping

# 3. 测试数据库
docker-compose exec mysql mysql -u combo_user -pcombo_password combo_db -e "SHOW TABLES;"

# 4. 测试 Redis
docker-compose exec redis redis-cli ping

# 5. 访问前端
curl http://localhost/

# 如果所有命令都成功，说明安装完成！
```

---

**祝使用愉快！** 🎊
