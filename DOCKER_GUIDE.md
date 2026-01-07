# Docker Guide for Pidgin Annotation Tool

This guide explains how to build and run the application using Docker.

## Prerequisites

1. **Install Docker Desktop** (Windows/Mac) or Docker Engine (Linux)
   - Download from: https://www.docker.com/products/docker-desktop
   - Make sure Docker is running

2. **Verify Docker Installation**
   ```bash
   docker --version
   docker-compose --version
   ```

## Step-by-Step Instructions

### Method 1: Using Docker Commands (Manual)

#### Step 1: Build the Docker Image
```bash
docker build -t pidgin-annotation-tool .
```

**What this does:**
- `-t pidgin-annotation-tool`: Tags the image with a name
- `.`: Uses the Dockerfile in current directory

**Expected output:**
```
Sending build context to Docker daemon...
Step 1/11 : FROM python:3.11-slim
...
Successfully built abc123def456
Successfully tagged pidgin-annotation-tool:latest
```

#### Step 2: Run the Container
```bash
docker run -d \
  --name annotation-app \
  -p 8501:8501 \
  -v $(pwd)/data.jsonl:/app/data.jsonl \
  -v $(pwd)/users.json:/app/users.json \
  -v $(pwd)/annotations.json:/app/annotations.json \
  -v $(pwd)/assignments.json:/app/assignments.json \
  -v $(pwd)/batch_assignments.json:/app/batch_assignments.json \
  -v $(pwd)/config.json:/app/config.json \
  pidgin-annotation-tool
```

**What this does:**
- `-d`: Run in detached mode (background)
- `--name annotation-app`: Name the container
- `-p 8501:8501`: Map port 8501 from host to container
- `-v`: Mount volumes (persist data files)
- Last argument: Image name to run

**For Windows PowerShell, use:**
```powershell
docker run -d `
  --name annotation-app `
  -p 8501:8501 `
  -v ${PWD}/data.jsonl:/app/data.jsonl `
  -v ${PWD}/users.json:/app/users.json `
  -v ${PWD}/annotations.json:/app/annotations.json `
  -v ${PWD}/assignments.json:/app/assignments.json `
  -v ${PWD}/batch_assignments.json:/app/batch_assignments.json `
  -v ${PWD}/config.json:/app/config.json `
  pidgin-annotation-tool
```

#### Step 3: Access the Application
Open your browser and go to:
```
http://localhost:8501
```

#### Step 4: View Logs
```bash
docker logs annotation-app
```

#### Step 5: Stop the Container
```bash
docker stop annotation-app
```

#### Step 6: Remove the Container
```bash
docker rm annotation-app
```

### Method 2: Using Docker Compose (Recommended)

#### Step 1: Build and Run
```bash
docker-compose up -d
```

**What this does:**
- Reads `docker-compose.yml`
- Builds the image if needed
- Starts the container
- `-d`: Run in background

#### Step 2: View Logs
```bash
docker-compose logs -f
```

#### Step 3: Stop the Application
```bash
docker-compose down
```

#### Step 4: Rebuild After Code Changes
```bash
docker-compose up -d --build
```

## Understanding the Dockerfile

### Each Step Explained:

1. **FROM python:3.11-slim**
   - Starts with Python 3.11 on Debian
   - `slim` = smaller image size

2. **WORKDIR /app**
   - Sets working directory inside container

3. **ENV PYTHONUNBUFFERED=1**
   - Makes Python output appear immediately in logs

4. **COPY requirements.txt**
   - Copies dependency list first (for caching)

5. **RUN pip install**
   - Installs all Python packages

6. **COPY *.py**
   - Copies application code

7. **EXPOSE 8501**
   - Documents which port the app uses

8. **CMD ["streamlit", "run", ...]**
   - Command that runs when container starts

## Common Commands

### View Running Containers
```bash
docker ps
```

### View All Containers (including stopped)
```bash
docker ps -a
```

### Execute Command in Container
```bash
docker exec -it annotation-app bash
```

### View Container Resource Usage
```bash
docker stats annotation-app
```

### Remove Image
```bash
docker rmi pidgin-annotation-tool
```

## Troubleshooting

### Port Already in Use
If port 8501 is already in use:
```bash
# Change the port mapping
docker run -p 8502:8501 pidgin-annotation-tool
# Then access at http://localhost:8502
```

### Container Won't Start
```bash
# Check logs
docker logs annotation-app

# Run interactively to see errors
docker run -it pidgin-annotation-tool
```

### Data Files Not Persisting
Make sure volumes are mounted correctly:
```bash
# Check volume mounts
docker inspect annotation-app | grep Mounts
```

### Rebuild After Code Changes
```bash
# Stop and remove old container
docker stop annotation-app
docker rm annotation-app

# Rebuild image
docker build -t pidgin-annotation-tool .

# Run again
docker run -d --name annotation-app -p 8501:8501 pidgin-annotation-tool
```

## Production Tips

1. **Use Environment Variables for Secrets**
   ```dockerfile
   ENV ADMIN_PASSWORD=your_secret_password
   ```

2. **Add Health Checks** (already included)
   - Helps Docker know if container is healthy

3. **Use Docker Compose for Production**
   - Easier to manage volumes and networking

4. **Consider Using .env File**
   - Store sensitive configuration separately

## Next Steps

- Set up reverse proxy (nginx) for production
- Add SSL/TLS certificates
- Set up automated backups for data files
- Configure resource limits (CPU, memory)


