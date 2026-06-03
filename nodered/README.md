# Node-RED SmartHome IoT - Configuración y Flujo de Trabajo

Este directorio contiene los flujos, scripts de sincronización y la configuración para el Bot de Telegram de nuestro proyecto SmartHome IoT.

---

## 1. Instalación de Nodos en Docker

Para que los flujos carguen correctamente, debes instalar los nodos del Dashboard y de Telegram dentro del contenedor. Ejecuta en tu terminal:

```bash
docker exec -u 0 mynodered npm install --prefix /data node-red-dashboard node-red-contrib-telegrambot
```

### Solución de Red/DNS (Obligatorio en hotspots y VPNs)
Para evitar que Node-RED sufra de bloqueos por IPv6 (lo que hace que la API de Telegram de un timeout de 30 segundos), inyecta este parche que fuerza la resolución IPv4 en el archivo `settings.js` del contenedor:

```bash
docker exec -u 0 mynodered sh -c "echo \"const dns = require('dns'); const originalLookup = dns.lookup; dns.lookup = function(hostname, options, callback) { if (typeof options === 'function') { callback = options; options = {}; } else if (typeof options === 'number') { options = { family: options }; } else if (!options) { options = {}; } options.family = 4; return originalLookup.call(this, hostname, options, callback); };\" | cat - /data/settings.js > temp && mv temp /data/settings.js && chown node-red:node-red /data/settings.js"
```

Además, desactiva la encriptación de credenciales para poder compartir los flujos en texto plano de forma local:

```bash
docker exec mynodered sed -i 's/\/\/credentialSecret: "a-secret-key",/credentialSecret: false,/g' /data/settings.js
```

Finalmente, **reinicia el contenedor** para aplicar todo:

```bash
docker restart mynodered
```

---

## 2. Configurar el Bot de Telegram

1. Crea una copia del archivo de ejemplo para tus credenciales locales:
   ```bash
   cp nodered/flows_cred.json.example nodered/flows_cred.json
   ```
2. Abre `nodered/flows_cred.json` e introduce la API Key del bot de Telegram que nos compartimos de manera privada. (Este archivo `flows_cred.json` está ignorado en `.gitignore` para no subir claves públicas a GitHub).

---

## 3. Sincronización de Cambios

Para que cualquier cambio en los archivos locales `flows.json` y `flows_cred.json` se vea reflejado instantáneamente en tu navegador, ejecuta el script de sincronización en tu laptop:

```bash
python3 nodered/sync.py
```

### ¿Qué hace `sync.py`?
1. Sube el archivo `flows.json` mediante la API Admin de Node-RED.
2. Inyecta y asocia tu API Key de Telegram de forma dinámica al nodo de configuración sin necesidad de reiniciar Docker.

---

## 4. Acceso y Comandos

* **Dashboard de SmartHome:** [http://localhost:1880/ui](http://localhost:1880/ui) (Grilla 2x2 optimizada sin superposición de elementos).
* **Editor de Node-RED:** [http://localhost:1880/](http://localhost:1880/)
* **Comandos del Bot (Grupo/Privado):**
  - `/status` - Muestra temperatura, humedad, gas, sonido y fecha en tiempo real.
  - `/ayuda` - Lista los comandos del bot.
