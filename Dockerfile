# ============================================
# DOCKERFILE FOR STREAMLIT ANNOTATION TOOL
# ============================================
# This file tells Docker how to build a container for our application
# Each step is explained below

# STEP 1: Choose Base Image
# --------------------------
# We use Python 3.11 slim - it's smaller (faster downloads) but has all we need
# 'slim' means it doesn't include unnecessary packages
FROM python:3.11-slim

# STEP 2: Set Working Directory
# ------------------------------
# This is where our app files will live inside the container
# All commands will run from this directory
WORKDIR /app

# STEP 3: Set Environment Variables
# ----------------------------------
# PYTHONUNBUFFERED=1: Makes Python output appear immediately (good for logs)
# PYTHONDONTWRITEBYTECODE=1: Prevents creating .pyc files (saves space)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# STEP 4: Install System Dependencies (Optional)
# -----------------------------------------------
# Some Python packages need system libraries
# For Streamlit, we usually don't need extra packages
# But we update apt-get and clean up to keep image small
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# STEP 5: Copy Requirements File First
# --------------------------------------
# We copy requirements.txt BEFORE copying code
# This allows Docker to cache the pip install step
# If requirements.txt doesn't change, Docker reuses the cached layer
COPY requirements.txt .

# STEP 6: Install Python Dependencies
# -------------------------------------
# Install all packages from requirements.txt
# --no-cache-dir: Don't store pip cache (saves space)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# STEP 7: Copy Application Files
# --------------------------------
# Copy all Python files needed for the application
# We copy these AFTER requirements to leverage Docker caching
COPY app.py .
COPY auth.py .
COPY data_loader.py .
COPY persistence.py .
COPY annotation_ui.py .
COPY config.py .
COPY db.py .

# STEP 8: Create Volume for Data Persistence (Optional)
# ------------------------------------------------------
# Create a directory where data files will be stored
# This allows data to persist even if container is recreated
# Note: We'll use a volume mount when running the container
VOLUME ["/app/data"]

# STEP 9: Expose Port
# -------------------
# Streamlit runs on port 8501 by default
# This tells Docker which port the app will use
EXPOSE 8501

# STEP 10: Health Check (Optional but Recommended)
# ------------------------------------------------
# This helps Docker know if the container is healthy
# Checks every 30 seconds if Streamlit is responding
# Note: Requires 'requests' package, or we can use a simpler check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.connect(('localhost', 8501)); s.close()" || exit 1

# STEP 11: Run the Application
# ----------------------------
# This command runs when the container starts
# --server.port=8501: Streamlit port
# --server.address=0.0.0.0: Listen on all network interfaces (allows external access)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
