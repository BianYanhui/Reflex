#!/bin/bash
# Project Reflex - 一键自动化测试脚本

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  Project Reflex - 自动化测试开始"
echo "=========================================="

echo ""
echo "[1/5] 检查 Docker 服务状态..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi
echo "✅ Docker 已运行"

echo ""
echo "[2/5] 构建并启动容器..."
docker compose down 2>/dev/null || true
docker compose up --build -d

echo ""
echo "[3/5] 等待服务初始化 (15秒)..."
sleep 15

echo ""
echo "[4/5] 检查容器状态..."
docker compose ps

echo ""
echo "[5/5] 触发微突发流量 (15个请求)..."
echo "-------------------------------------------"
docker compose exec -T client python3 client.py
echo "-------------------------------------------"

echo ""
echo "[测试完成] 等待日志传输..."
sleep 5

echo ""
echo "=========================================="
echo "  容器日志输出："
echo "=========================================="
docker compose logs --tail=100

echo ""
echo "=========================================="
echo "  测试验证要点："
echo "=========================================="
echo "✅ 现象一: Router 日志应显示 'Routed Task 1~5 to 10.0.0.31'"
echo "✅ 现象二: Device_A 应打印 '[CRITICAL] VRAM OOM Warning!'"
echo "✅ 现象三: Router 应打印 'Device A penalized...Rerouting to Device B'"
echo "✅ 现象四: Client 应显示 'Success rate: 15/15'"
