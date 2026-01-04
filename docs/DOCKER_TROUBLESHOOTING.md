# Docker Troubleshooting Guide

Common issues when running the bookmarks application with Docker.

## Permission Denied Error

**Error:**
```
permission denied while trying to connect to the Docker daemon socket
```

**Cause:** Your user doesn't have permission to access the Docker daemon.

**Solution:**

### Option 1: Add User to Docker Group (Recommended)

```bash
# Add your user to the docker group
sudo usermod -aG docker $USER

# Apply the group change (or log out and back in)
newgrp docker

# Verify it works
docker ps
```

### Option 2: Use sudo (Not Recommended for Development)

```bash
sudo make service-install
```

**Note:** Using `sudo` with Docker is not recommended for development as it can create permission issues with files created by containers.

---

## Docker Daemon Not Running

**Error:**
```
Cannot connect to the Docker daemon
```

**Solution:**

### Linux (systemd)

```bash
# Start Docker daemon
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Check status
sudo systemctl status docker
```

### macOS

```bash
# Start Docker Desktop application
open -a Docker
```

### Windows (WSL2)

```bash
# Start Docker Desktop application
# Or in PowerShell:
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

---

## Image Build Failures

**Error:**
```
failed to solve: failed to compute cache key
```

**Solutions:**

1. **Clear Docker build cache:**
   ```bash
   docker builder prune -a
   ```

2. **Rebuild without cache:**
   ```bash
   docker compose build --no-cache
   ```

3. **Check Dockerfile syntax:**
   ```bash
   docker compose config
   ```

---

## Port Already in Use

**Error:**
```
Bind for 0.0.0.0:5000 failed: port is already allocated
```

**Solutions:**

1. **Change the port in `.env`:**
   ```bash
   echo "BOOKMARKS_PORT=5001" >> .env
   ```

2. **Stop the conflicting service:**
   ```bash
   # Find what's using port 5000
   sudo lsof -i :5000
   
   # Stop the process (replace PID with actual process ID)
   kill <PID>
   ```

3. **Stop all Docker containers:**
   ```bash
   docker compose down
   ```

---

## Volume Permission Issues

**Error:**
```
Permission denied when accessing /data/bookmarks.js
```

**Solution:**

Named volumes (default) should avoid this issue. If you're using bind mounts:

```bash
# Fix permissions on the data directory
sudo chown -R $USER:$USER ./data
```

---

## Container Keeps Restarting

**Check logs:**
```bash
docker compose logs -f bookmarks
```

**Common causes:**

1. **Missing environment variables** - Check `.env` file exists
2. **Invalid bookmarks.js** - Validate JSON syntax
3. **Port conflict** - Change `BOOKMARKS_PORT`

**Restart with fresh state:**
```bash
docker compose down
docker compose up -d
```

---

## Clean Slate (Nuclear Option)

If all else fails, completely reset Docker state:

```bash
# Stop and remove containers
docker compose down -v

# Remove the image
docker rmi bookmarks:local

# Rebuild from scratch
make service-install
```

---

## Getting Help

If you're still stuck:

1. **Check logs:**
   ```bash
   docker compose logs -f
   ```

2. **Verify Docker installation:**
   ```bash
   docker --version
   docker compose version
   ```

3. **Test basic Docker functionality:**
   ```bash
   docker run hello-world
   ```

4. **Open an issue:** Include the output of the above commands and your error message.
