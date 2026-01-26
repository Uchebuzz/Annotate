#!/bin/bash
# Startup script that runs both cron and streamlit

# Start cron daemon in the background
echo "Starting cron daemon..."
cron

# Start streamlit in the foreground
echo "Starting Streamlit application..."
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0

