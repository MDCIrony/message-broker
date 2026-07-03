#!/bin/bash
# Script para iniciar un consumidor interactivo WebSocket
# Uso: ./consumer.sh [puerto] [nombre_consumidor] [token]

PORT=${1:-8000}
CLIENT_NAME=${2:-"consumidor_cli"}
TOKEN=${3:-"consumer-token-xyz"}

# Invocar el script python interactivo pasándole los parámetros
python3 "$(dirname "$0")/python/consumer.py" "$PORT" "$CLIENT_NAME" "$TOKEN"
