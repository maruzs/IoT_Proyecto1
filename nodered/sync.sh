#!/bin/bash
# sync.sh - Copia el archivo flows.json local al contenedor y recarga Node-RED.

# Directorio del script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=== Sincronizando flows.json con el contenedor Docker ==="

# 1. Copiar flows.json al contenedor
docker cp "$DIR/flows.json" mynodered:/data/flows.json
if [ $? -eq 0 ]; then
    echo "✓ Archivo flows.json copiado exitosamente al contenedor."
else
    echo "✗ Error al copiar flows.json al contenedor."
    exit 1
fi

# 2. Hacer reload instantáneo a través de la API de Node-RED
echo "Refrescando flujos en la API de Node-RED..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:1880/flows -H "Node-RED-Deployment-Type: reload" -H "Content-Type: application/json")

if [ "$RESPONSE" == "204" ] || [ "$RESPONSE" == "200" ]; then
    echo "✓ Flujos recargados instantáneamente sin reiniciar el contenedor."
else
    echo "⚠ La API respondió con código $RESPONSE. Reiniciando contenedor como respaldo..."
    docker restart mynodered
    echo "✓ Contenedor reiniciado."
fi

echo "=== Sincronización finalizada ==="
