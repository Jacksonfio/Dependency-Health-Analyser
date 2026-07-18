#!/bin/bash
# Quick start script for DepHealth

set -e

echo "🚀 Starting DepHealth Development Environment"

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed."; exit 1; }

# Create .env files if they don't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend/.env from example..."
    cp backend/.env.example backend/.env
fi

if [ ! -f frontend/.env.local ]; then
    echo "📝 Creating frontend/.env.local..."
    cat > frontend/.env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose -f infra/docker/docker-compose.prod.yml up -d postgres redis neo4j

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run backend migrations
echo "🔄 Running database migrations..."
docker-compose -f infra/docker/docker-compose.prod.yml run --rm backend alembic upgrade head

# Start all services
echo "🚀 Starting all services..."
docker-compose -f infra/docker/docker-compose.prod.yml up -d

echo ""
echo "✅ DepHealth is running!"
echo ""
echo "📊 Services:"
echo "   Frontend:     http://localhost:3000"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Neo4j:        http://localhost:7474 (neo4j/password)"
echo "   Flower:       http://localhost:5555"
echo ""
echo "📝 To view logs: docker-compose -f infra/docker/docker-compose.prod.yml logs -f"
echo "🛑 To stop:      docker-compose -f infra/docker/docker-compose.prod.yml down"