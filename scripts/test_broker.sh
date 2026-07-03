#!/bin/bash
# Script de pruebas de seguridad y ACL para el Broker de Mensajes

echo "=== 1. Publicación Autorizada (Admin) ==="
curl -s -X POST "http://localhost:8000/api/publish" \
     -H "Content-Type: application/json" \
     -H "X-Broker-Token: admin-token-999" \
     -d '{"topic": "noticias", "payload": "Noticia de ultima hora por Admin"}' | json_pp 2>/dev/null || curl -s -X POST "http://localhost:8000/api/publish" -H "Content-Type: application/json" -H "X-Broker-Token: admin-token-999" -d '{"topic": "noticias", "payload": "Noticia de ultima hora por Admin"}'
echo -e "\n"

echo "=== 2. Publicación Autorizada (Productor) ==="
curl -s -X POST "http://localhost:8000/api/publish" \
     -H "Content-Type: application/json" \
     -H "X-Broker-Token: producer-token-abc" \
     -d '{"topic": "alertas", "payload": "Fuga detectada por Productor"}' | json_pp 2>/dev/null || curl -s -X POST "http://localhost:8000/api/publish" -H "Content-Type: application/json" -H "X-Broker-Token: producer-token-abc" -d '{"topic": "alertas", "payload": "Fuga detectada por Productor"}'
echo -e "\n"

echo "=== 3. Publicación Denegada (Consumidor intentando Publicar - Fails with 403) ==="
curl -s -X POST "http://localhost:8000/api/publish" \
     -H "Content-Type: application/json" \
     -H "X-Broker-Token: consumer-token-xyz" \
     -d '{"topic": "alertas", "payload": "Mensaje bloqueado"}'
echo -e "\n\n"

echo "=== 4. Publicación Denegada (Token Inválido - Fails with 403) ==="
curl -s -X POST "http://localhost:8000/api/publish" \
     -H "Content-Type: application/json" \
     -H "X-Broker-Token: token-falso-123" \
     -d '{"topic": "alertas", "payload": "Mensaje falso"}'
echo -e "\n\n"

echo "=== 5. Lectura de Tópico Autorizada para Consumidor (noticias) ==="
curl -s "http://localhost:8000/api/messages?topic=noticias" \
     -H "X-Broker-Token: consumer-token-xyz" | json_pp 2>/dev/null || curl -s "http://localhost:8000/api/messages?topic=noticias" -H "X-Broker-Token: consumer-token-xyz"
echo -e "\n"

echo "=== 6. Lectura de Tópico Denegada para Consumidor (deportes - Fails with 403) ==="
curl -s "http://localhost:8000/api/messages?topic=deportes" \
     -H "X-Broker-Token: consumer-token-xyz"
echo -e "\n\n"
