#!/bin/bash

# Voicely Backend Deployment Script
# Tự động hóa quá trình build và upload lên server

set -e  # Exit on error

echo "🚀 Voicely Backend Deployment Script"
echo "===================================="

# Configuration
SERVER_USER="${SERVER_USER:-ubuntu}"
SERVER_HOST="${SERVER_HOST}"
DEPLOY_PATH="${DEPLOY_PATH:-/home/ubuntu/voicely-app}"
TAR_FILE="voicely-be-$(date +%Y%m%d-%H%M%S).tar.gz"

# Check if server host is provided
if [ -z "$SERVER_HOST" ]; then
    echo "❌ Error: SERVER_HOST is not set"
    echo "Usage: SERVER_HOST=your-server-ip ./deploy.sh"
    exit 1
fi

echo "📦 Step 1: Creating deployment package..."
tar --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='ENV' \
    --exclude='uploads/*' \
    --exclude='tests' \
    --exclude='.vscode' \
    --exclude='.idea' \
    --exclude='*.log' \
    --exclude='.DS_Store' \
    -czf "$TAR_FILE" \
    --exclude="$TAR_FILE" \
    .

echo "✅ Package created: $TAR_FILE ($(du -h $TAR_FILE | cut -f1))"

echo ""
echo "📤 Step 2: Uploading to server..."
scp "$TAR_FILE" "$SERVER_USER@$SERVER_HOST:/tmp/"

echo ""
echo "🔧 Step 3: Deploying on server..."
ssh "$SERVER_USER@$SERVER_HOST" << EOF
    set -e
    
    # Create deploy directory if not exists
    mkdir -p "$DEPLOY_PATH"
    
    # Backup old deployment (if exists)
    if [ -d "$DEPLOY_PATH/app" ]; then
        echo "📦 Backing up old deployment..."
        tar -czf "$DEPLOY_PATH/backup-\$(date +%Y%m%d-%H%M%S).tar.gz" \
            -C "$DEPLOY_PATH" \
            --exclude='*.tar.gz' \
            . || true
    fi
    
    # Extract new deployment
    echo "📂 Extracting new deployment..."
    tar -xzf "/tmp/$TAR_FILE" -C "$DEPLOY_PATH"
    
    # Cleanup
    rm "/tmp/$TAR_FILE"
    
    # Set permissions
    chmod +x "$DEPLOY_PATH"/*.sh || true
    
    echo "✅ Files deployed to $DEPLOY_PATH"
    
    # Stop existing containers
    cd "$DEPLOY_PATH"
    if [ -f "docker-compose.yml" ]; then
        echo "🛑 Stopping existing containers..."
        docker-compose down || true
    fi
    
    # Start containers
    echo "🚀 Starting containers..."
    docker-compose up -d --build
    
    echo ""
    echo "✅ Deployment completed!"
    echo "📊 Container status:"
    docker-compose ps
EOF

echo ""
echo "🧹 Step 4: Cleanup local files..."
rm "$TAR_FILE"

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📝 Next steps:"
echo "  1. SSH to server: ssh $SERVER_USER@$SERVER_HOST"
echo "  2. Check logs: cd $DEPLOY_PATH && docker-compose logs -f"
echo "  3. Access API: http://$SERVER_HOST:8000/docs"
echo ""
