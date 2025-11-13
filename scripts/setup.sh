#!/bin/bash

# Combo Tool System - Quick Setup Script
# This script helps you quickly set up the development environment

set -e

echo "🚀 Combo Tool System - Setup Script"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        echo "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is installed${NC}"
}

# Check if Docker Compose is installed
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker Compose is installed${NC}"
}

# Setup environment files
setup_env() {
    echo ""
    echo "📝 Setting up environment files..."
    
    if [ ! -f backend/.env ]; then
        cp backend/.env.example backend/.env
        echo -e "${GREEN}✅ Created backend/.env${NC}"
        echo -e "${YELLOW}⚠️  Please review and update backend/.env with your settings${NC}"
    else
        echo -e "${YELLOW}⚠️  backend/.env already exists, skipping${NC}"
    fi
}

# Start services
start_services() {
    echo ""
    echo "🐳 Starting Docker services..."
    echo ""
    
    # Ask which mode
    echo "Choose deployment mode:"
    echo "1) Development mode (with hot reload)"
    echo "2) Production mode"
    read -p "Enter choice (1 or 2): " mode_choice
    
    if [ "$mode_choice" == "1" ]; then
        echo "Starting development mode..."
        docker-compose -f docker-compose.dev.yml up -d
    else
        echo "Starting production mode..."
        docker-compose up -d
    fi
    
    echo ""
    echo -e "${GREEN}✅ Services started${NC}"
}

# Wait for services
wait_for_services() {
    echo ""
    echo "⏳ Waiting for services to be ready..."
    echo "This may take a minute or two..."
    
    # Wait for MySQL
    echo -n "Waiting for MySQL..."
    for i in {1..30}; do
        if docker-compose exec -T mysql mysqladmin ping -h localhost --silent 2>/dev/null; then
            echo -e " ${GREEN}✅${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for Redis
    echo -n "Waiting for Redis..."
    for i in {1..30}; do
        if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
            echo -e " ${GREEN}✅${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for Backend
    echo -n "Waiting for Backend..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health/ping > /dev/null 2>&1; then
            echo -e " ${GREEN}✅${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
}

# Migrate data
migrate_data() {
    echo ""
    read -p "Do you want to migrate templates from JSON to MySQL? (y/n): " migrate_choice
    
    if [ "$migrate_choice" == "y" ] || [ "$migrate_choice" == "Y" ]; then
        echo "🔄 Migrating templates..."
        docker-compose exec backend python /app/../scripts/migrate_templates.py /app/../tool/templates.json
        echo -e "${GREEN}✅ Migration completed${NC}"
    else
        echo -e "${YELLOW}⏭️  Skipped migration${NC}"
    fi
}

# Show access info
show_info() {
    echo ""
    echo "=========================================="
    echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
    echo "=========================================="
    echo ""
    echo "📍 Access your services:"
    echo "   Frontend:        http://localhost"
    echo "   Backend API:     http://localhost/api"
    echo "   API Docs:        http://localhost/docs"
    echo "   Health Check:    http://localhost/api/health"
    echo ""
    echo "🗄️  Database connections:"
    echo "   MySQL:           localhost:3306"
    echo "   Redis:           localhost:6379"
    echo ""
    echo "📝 Useful commands:"
    echo "   View logs:       docker-compose logs -f"
    echo "   Stop services:   docker-compose down"
    echo "   Restart:         docker-compose restart"
    echo ""
    echo "📚 Documentation:"
    echo "   Deployment:      DEPLOYMENT.md"
    echo "   Architecture:    ARCHITECTURE.md"
    echo "   Backend README:  backend/README.md"
    echo ""
}

# Main setup flow
main() {
    echo ""
    check_docker
    check_docker_compose
    setup_env
    
    read -p "Do you want to start the services now? (y/n): " start_choice
    if [ "$start_choice" == "y" ] || [ "$start_choice" == "Y" ]; then
        start_services
        wait_for_services
        migrate_data
        show_info
    else
        echo ""
        echo -e "${YELLOW}Setup prepared. Run 'docker-compose up -d' when ready.${NC}"
    fi
}

# Run main function
main
