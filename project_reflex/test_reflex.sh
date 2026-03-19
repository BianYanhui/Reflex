#!/bin/bash
# Project Reflex - Automated Test Script

echo "========================================"
echo "Project Reflex - Automated Testing"
echo "========================================"

PROJECT_DIR="/Users/yhbian/Library/CloudStorage/OneDrive-个人/Yanhui/20260318-Reflex/20260319-Reflex_Demo/project_reflex"

cd "$PROJECT_DIR" || exit 1

echo ""
echo "[Step 1] Building and starting containers..."
docker compose up --build -d

echo ""
echo "[Step 2] Waiting for containers to initialize (10s)..."
sleep 10

echo ""
echo "[Step 3] Checking container status..."
docker compose ps

echo ""
echo "[Step 4] Starting log monitoring in background..."
docker compose logs -f > /tmp/reflex_logs.txt &
LOGS_PID=$!

echo ""
echo "[Step 5] Triggering micro-burst traffic (15 requests in 100ms)..."
docker compose exec -T client python3 client.py

echo ""
echo "[Step 6] Waiting for all requests to complete (15s)..."
sleep 15

echo ""
echo "[Step 7] Stopping log monitoring..."
kill $LOGS_PID 2>/dev/null

echo ""
echo "========================================"
echo "Test Complete - Log Output:"
echo "========================================"
cat /tmp/reflex_logs.txt
