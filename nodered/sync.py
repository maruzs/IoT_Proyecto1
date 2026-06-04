#!/usr/bin/env python3
import json
import urllib.request
import os

# Configuración
DIR = os.path.dirname(os.path.abspath(__file__))
FLOWS_PATH = os.path.join(DIR, 'flows.json')
CREDS_PATH = os.path.join(DIR, 'flows_cred.json')
API_URL = 'http://localhost:1880/flows'

print("=== Sincronizando flujos y credenciales mediante API de Node-RED ===")

# Leer flujos
if not os.path.exists(FLOWS_PATH):
    print(f"✗ Error: No se encuentra {FLOWS_PATH}")
    exit(1)

with open(FLOWS_PATH, 'r') as f:
    flows = json.load(f)

# Leer credenciales si existen
credentials = {}
if os.path.exists(CREDS_PATH):
    with open(CREDS_PATH, 'r') as f:
        credentials = json.load(f)
    print("✓ Credenciales (flows_cred.json) cargadas locales.")
else:
    print("⚠ Advertencia: No se encontraron credenciales locales.")

# Subir flujos primero para que exista el nodo 'telegram_bot_config'
req_flows = urllib.request.Request(
    API_URL,
    data=json.dumps(flows).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req_flows) as response:
        if response.status in (200, 204):
            print("✓ Flujos sincronizados exitosamente por API.")
        else:
            print(f"✗ Error al subir flujos. Código HTTP: {response.status}")
except Exception as e:
    print(f"✗ Falló la conexión al API de flujos: {e}")
    exit(1)

# Ahora subimos las credenciales específicas del Bot de Telegram al endpoint del nodo
if "telegram_bot_config" in credentials:
    bot_creds = credentials["telegram_bot_config"]
    # El tipo de nodo es "telegram bot", por lo que usamos la codificación URL %20 para el espacio
    url_node_creds = 'http://localhost:1880/credentials/telegram%20bot/telegram_bot_config'
    
    req_creds = urllib.request.Request(
        url_node_creds,
        data=json.dumps(bot_creds).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req_creds) as response:
            if response.status in (200, 204):
                print("✓ Credenciales del Bot de Telegram asociadas y guardadas exitosamente.")
            else:
                print(f"✗ Error al asociar credenciales. Código HTTP: {response.status}")
    except Exception as e:
        print(f"✗ Falló la asociación de credenciales al nodo: {e}")

print("=== Sincronización finalizada ===")
