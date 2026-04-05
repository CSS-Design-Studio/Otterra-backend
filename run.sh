#!/bin/bash

######################################################
#  Solotrip FastAPI 啟動腳本                          #
#  用法: ./run.sh [環境]                              #
#  環境選項: local, dev, prod                         #
######################################################

# 預設環境為 local
ENV=${1:-local}

# 驗證環境參數
if [[ ! "$ENV" =~ ^(local|dev|prod)$ ]]; then
    echo "❌ 錯誤：無效的環境參數 '$ENV'"
    echo ""
    echo "用法: ./run.sh [環境]"
    echo "環境選項："
    echo "  local - 本地開發環境（預設）"
    echo "  dev   - 開發/測試環境"
    echo "  prod  - 正式環境"
    echo ""
    echo "範例："
    echo "  ./run.sh        # 使用 local 環境"
    echo "  ./run.sh dev    # 使用 dev 環境"
    echo "  ./run.sh prod   # 使用 prod 環境"
    exit 1
fi

# 更新 .env 檔案中的環境設定
sed -i "s/^ENV=.*/ENV=$ENV/" .env

echo "========================================================"
echo "  🚀 啟動 Solotrip Backend"
echo "========================================================"
echo "  環境: $ENV"
echo "  配置檔: config/.env.$ENV"
echo "========================================================"
echo ""

# 根據環境選擇啟動方式
if [ "$ENV" = "prod" ]; then
    # 正式環境：多 worker，關閉熱重載
    echo "⚙️  正式環境模式：使用 4 個 worker"
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
else
    # 開發/測試環境：啟用熱重載
    echo "⚙️  開發模式：啟用熱重載"
    python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi
