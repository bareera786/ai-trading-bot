#!/bin/bash
# Production deployment script for optimized Docker setup

set -e

echo "🚀 Starting AI Trading Bot Production Deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="ai-trading-bot"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if .env file exists
    if [ ! -f "config/deploy.env" ]; then
        log_warn "config/deploy.env not found. Copying from example..."
        cp config/deploy.env.example config/deploy.env
        log_error "Please edit config/deploy.env with your production settings before continuing."
        exit 1
    fi

    log_info "Dependencies check passed."
}

create_backup() {
    log_info "Creating backup of current state..."

    mkdir -p "$BACKUP_DIR"

    # Backup database if running
    if docker ps | grep -q "${PROJECT_NAME}-postgres"; then
        log_info "Backing up PostgreSQL database..."
        docker exec ${PROJECT_NAME}-postgres pg_dump -U trading_user trading_bot > "$BACKUP_DIR/database.sql" 2>/dev/null || true
    fi

    # Backup Redis data if running
    if docker ps | grep -q "${PROJECT_NAME}-redis"; then
        log_info "Backing up Redis data..."
        docker exec ${PROJECT_NAME}-redis redis-cli SAVE
        docker cp ${PROJECT_NAME}-redis:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb" 2>/dev/null || true
    fi

    # Backup bot persistence
    if [ -d "bot_persistence" ]; then
        cp -r bot_persistence "$BACKUP_DIR/"
    fi

    log_info "Backup created at: $BACKUP_DIR"
}

stop_services() {
    log_info "Stopping existing services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down || true
}

build_and_deploy() {
    log_info "Building and deploying services..."

    # Build with no cache for clean builds
    log_info "Building Docker images..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache

    # Start services
    log_info "Starting services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    max_attempts=30
    attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "healthy"; then
            log_info "Services are healthy!"
            break
        fi

        log_info "Waiting... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "Services failed to become healthy within timeout."
        show_logs
        exit 1
    fi
}

run_migrations() {
    log_info "Running database migrations..."

    # Wait for database to be ready
    docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres sh -c 'while ! pg_isready -U trading_user -d trading_bot; do sleep 1; done'

    # Run migrations if they exist
    if [ -f "scripts/migrate_db.py" ]; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T ai-trading-bot python scripts/migrate_db.py
    fi
}

run_health_checks() {
    log_info "Running health checks..."

    # Test application health endpoint
    max_attempts=10
    attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
            log_info "Application health check passed!"
            break
        fi

        log_info "Health check failed, retrying... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "Application health check failed."
        show_logs
        exit 1
    fi
}

show_logs() {
    log_info "Showing recent logs..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail=50
}

cleanup_old_images() {
    log_info "Cleaning up old Docker images..."

    # Remove dangling images
    docker image prune -f

    # Remove unused images older than 24 hours
    docker image prune -a --filter "until=24h" -f
}

show_deployment_info() {
    log_info "Deployment completed successfully!"
    echo ""
    echo "📊 Deployment Summary:"
    echo "  🌐 Application: http://localhost:5000"
    echo "  🐘 PostgreSQL: localhost:5432"
    echo "  🔴 Redis: localhost:6379"
    echo "  📊 Grafana (if enabled): http://localhost:3000"
    echo "  📈 Prometheus (if enabled): http://localhost:9090"
    echo ""
    echo "🔧 Useful commands:"
    echo "  View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo "  Stop services: docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "  Restart app: docker-compose -f $DOCKER_COMPOSE_FILE restart ai-trading-bot"
    echo "  Shell access: docker-compose -f $DOCKER_COMPOSE_FILE exec ai-trading-bot bash"
    echo ""
    echo "💾 Backup location: $BACKUP_DIR"
}

# Main deployment flow
main() {
    echo "🤖 AI Trading Bot - Production Deployment Script"
    echo "=============================================="

    check_dependencies
    create_backup
    stop_services
    build_and_deploy
    run_migrations
    run_health_checks
    cleanup_old_images
    show_deployment_info

    log_info "🎉 Deployment completed successfully!"
}

# Handle command line arguments
case "${1:-}" in
    "backup")
        create_backup
        ;;
    "stop")
        stop_services
        ;;
    "logs")
        show_logs
        ;;
    "health")
        run_health_checks
        ;;
    *)
        main
        ;;
esac