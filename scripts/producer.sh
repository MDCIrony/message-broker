#!/bin/bash
# Script para publicar mensajes continuos al broker de forma periódica
# Uso: ./producer.sh [puerto] [nombre_productor] [tópico] [intervalo_segundos] [token]

PORT=${1:-8000}
PRODUCER_NAME=${2:-"productor_cli"}
TOPIC=${3:-"noticias"}
INTERVAL=${4:-5}
TOKEN=${5:-"producer-token-abc"}

# Generar un UUID único para esta ejecución del productor
PRODUCER_UUID=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())')
FULL_PRODUCER_ID="${PRODUCER_NAME}_${PRODUCER_UUID}"

echo "=================================================="
echo " Iniciando Productor Continuo de Mensajes"
echo "=================================================="
echo "ID Productor: $FULL_PRODUCER_ID"
echo "Puerto:       $PORT"
echo "Tópico:       $TOPIC"
echo "Intervalo:    $INTERVAL segundos"
echo "Token:        $TOKEN"
echo "--------------------------------------------------"

COUNTER=1
while true; do
  PAYLOAD="Mensaje #$COUNTER de $FULL_PRODUCER_ID enviado a las $(date +%T)"
  
  # Realizar petición POST al endpoint REST del broker
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:$PORT/api/publish" \
       -H "Content-Type: application/json" \
       -H "X-Broker-Token: $TOKEN" \
       -d "{\"topic\": \"$TOPIC\", \"payload\": \"$PAYLOAD\"}")
  
  if [ "$RESPONSE" -eq 201 ]; then
    echo "[$(date +%T)] [ÉXITO] Mensaje #$COUNTER enviado a '$TOPIC'."
  else
    echo "[$(date +%T)] [ERROR] Falló el envío. Código HTTP: $RESPONSE"
  fi
  
  COUNTER=$((COUNTER + 1))
  sleep "$INTERVAL"
done
