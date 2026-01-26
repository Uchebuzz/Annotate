#!/bin/bash
# Script to push an empty commit to keep the repository active

cd /app || exit 1

# Check if .git directory exists
if [ ! -d ".git" ]; then
    echo "Warning: .git directory not found. Skipping git push."
    exit 0
fi

# Configure git if not already configured
git config user.name "Docker Container" || true
git config user.email "docker@localhost" || true

# Create empty commit with timestamp
git commit --allow-empty -m "chore: keep alive [$(date -u +'%Y-%m-%d %H:%M:%S UTC')]" || {
    echo "Warning: Failed to create commit. Repository may not be initialized or already up to date."
    exit 0
}

# Push to origin
git push origin HEAD || {
    echo "Warning: Failed to push. This is normal if running locally without git credentials or if already up to date."
    exit 0  # Don't fail the cron job if push fails
}

