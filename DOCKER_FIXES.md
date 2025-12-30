# Docker Deployment Fixes

## Overview
This project has been updated to permanently fix Docker read-only filesystem issues that were causing deployment failures.

## Changes Made

### 1. Dockerfile Updates
- **Dockerfile**: Added creation of all necessary runtime directories with proper permissions
- **Dockerfile.optimized**: Updated user ID to 1000:1000 and added all required directories

### 2. Docker Compose Updates
- **docker-compose.yml**: Added user mapping and read-write volume mounts
- **docker-compose.prod.yml**: Updated user IDs and ensured volume mounts are read-write

### 3. Deployment Script
- **deploy_with_fix.sh**: New deployment script that prepares host directories with correct permissions before starting containers

### 4. Production Deployment
- **deploy_to_vps_complete.sh**: Updated to use the new deployment script

## How It Works

1. **Host Directory Preparation**: The deployment script creates necessary directories on the host with proper permissions
2. **User Mapping**: Containers run with user ID 1000:1000 matching the host user
3. **Volume Mounts**: All volume mounts are explicitly set to read-write (:rw)
4. **Directory Creation**: Dockerfiles create all required directories with correct ownership

## Usage

### Local Development
```bash
./deploy_with_fix.sh
```

### Production Deployment
```bash
./deploy_to_vps_complete.sh
```

## Key Fixes

- ✅ User ID consistency (1000:1000) between host and container
- ✅ All volume mounts are read-write
- ✅ All required directories are pre-created with correct permissions
- ✅ Host directories are prepared before container startup
- ✅ No more read-only filesystem errors

## Emergency Fix for Permission Errors

If you still get "No such file or directory" errors after deployment, run:

```bash
./emergency_docker_fix.sh
```

This script will:
- Stop and remove old containers
- Delete old images to force rebuild
- Fix host directory permissions
- Rebuild with correct user mapping

## Troubleshooting

### Check User IDs
Ensure your host user has UID/GID 1000:
```bash
id -u  # Should show 1000
id -g  # Should show 1000
```

### Manual Permission Fix
If needed, fix permissions manually:
```bash
sudo chown -R 1000:1000 ./bot_persistence
sudo chown -R 1000:1000 ./logs
sudo chown -R 1000:1000 ./artifacts
sudo chown -R 1000:1000 ./reports
```

### Container User Verification
Check what user the container is running as:
```bash
docker exec ai-bot-container id
# Should show: uid=1000(trader) gid=1000(trader)
```