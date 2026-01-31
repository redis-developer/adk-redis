#!/bin/bash

# Setup script for Agent Memory Server with bug fix
# This script builds Agent Memory Server from source until the next official release
# includes the fix for non-OpenAI provider support.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/redis/agent-memory-server.git"
BUILD_DIR="${BUILD_DIR:-/tmp/agent-memory-server}"
IMAGE_TAG="${IMAGE_TAG:-agent-memory-server:latest-fix}"

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
    
    # Check for git
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed. Please install Git first."
        exit 1
    fi
    print_success "Git is installed"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    print_success "Docker daemon is running"
    
    echo ""
}

clone_repository() {
    print_header "Cloning Agent Memory Server Repository"
    
    if [ -d "$BUILD_DIR" ]; then
        print_warning "Directory $BUILD_DIR already exists"
        read -p "Do you want to remove it and clone fresh? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing existing directory..."
            rm -rf "$BUILD_DIR"
        else
            print_info "Using existing directory. Pulling latest changes..."
            cd "$BUILD_DIR"
            git pull origin main
            cd - > /dev/null
            return 0
        fi
    fi
    
    print_info "Cloning repository to $BUILD_DIR..."
    git clone "$REPO_URL" "$BUILD_DIR"
    print_success "Repository cloned successfully"
    
    # Show the latest commit
    cd "$BUILD_DIR"
    COMMIT_HASH=$(git rev-parse --short HEAD)
    COMMIT_MSG=$(git log -1 --pretty=%B | head -n 1)
    print_info "Latest commit: $COMMIT_HASH - $COMMIT_MSG"
    cd - > /dev/null
    
    echo ""
}

build_image() {
    print_header "Building Docker Image"
    
    print_info "Building image: $IMAGE_TAG"
    print_info "This may take a few minutes..."
    
    cd "$BUILD_DIR"
    
    if docker build -t "$IMAGE_TAG" .; then
        print_success "Docker image built successfully: $IMAGE_TAG"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
    
    cd - > /dev/null
    echo ""
}

verify_image() {
    print_header "Verifying Image"
    
    if docker images | grep -q "agent-memory-server.*latest-fix"; then
        print_success "Image verified:"
        docker images | grep "agent-memory-server.*latest-fix" | head -n 1
    else
        print_error "Image verification failed"
        exit 1
    fi
    
    echo ""
}

print_next_steps() {
    print_header "Setup Complete!"
    
    echo -e "${GREEN}The Agent Memory Server image has been built successfully.${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. For Docker Compose (examples/travel_agent_memory):"
    echo -e "   ${BLUE}cd examples/travel_agent_memory${NC}"
    echo -e "   ${BLUE}docker compose up -d${NC}"
    echo ""
    echo "2. For manual Docker setup (examples/simple_redis_memory):"
    echo -e "   ${BLUE}docker run -d --name agent-memory-server -p 8000:8000 \\${NC}"
    echo -e "   ${BLUE}  -e REDIS_URL=redis://host.docker.internal:6379 \\${NC}"
    echo -e "   ${BLUE}  -e GEMINI_API_KEY=your-api-key \\${NC}"
    echo -e "   ${BLUE}  -e GENERATION_MODEL=gemini/gemini-2.0-flash-exp \\${NC}"
    echo -e "   ${BLUE}  -e EMBEDDING_MODEL=gemini/text-embedding-004 \\${NC}"
    echo -e "   ${BLUE}  -e EXTRACTION_DEBOUNCE_SECONDS=30 \\${NC}"
    echo -e "   ${BLUE}  $IMAGE_TAG \\${NC}"
    echo -e "   ${BLUE}  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio${NC}"
    echo ""
    echo -e "${YELLOW}Note: This is a temporary workaround until the next official release.${NC}"
    echo -e "${YELLOW}Once released, you can use: redislabs/agent-memory-server:latest${NC}"
    echo ""
}

# Main execution
main() {
    echo ""
    print_header "Agent Memory Server Setup Script"
    echo ""
    print_info "This script will:"
    echo "  1. Clone the Agent Memory Server repository"
    echo "  2. Build a Docker image with the latest bug fixes"
    echo "  3. Tag it as: $IMAGE_TAG"
    echo ""
    print_warning "This is temporary until the next official release includes the fix."
    echo ""
    
    check_prerequisites
    clone_repository
    build_image
    verify_image
    print_next_steps
}

# Run main function
main

