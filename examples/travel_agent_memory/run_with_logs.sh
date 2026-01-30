#!/bin/bash
# Run travel agent example with Agent Memory Server logs visible

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Travel Agent Memory Example Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Agent Memory Server is running
echo -e "${YELLOW}Checking Agent Memory Server...${NC}"
if ! docker ps | grep -q agent-memory-server; then
    echo -e "${RED}Error: Agent Memory Server is not running!${NC}"
    echo ""
    echo "Start it with:"
    echo "  docker start agent-memory-server"
    echo ""
    echo "Or check if it exists:"
    echo "  docker ps -a | grep agent-memory-server"
    exit 1
fi

# Check if server is responding
if ! curl -s http://localhost:8088/health > /dev/null 2>&1; then
    echo -e "${RED}Error: Agent Memory Server is not responding on port 8088!${NC}"
    echo ""
    echo "Check the logs:"
    echo "  docker logs agent-memory-server"
    exit 1
fi

echo -e "${GREEN}✓ Agent Memory Server is running${NC}"
echo ""

# Check Redis
echo -e "${YELLOW}Checking Redis...${NC}"
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}Error: Redis is not running!${NC}"
    echo ""
    echo "Start it with:"
    echo "  redis-server --port 6379 --daemonize yes"
    exit 1
fi

echo -e "${GREEN}✓ Redis is running${NC}"
echo ""

# Ask which example to run
echo -e "${YELLOW}Which example do you want to run?${NC}"
echo "  1) Simple test (2 messages, quick verification)"
echo "  2) Full travel agent WITH tools (16 messages, complete journey)"
echo "  3) Travel agent WITHOUT tools (automatic memory)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        SCRIPT="test_tools_simple.py"
        ;;
    2)
        SCRIPT="travel_agent_with_tools.py"
        ;;
    3)
        SCRIPT="travel_agent_without_tools.py"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Starting Example: $SCRIPT${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Opening Agent Memory Server logs in a new terminal...${NC}"
echo ""

# Open logs in a new terminal window (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "tell application \"Terminal\" to do script \"docker logs agent-memory-server -f --tail 50\""
    sleep 1
fi

# Run the example
echo -e "${GREEN}Running example...${NC}"
echo ""
cd "$(dirname "$0")"
uv run python "$SCRIPT"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Example completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}To view memories created:${NC}"
echo "  curl http://localhost:8088/v1/namespaces"
echo ""
echo -e "${YELLOW}To view specific user's memories:${NC}"
echo "  curl 'http://localhost:8088/v1/namespaces/NAMESPACE/users/USER_ID/memories'"
echo ""

