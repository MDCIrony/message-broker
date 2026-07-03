#!/bin/bash
# Script para publicar un mensaje al broker utilizando curl con seguridad

TOPIC=${1:-"alertas"}
PAYLOAD=${2:-"Este es un mensaje de prueba con seguridad desde la CLI"}
TOKEN=${3:-"admin-token-999"}

echo "Enviando mensaje..."
echo "Tópico:  $TOPIC"
echo "Mensaje: $PAYLOAD"
echo "Token:   $TOKEN"
echo "--------------------------------------------------"

curl -X POST "http://localhost:8000/api/publish" \
     -H "Content-Type: application/json" \
     -H "X-Broker-Token: $TOKEN" \
     -d "{\"topic\": \"$TOPIC\", \"payload\": \"$PAYLOAD\"}"

echo -e "\n\nListo!"
