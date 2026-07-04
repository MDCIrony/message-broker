#!/bin/bash
# Script para iniciar la consola de administración
# Uso: ./admin_monitor.sh [host] [puerto] [token_admin]

HOST=${1:-"localhost"}
PORT=${2:-8000}
TOKEN=${3:-"admin-token-999"}

python3 "$(dirname "$0")/python/admin_monitor.py" "$HOST" "$PORT" "$TOKEN"
