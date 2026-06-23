#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# SAGE Research — 一键环境配置 + 启动脚本
# 用法: ./setup.sh
# 停止: Ctrl+C
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   SAGE Research — Setup & Launch    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 1. Detect conda
# ============================================================
if ! command -v conda &>/dev/null; then
    err "conda 未安装。请先安装 Miniconda: https://docs.conda.io/en/latest/miniconda.html"
fi
ok "conda 已安装"

# ============================================================
# 2. Setup conda environment
# ============================================================
ENV_NAME="deep-research"
if conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    ok "conda 环境 '${ENV_NAME}' 已存在"
else
    info "创建 conda 环境 '${ENV_NAME}' (Python 3.14)..."
    conda create -n "$ENV_NAME" python=3.14 -y
    ok "conda 环境创建完成"
fi

# Activate
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

# ============================================================
# 3. Python dependencies (hash-based incremental)
# ============================================================
REQ_HASH=$(md5sum requirements.txt 2>/dev/null | cut -d' ' -f1 || echo "")
HASH_FILE=".requirements_hash"
if [ -f "$HASH_FILE" ] && [ "$(cat "$HASH_FILE")" = "$REQ_HASH" ]; then
    ok "Python 依赖已是最新"
else
    info "安装 Python 依赖..."
    pip install -r requirements.txt
    echo "$REQ_HASH" > "$HASH_FILE"
    ok "Python 依赖安装完成"
fi

# ============================================================
# 4. .env file
# ============================================================
if [ -f ".env" ]; then
    ok ".env 文件已存在"
else
    warn ".env 文件不存在，正在从 .env.example 创建..."
    cp .env.example .env
    warn "请编辑 .env 填入你的 API Key，然后重新运行 ./setup.sh"
    exit 0
fi

# ============================================================
# 5. Data directories
# ============================================================
mkdir -p data/originals data/converted data/downloads data/rag data/search_cache
ok "数据目录已就绪"

# ============================================================
# 6. Frontend dependencies
# ============================================================
if [ -d "web/node_modules" ]; then
    ok "前端依赖已安装"
else
    info "安装前端依赖..."
    cd web
    npm install
    cd ..
    ok "前端依赖安装完成"
fi

# ============================================================
# 7. Start services
# ============================================================
info "启动后端服务 (http://localhost:8000)..."
python server.py &
BACKEND_PID=$!

# Wait for backend to be ready
info "等待后端就绪..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/api/library > /dev/null 2>&1; then
        ok "后端已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        kill "$BACKEND_PID" 2>/dev/null
        err "后端启动超时，请检查 .env 配置是否正确"
    fi
    sleep 1
done

info "启动前端服务 (http://localhost:3000)..."
cd web
npm run dev &
FRONTEND_PID=$!
cd ..

# ============================================================
# 8. Cleanup on exit
# ============================================================
cleanup() {
    echo ""
    info "正在关闭服务..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    ok "服务已关闭"
}
trap cleanup EXIT INT TERM

# ============================================================
# 9. Open browser
# ============================================================
sleep 3
info "打开浏览器 http://localhost:3000 ..."
if command -v explorer.exe &>/dev/null; then
    explorer.exe "http://localhost:3000" 2>/dev/null || true
elif command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:3000" 2>/dev/null || true
elif command -v open &>/dev/null; then
    open "http://localhost:3000" 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  服务运行中                         ║${NC}"
echo -e "${GREEN}║  后端: http://localhost:8000        ║${NC}"
echo -e "${GREEN}║  前端: http://localhost:3000        ║${NC}"
echo -e "${GREEN}║  按 Ctrl+C 停止所有服务             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""

# Wait for frontend (foreground process)
wait "$FRONTEND_PID"
