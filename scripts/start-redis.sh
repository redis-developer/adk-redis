#!/bin/bash

# Redis 8.4 startup script
# This script starts Redis 8.4 in a Docker container with proper health checks

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REDIS_CONTAINER_NAME="${REDIS_CONTAINER_NAME:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_IMAGE="${REDIS_IMAGE:-redis:8.4-alpine}"

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check for Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker is installed"

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    print_success "Docker daemon is running"

    echo ""
}

check_port_conflict() {
    print_header "Checking Port Availability"

    # Check if port is already in use
    if lsof -Pi :${REDIS_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        print_warning "Port ${REDIS_PORT} is already in use"

        # Check if it's our Redis container
        if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NAME}$"; then
            print_info "Redis container '${REDIS_CONTAINER_NAME}' is already running"
            return 1
        else
            print_error "Port ${REDIS_PORT} is in use by another process"
            echo ""
            echo "To find what's using the port:"
            echo "  lsof -i :${REDIS_PORT}"
            echo ""
            echo "To use a different port, set REDIS_PORT environment variable:"
            echo "  REDIS_PORT=6380 $0"
            exit 1
        fi
    fi

    print_success "Port ${REDIS_PORT} is available"
    echo ""
    return 0
}

check_existing_container() {
    print_header "Checking for Existing Container"

    # Check if container exists (running or stopped)
    if docker ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        # Check if it's running
        if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NAME}$"; then
            print_info "Container '${REDIS_CONTAINER_NAME}' is already running"
            return 1
        else
            print_warning "Container '${REDIS_CONTAINER_NAME}' exists but is stopped"
            read -p "Do you want to start the existing container? (Y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                print_info "Starting existing container..."
                docker start ${REDIS_CONTAINER_NAME}
                return 1
            else
                print_info "Removing stopped container..."
                docker rm ${REDIS_CONTAINER_NAME}
                return 0
            fi
        fi
    fi

    print_info "No existing container found"
    echo ""
    return 0
}

start_redis() {
    print_header "Starting Redis 8.4"

    print_info "Starting Redis container: ${REDIS_CONTAINER_NAME}"
    print_info "Port: ${REDIS_PORT}"
    print_info "Image: ${REDIS_IMAGE}"
    echo ""

    docker run -d \
        --name ${REDIS_CONTAINER_NAME} \
        -p ${REDIS_PORT}:6379 \
        --health-cmd "redis-cli ping" \
        --health-interval 5s \
        --health-timeout 3s \
        --health-retries 5 \
        ${REDIS_IMAGE}

    print_success "Redis container started"
    echo ""
}



verify_redis() {
    print_header "Verifying Redis"

    print_info "Waiting for Redis to be healthy..."

    # Wait up to 30 seconds for container to be healthy
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker inspect --format='{{.State.Health.Status}}' ${REDIS_CONTAINER_NAME} 2>/dev/null | grep -q "healthy"; then
            print_success "Redis is healthy and ready"
            echo ""
            return 0
        fi

        sleep 1
        attempt=$((attempt + 1))
        echo -n "."
    done

    echo ""
    print_error "Redis failed to become healthy within 30 seconds"
    echo ""
    echo "Check container logs:"
    echo "  docker logs ${REDIS_CONTAINER_NAME}"
    exit 1
}

test_redis_connection() {
    print_header "Testing Redis Connection"

    # Test with redis-cli if available
    if command -v redis-cli &> /dev/null; then
        print_info "Testing connection with redis-cli..."
        if redis-cli -p ${REDIS_PORT} ping 2>/dev/null | grep -q "PONG"; then
            print_success "Redis connection test successful (redis-cli)"
        else
            print_warning "redis-cli test failed, but container may still be working"
        fi
    fi

    # Test with docker exec
    print_info "Testing connection via Docker..."
    if docker exec ${REDIS_CONTAINER_NAME} redis-cli ping | grep -q "PONG"; then
        print_success "Redis connection test successful (docker exec)"
    else
        print_error "Redis connection test failed"
        exit 1
    fi

    echo ""
}

print_next_steps() {
    print_header "Redis is Ready!"

    echo -e "${GREEN}Redis 8.4 is now running successfully.${NC}"
    echo ""
    echo "Connection details:"
    echo -e "  ${BLUE}Host:${NC} localhost"
    echo -e "  ${BLUE}Port:${NC} ${REDIS_PORT}"
    echo -e "  ${BLUE}Container:${NC} ${REDIS_CONTAINER_NAME}"
    echo ""
    echo "Useful commands:"
    echo ""
    echo "  Test connection:"
    echo -e "    ${BLUE}redis-cli -p ${REDIS_PORT} ping${NC}"
    echo -e "    ${BLUE}docker exec ${REDIS_CONTAINER_NAME} redis-cli ping${NC}"
    echo ""
    echo "  View logs:"
    echo -e "    ${BLUE}docker logs ${REDIS_CONTAINER_NAME}${NC}"
    echo -e "    ${BLUE}docker logs -f ${REDIS_CONTAINER_NAME}${NC}  # Follow logs"
    echo ""
    echo "  Check status:"
    echo -e "    ${BLUE}docker ps | grep ${REDIS_CONTAINER_NAME}${NC}"
    echo ""
    echo "  Stop Redis:"
    echo -e "    ${BLUE}docker stop ${REDIS_CONTAINER_NAME}${NC}"
    echo ""
    echo "  Restart Redis:"
    echo -e "    ${BLUE}docker restart ${REDIS_CONTAINER_NAME}${NC}"
    echo ""
    echo "  Remove Redis (stops and deletes container):"
    echo -e "    ${BLUE}docker rm -f ${REDIS_CONTAINER_NAME}${NC}"
    echo ""
    echo -e "${BLUE}Redis 8.4 Features:${NC}"
    echo "  ✓ Redis Query Engine (evolved from RediSearch)"
    echo "  ✓ Native vector search"
    echo "  ✓ Full-text search"
    echo "  ✓ JSON operations"
    echo ""
}

# Main execution
main() {
    echo ""
    print_header "Redis 8.4 Startup Script"
    echo ""

    check_prerequisites

    # Check if Redis is already running
    if ! check_port_conflict; then
        verify_redis
        test_redis_connection
        print_next_steps
        exit 0
    fi

    # Check for existing container
    if ! check_existing_container; then
        verify_redis
        test_redis_connection
        print_next_steps
        exit 0
    fi

    # Start new Redis container
    start_redis
    verify_redis
    test_redis_connection
    print_next_steps
}

# Run main function
main
