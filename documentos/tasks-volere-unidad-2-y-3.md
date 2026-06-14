# Tarjetas Volere — Proyecto IoT Final 2026, Unidades 2 y 3

> **Formato:** Tarjeta de Volere con Historia de Usuario / Historia Técnica + criterios Gherkin.
> **Arquitectura:** Microservicios con LangGraph como motor de agente, MCP para exposición de tools, Docker Compose para despliegue.
> **Stack:** Python (FastAPI), LangGraph, Ollama, Mosquitto, Node-RED, InfluxDB, Grafana.

---

## Unidad 2 — Protocolos, Seguridad y LLM Local

---

### T-001: MQTT Broker con TLS y autenticación

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 2
**Servicio:** Infraestructura — Mosquitto
**Dependencias:** Ninguna

#### Contexto
El broker MQTT debe pasar de operar en texto plano (puerto 1883) a un canal seguro con cifrado TLS y autenticación usuario/contraseña. Esto protege la comunicación extremo a extremo entre sensores, actuadores y servicios.

#### Descripción
Configurar Mosquitto con certificado TLS autofirmado, activar escucha en puerto 8883, y crear archivo de usuarios con `mosquitto_passwd`. El listener inseguro (1883) debe deshabilitarse.

#### Criterios de Aceptación

```gherkin
Escenario: Conexión TLS desde cliente MQTT
  Dado que el broker Mosquitto está corriendo con TLS habilitado en puerto 8883
  Y existe un usuario "equipo69" con contraseña en el archivo de passwords
  Cuando un cliente MQTT intenta conectarse sin TLS al puerto 1883
  Entonces la conexión es rechazada
  Cuando un cliente MQTT intenta conectarse con TLS al puerto 8883 sin credenciales
  Entonces la conexión es rechazada
  Cuando un cliente MQTT se conecta con TLS al puerto 8883 con credenciales válidas
  Entonces la conexión es aceptada y puede publicar y suscribirse

Escenario: Certificado TLS autofirmado válido
  Dado que se ejecutó openssl req -new -x509 -days 365
  Cuando un cliente configura el CA certificate generado
  Entonces la conexión TLS se establece sin errores de verificación
```

---

### T-002: ACLs Mosquitto por cliente

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 2
**Servicio:** Infraestructura — Mosquitto
**Dependencias:** T-001

#### Contexto
Sin ACLs, cualquier cliente autenticado puede publicar o suscribirse a cualquier tópico. Esto es un riesgo de seguridad: un sensor comprometido podría publicar comandos de control.

#### Descripción
Definir reglas ACL en Mosquitto que limiten qué clientes pueden publicar y suscribirse a cada tópico. Cada dispositivo y servicio debe tener permisos mínimos necesarios.

#### Criterios de Aceptación

```gherkin
Escenario: Sensor solo publica datos, no comandos
  Dado que el cliente "esp32-sensor" tiene ACL configurada
  Cuando intenta publicar en smarthome/equipo69/control/led
  Entonces la publicación es rechazada por el broker
  Cuando publica en smarthome/equipo69/datos
  Entonces la publicación es aceptada

Escenario: LLM Gateway publica comandos y recibe datos
  Dado que el cliente "llm-gateway" tiene ACL configurada
  Cuando publica en smarthome/equipo69/control/led
  Entonces la publicación es aceptada
  Cuando se suscribe a smarthome/equipo69/datos
  Entonces la suscripción es aceptada
```

---

### T-003: Firmware ESP32 con soporte TLS

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 2
**Servicio:** Firmware — MKR1000 + ESP32-CAM
**Dependencias:** T-001

#### Contexto
El firmware del MKR1000 (sensores: temperatura, humedad, gas, sonido, PIR) y del ESP32-CAM (cámara) se conecta a MQTT sin TLS. Ambos deben actualizarse para usar conexión segura con certificado CA y autenticación usuario/contraseña.

#### Descripción
Actualizar el firmware del MKR1000 y ESP32-CAM para conectarse al broker en puerto 8883 con TLS. En el MKR1000 usar `WiFiSSLClient`, en la ESP32-CAM usar `WiFiClientSecure`. Incluir el certificado CA autofirmado embebido, credenciales externalizadas (sin hardcodear en el repo), y manejo de reconexión TLS en ambos.

#### Criterios de Aceptación

```gherkin
Escenario: MKR1000 se conecta con TLS y publica datos de sensores
  Dado que el MKR1000 tiene el firmware actualizado con soporte TLS
  Y el certificado CA está embebido en el código
  Y las credenciales MQTT están configuradas
  Cuando el MKR1000 inicia y se conecta a WiFi
  Entonces establece conexión MQTT segura al puerto 8883
  Y publica datos de sensores en smarthome/equipo69/datos cada 2 segundos

Escenario: ESP32-CAM se conecta con TLS y publica imágenes
  Dado que la ESP32-CAM tiene el firmware actualizado con soporte TLS
  Y el certificado CA está embebido
  Cuando captura una imagen por comando MQTT
  Entonces publica la imagen en smarthome/equipo69/camara/imagen vía MQTT seguro

Escenario: Reconexión TLS tras caída de red
  Dado que el MKR1000 (o ESP32-CAM) estaba conectado con TLS
  Cuando se interrumpe la conexión WiFi
  Y se restablece después de 10 segundos
  Entonces el dispositivo reconecta MQTT con TLS sin intervención manual
  Y reanuda la publicación de datos
```

---

### T-004: Firmware ESP32 cliente CoAP

**Tipo:** Historia Técnica
**Prioridad:** 🟡 Media
**Unidad:** 2
**Servicio:** Firmware — ESP32 CoAP
**Dependencias:** Ninguna (paralelo a T-003)

#### Contexto
La Unidad 2 requiere implementar CoAP en al menos un nodo sensor como protocolo alternativo a MQTT. CoAP usa UDP en lugar de TCP, ideal para dispositivos con recursos limitados.

#### Descripción
Programar un ESP32 (puede ser uno nuevo o reutilizar uno existente) para publicar temperatura o humedad usando CoAP sobre UDP puerto 5683, con la librería `CoAP-simple-library`.

#### Criterios de Aceptación

```gherkin
Escenario: ESP32 publica datos vía CoAP
  Dado que el ESP32 está programado con firmware CoAP
  Y está conectado a la red WiFi
  Cuando el sensor toma una lectura de temperatura
  Entonces envía un mensaje CoAP POST al endpoint configurado
  Y el mensaje contiene el valor de temperatura en formato JSON

Escenario: Intervalo de publicación configurable
  Dado que el ESP32 CoAP está en funcionamiento
  Cuando se recibe un mensaje CoAP PUT con nuevo intervalo
  Entonces el ESP32 ajusta su frecuencia de publicación
```

---

### T-005: Microservicio CoAP Bridge

**Tipo:** Historia Técnica
**Prioridad:** 🟡 Media
**Unidad:** 2
**Servicio:** CoAP Bridge Service (Python)
**Dependencias:** T-001, T-004

#### Contexto
En lugar de usar el nodo `node-red-contrib-coap`, implementamos un microservicio dedicado que escucha mensajes CoAP y los traduce a MQTT. Esto desacopla Node-RED del protocolo CoAP y facilita el testing independiente.

#### Descripción
Microservicio Python (`aiocoap` o `coapthon3`) que expone un endpoint CoAP, recibe datos del ESP32, parsea el JSON, y republica en el tópico MQTT correspondiente con TLS.

#### Criterios de Aceptación

```gherkin
Escenario: Traducción CoAP a MQTT
  Dado que el CoAP Bridge Service está corriendo
  Y está suscrito a recursos CoAP en /sensores/temperatura
  Cuando el ESP32 CoAP envía {"temperatura": 29.5, "humedad": 70}
  Entonces el servicio publica en MQTT smarthome/equipo69/datos con el mismo payload
  Y el mensaje es recibido por los suscriptores MQTT

Escenario: Manejo de mensajes malformados
  Dado que el CoAP Bridge Service está corriendo
  Cuando recibe un mensaje CoAP que no es JSON válido
  Entonces registra un warning en logs
  Y NO publica nada en MQTT
```

---

### T-006: Instalación y configuración de Ollama

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 2
**Servicio:** Infraestructura — Ollama (host)
**Dependencias:** Ninguna

#### Contexto
Ollama corre directamente en el sistema operativo host, no en Docker. Debe instalarse, descargarse el modelo liviano, y verificar que la API responde correctamente en `localhost:11434`. Los contenedores lo accederán vía `172.17.0.1:11434`.

#### Descripción
Instalar Ollama, descargar `phi3:mini` o `llama3.2:3b`, verificar que `ollama serve` expone la API, y probar con un prompt de ejemplo que devuelva JSON válido con `"format": "json"`.

#### Criterios de Aceptación

```gherkin
Escenario: Ollama responde con JSON válido
  Dado que Ollama está corriendo en localhost:11434
  Y el modelo phi3:mini está descargado
  Cuando se envía un POST a /api/generate con un prompt que pide respuesta JSON
  Y se incluye "format": "json" y "stream": false
  Entonces la respuesta contiene un JSON parseable en el campo "response"
  Y el tiempo de respuesta es menor a 15 segundos en CPU

Escenario: Ollama responde prompt de control domótico
  Dado que Ollama está corriendo con phi3:mini
  Cuando se envía un prompt con estado del hogar (temp, gas, movimiento, hora)
  Entonces la respuesta es un JSON con campos: nivel_alerta, activar_led, activar_buzzer, mensaje_alerta, razonamiento
  Y todos los campos tienen tipos correctos (string, boolean, boolean, string, string)
```

---

### T-007: Microservicio LLM Gateway (REST API + Ollama client)

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 2
**Servicio:** LLM Gateway Service (Python/FastAPI)
**Dependencias:** T-001, T-006

#### Contexto
El LLM Gateway es el servicio central que orquesta la comunicación con Ollama. Recibe triggers (vía REST desde Node-RED, por timer interno del agente LangGraph, o por eventos MQTT), construye prompts con contexto de sensores, llama a Ollama, valida la respuesta JSON, y publica comandos MQTT. Separa la lógica de razonamiento del flow de Node-RED.

#### Descripción
Microservicio FastAPI con endpoints REST (`POST /llm/decide`, `POST /llm/query`) y cliente MQTT interno para publicar comandos. Incluye: prompt builder que inyecta estado actual del hogar, llamada a Ollama con timeout y reintentos, validador de respuesta JSON con fallback, y publicación MQTT con TLS.

#### Criterios de Aceptación

```gherkin
Escenario: Gateway recibe trigger y publica comandos
  Dado que el LLM Gateway Service está corriendo
  Y Ollama está disponible en 172.17.0.1:11434
  Y el broker MQTT seguro está accesible
  Cuando se envía POST /llm/decide con el estado actual de sensores
  Entonces el servicio construye un prompt con ese contexto
  Y llama a Ollama con "format": "json"
  Y parsea la respuesta JSON
  Y publica los comandos en smarthome/equipo69/control/led y smarthome/equipo69/llm/decision

Escenario: Gateway maneja respuesta JSON inválida de Ollama
  Dado que el LLM Gateway recibe una respuesta de Ollama
  Cuando el campo "response" no es JSON válido
  Entonces el gateway reintenta la llamada con un prompt reforzado (max 3 intentos)
  Y si todos fallan, publica un estado de error en smarthome/equipo69/llm/respuesta
  Y registra el error en logs

Escenario: Gateway maneja timeout de Ollama
  Dado que Ollama tarda más de 30 segundos en responder
  Cuando el LLM Gateway envía la solicitud
  Entonces cancela la llamada después del timeout
  Y devuelve HTTP 504 al caller
  Y NO publica comandos MQTT incorrectos
```

---

### T-008: MCP Tools para LLM Gateway

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 2
**Servicio:** LLM Gateway Service
**Dependencias:** T-007, T-015 (Digital Twin)

#### Contexto
Para que LangGraph y el agente autónomo funcionen correctamente, el LLM Gateway debe exponer tools vía MCP (Model Context Protocol). Estas tools permiten al LLM consultar estado de sensores, activar actuadores, y enviar notificaciones sin que el prompt tenga que contener toda la lógica.

#### Descripción
Implementar un servidor MCP dentro del LLM Gateway que exponga las siguientes tools: `get_sensor_state`, `activate_actuator`, `send_notification`, `adjust_threshold`, `query_history`. Cada tool ejecuta acciones concretas (leer Digital Twin, publicar MQTT, llamar Alert Manager).

#### Criterios de Aceptación

```gherkin
Escenario: Tool get_sensor_state retorna estado actual
  Dado que el MCP server está corriendo en el LLM Gateway
  Y el Digital Twin Service tiene datos actualizados
  Cuando se invoca la tool "get_sensor_state" con parámetro sensor="temperatura"
  Entonces retorna el valor actual de temperatura desde el Digital Twin
  Y el tiempo de respuesta es menor a 200ms

Escenario: Tool activate_actuator publica en MQTT
  Dado que la tool activate_actuator está registrada
  Cuando se invoca con parámetros dispositivo="led", estado=true
  Entonces el LLM Gateway publica {"estado": true} en smarthome/equipo69/control/led
  Y retorna confirmación de publicación exitosa

Escenario: Tools disponibles en el endpoint MCP
  Dado que el servidor MCP está corriendo
  Cuando un cliente consulta el endpoint de tools disponibles
  Entonces la respuesta lista al menos: get_sensor_state, activate_actuator, send_notification, adjust_threshold, query_history
  Y cada tool tiene descripción, parámetros y tipos documentados
```

---

### T-009: LangGraph Agent — Decisiones contextuales (Unidad 2)

**Tipo:** Historia de Usuario
**Prioridad:** 🔴 Alta
**Unidad:** 2
**Servicio:** LLM Gateway Service (módulo LangGraph)
**Dependencias:** T-007, T-008

#### Descripción
**Como** residente del hogar inteligente, **quiero** que el sistema tome decisiones contextuales basadas en todos los sensores y las ejecute automáticamente, **para** no tener que programar reglas if/else manuales para cada situación posible.

#### Criterios de Aceptación

```gherkin
Escenario: Alerta crítica nocturna con gas elevado
  Dado que son las 02:15 de la madrugada
  Y el sensor de gas reporta 450 ppm (umbral: 400 ppm)
  Y el sensor de movimiento detecta presencia
  Y la cámara NO detecta una persona conocida
  Cuando el LangGraph Agent recibe el estado completo del hogar
  Entonces el LLM clasifica la alerta como "critico"
  Y el agente decide activar el LED de alerta
  Y el agente decide activar el buzzer
  Y el agente publica un mensaje de alerta en smarthome/equipo69/llm/decision
  Y el razonamiento explica por qué la situación es crítica

Escenario: Estado normal sin acciones necesarias
  Dado que la temperatura es 25°C (umbral: 28°C)
  Y el gas es 200 ppm (umbral: 400 ppm)
  Y no hay movimiento detectado
  Cuando el LangGraph Agent evalúa el estado
  Entonces el nivel de alerta es "normal"
  Y NO se activa ningún actuador
  Y el razonamiento indica que todos los valores están dentro de rangos seguros

Escenario: Alerta media por temperatura elevada
  Dado que la temperatura es 32°C (umbral: 28°C)
  Y el gas está en 200 ppm (normal)
  Y es de día (14:00)
  Cuando el LangGraph Agent evalúa el estado
  Entonces el nivel de alerta es "medio"
  Y el agente publica un mensaje de advertencia
  Y NO activa buzzer porque no es una emergencia inmediata
```

---

### T-010: Interfaz de consulta en lenguaje natural

**Tipo:** Historia de Usuario
**Prioridad:** 🟡 Media
**Unidad:** 2
**Servicio:** Node-RED Dashboard + LLM Gateway
**Dependencias:** T-007, T-011

#### Descripción
**Como** usuario del sistema SmartHome, **quiero** poder hacer preguntas en español sobre el estado del hogar desde el dashboard, **para** entender la situación sin tener que interpretar datos crudos de sensores.

#### Criterios de Aceptación

```gherkin
Escenario: Consulta de temperatura por lenguaje natural
  Dado que el dashboard de Node-RED está accesible
  Y el campo de texto de consulta NL está visible
  Y la temperatura actual es 29.5°C
  Cuando el usuario escribe "¿Cuál es la temperatura del living?"
  Y presiona enviar
  Entonces el sistema responde en el dashboard con la temperatura actual en texto natural
  Y la respuesta es coherente con el valor real del sensor

Escenario: Consulta de estado general
  Dado que el dashboard tiene el campo de consulta NL
  Y los sensores reportan temp=31°C, gas=420ppm, movimiento=si
  Cuando el usuario escribe "Resume el estado del hogar en una frase"
  Entonces el sistema responde con un resumen en español que menciona los valores anómalos
  Y la respuesta incluye una advertencia sobre el gas elevado

Escenario: Pregunta sobre seguridad
  Dado que los niveles de gas son 450 ppm
  Cuando el usuario escribe "¿Es seguro dormir con estos niveles de gas?"
  Entonces el sistema responde que NO es seguro
  Y explica brevemente por qué
```

---

### T-011: Actualizar flujos Node-RED (TLS + integración LLM)

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 2
**Servicio:** Node-RED
**Dependencias:** T-001, T-007

#### Contexto
Los flujos actuales de Node-RED usan MQTT sin TLS y no integran el LLM Gateway. Hay que actualizar los nodos MQTT para usar TLS + credenciales, agregar el trigger hacia el LLM Gateway, y exponer la interfaz de consulta NL.

#### Descripción
Modificar `nodered/flows.json`: actualizar broker MQTT config a TLS (puerto 8883, credenciales), agregar nodo HTTP Request que envía estado de sensores a `POST /llm/decide`, agregar nodos que reciben y parsean la respuesta, y agregar el campo de texto NL + display de respuesta en el dashboard. Manejar credenciales via variables de entorno (no hardcodear).

#### Criterios de Aceptación

```gherkin
Escenario: Node-RED se conecta a broker MQTT seguro
  Dado que Node-RED está desplegado con los flujos actualizados
  Y las variables de entorno MQTT_TLS_CA, MQTT_USER, MQTT_PASS están configuradas
  Cuando Node-RED inicia
  Entonces el nodo MQTT se conecta exitosamente al broker en puerto 8883
  Y muestra estado "connected" en el dashboard

Escenario: Node-RED envía estado al LLM Gateway y procesa respuesta
  Dado que el flujo de Node-RED está corriendo
  Y recibe un mensaje MQTT en smarthome/equipo69/datos
  Cuando el flujo dispara una solicitud HTTP POST al LLM Gateway /llm/decide
  Entonces el LLM Gateway responde con JSON de decisión
  Y Node-RED publica los comandos MQTT resultantes
  Y actualiza el dashboard con el nivel de alerta y razonamiento
```

---

### T-012: Análisis de vulnerabilidad IoT

**Tipo:** Historia Técnica
**Prioridad:** 🟡 Media
**Unidad:** 2
**Servicio:** Documentación
**Dependencias:** T-001, T-002

#### Contexto
La rúbrica exige documentar al menos una vulnerabilidad conocida del stack IoT con propuesta de mitigación. Con el sistema ya asegurado (TLS + auth + ACLs), se debe analizar qué vulnerabilidades persisten o existían antes.

#### Descripción
Identificar, documentar y proponer mitigación para al menos una vulnerabilidad del stack (ej: MQTT sin autenticación — estado anterior, firmware sin OTA segura, broker expuesto, ausencia de rate limiting). Incluir análisis de impacto y remediación.

#### Criterios de Aceptación

```gherkin
Escenario: Documento de vulnerabilidad completo
  Dado que se identificó una vulnerabilidad en el stack IoT
  Cuando se redacta la sección de seguridad para el informe
  Entonces el documento incluye: nombre de la vulnerabilidad, vector de ataque, impacto potencial, medida de mitigación implementada
  Y la mitigación es técnicamente correcta y verificable
```

---

## Unidad 3 — Gemelo Digital y Agente Autónomo

---

### T-013: Docker Compose stack completo

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 3
**Servicio:** Infraestructura — Docker Compose
**Dependencias:** T-001 (config Mosquitto reutilizada)

#### Contexto
Todo el sistema debe poder iniciarse con `docker compose up -d`. El archivo `docker-compose.yml` debe orquestar Mosquitto, InfluxDB, Grafana, Node-RED, y los microservicios nuevos (LLM Gateway con LangGraph, Digital Twin, CoAP Bridge, Prediction Engine, Alert Manager).

#### Descripción
Crear `docker-compose.yml` en `unidad3/` con todos los servicios. Configurar redes internas, volúmenes persistentes, variables de entorno, healthchecks, y dependencias entre servicios. Ollama corre en el host (no en Docker).

#### Criterios de Aceptación

```gherkin
Escenario: Todos los servicios levantan con un comando
  Dado que el archivo docker-compose.yml está en unidad3/
  Cuando se ejecuta docker compose up -d
  Entonces todos los servicios inician sin errores en menos de 60 segundos
  Y docker compose ps muestra todos los servicios con estado "healthy" o "running"

Escenario: Servicios se comunican entre sí
  Dado que el stack Docker está corriendo
  Cuando Node-RED publica un mensaje MQTT en el broker
  Entonces el Digital Twin Service recibe la actualización
  Y InfluxDB registra la métrica
  Y Grafana puede consultar InfluxDB

Escenario: Reinicio de servicios preserva datos
  Dado que el stack está corriendo con datos en InfluxDB
  Cuando se ejecuta docker compose down y docker compose up -d
  Entonces los datos históricos en InfluxDB persisten
  Y Grafana mantiene sus dashboards configurados
```

---

### T-014: InfluxDB — ingesta MQTT y políticas de retención

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 3
**Servicio:** Infraestructura — InfluxDB + Telegraf o custom ingester
**Dependencias:** T-013

#### Contexto
InfluxDB 2.7 almacenará todas las series de tiempo de sensores. Se necesita un mecanismo de ingesta desde MQTT (puede ser Telegraf con plugin MQTT o un servicio propio). Debe configurarse bucket, organización, token y política de retención.

#### Descripción
Configurar InfluxDB con bucket `sensores`, organización `smarthome`. Implementar ingesta MQTT→InfluxDB (vía Telegraf o un microservicio ingester). Configurar retención de 7 días para datos crudos, 30 días para agregaciones.

#### Criterios de Aceptación

```gherkin
Escenario: Datos MQTT se escriben en InfluxDB
  Dado que InfluxDB está corriendo y el ingester está configurado
  Cuando el MKR1000 publica temperatura=29.5 en smarthome/equipo69/datos
  Entonces en menos de 5 segundos el dato aparece en el bucket "sensores"
  Y se puede consultar con Flux: from(bucket:"sensores") |> range(start: -1m)

Escenario: Retención de datos configurada
  Dado que la política de retención está configurada a 7 días
  Cuando se insertan datos con timestamp de hace 8 días
  Entonces esos datos son eliminados automáticamente
  Y los datos de hace 6 días permanecen consultables
```

---

### T-015: Microservicio Digital Twin + API REST

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 3
**Servicio:** Digital Twin Service (Python/FastAPI)
**Dependencias:** T-001 (MQTT), T-013

#### Contexto
El Gemelo Digital es un objeto JSON persistente con el estado completo del hogar, historial de 1 hora, predicciones y resumen del LLM. Debe mantenerse sincronizado vía MQTT y exponerse por API REST. Esto reemplaza la implementación sugerida en Node-RED por un servicio dedicado más robusto.

#### Descripción
Microservicio FastAPI que: (a) se suscribe a `smarthome/equipo69/#` vía MQTT, (b) mantiene en memoria el estado completo con los últimos 60 registros por sensor, (c) expone `GET /gemelo/estado` con el JSON completo, (d) persiste snapshot a disco cada 30 segundos para recuperación tras restart.

#### Criterios de Aceptación

```gherkin
Escenario: API REST retorna estado completo actualizado
  Dado que el Digital Twin Service está corriendo
  Y los sensores están publicando datos vía MQTT
  Cuando se hace GET /gemelo/estado
  Entonces la respuesta contiene el JSON con estado_actual, historial_1h, alertas_activas, prediccion_30min, resumen_llm
  Y los valores de estado_actual coinciden con la última publicación MQTT de cada sensor

Escenario: Historial de 1 hora con 60 registros
  Dado que el Digital Twin Service lleva corriendo más de 1 hora
  Y los sensores publican cada 1 minuto
  Cuando se consulta GET /gemelo/estado
  Entonces el array historial_1h contiene exactamente 60 entradas
  Y cada entrada tiene timestamp, temperatura, humedad y gas

Escenario: Recuperación tras reinicio
  Dado que el Digital Twin Service se detuvo inesperadamente
  Y existía un snapshot en disco de hace menos de 30 segundos
  Cuando el servicio reinicia
  Entonces carga el estado desde el snapshot
  Y reanuda la sincronización MQTT desde el último timestamp guardado
```

---

### T-016: Microservicio Prediction Engine

**Tipo:** Historia Técnica
**Prioridad:** 🔴 Alta
**Unidad:** 3
**Servicio:** Prediction Engine Service (Python)
**Dependencias:** T-001, T-014, T-015

#### Contexto
El Prediction Engine debe ejecutarse cada 10 minutos, consultar el historial de las últimas 6 horas desde InfluxDB (o Digital Twin), calcular regresión lineal con `sklearn.linear_model.LinearRegression` para temperatura y gas, proyectar a 30 minutos, y publicar los resultados en MQTT. Si la predicción supera umbrales, debe publicar alerta preventiva.

#### Descripción
Microservicio Python con timer interno (cada 10 min). Consulta InfluxDB vía Flux query para últimas 6h de temp y gas. Entrena `LinearRegression` de sklearn sobre los timestamps (convertidos a minutos relativos) y valores del sensor, y proyecta 30 min hacia adelante. Publica en `prediccion/temperatura` y `prediccion/gas`. Si el valor proyectado supera el umbral, publica alerta preventiva en `smarthome/equipo69/alerta`.

#### Criterios de Aceptación

```gherkin
Escenario: Predicción publicada en MQTT cada 10 minutos
  Dado que el Prediction Engine está corriendo
  Y existen al menos 20 puntos de datos históricos en InfluxDB
  Cuando transcurren 10 minutos desde la última predicción
  Entonces se publica un mensaje en smarthome/equipo69/prediccion/temperatura con valor proyectado y horizon_min=30
  Y se publica un mensaje en smarthome/equipo69/prediccion/gas con valor proyectado y horizon_min=30

Escenario: Alerta preventiva cuando predicción supera umbral
  Dado que la temperatura proyectada a 30 min es 31.2°C (umbral: 28°C)
  Cuando el Prediction Engine calcula la proyección
  Entonces publica en smarthome/equipo69/alerta un mensaje con "tipo": "preventiva"
  Y el mensaje incluye el sensor afectado y el valor proyectado

Escenario: Predicción con datos insuficientes
  Dado que existen menos de 5 puntos de datos históricos
  Cuando el Prediction Engine intenta calcular la regresión
  Entonces registra un warning en logs
  Y NO publica predicciones (evita datos inválidos)
```

---

### T-017: LangGraph Agent autónomo con acciones en cadena (Unidad 3)

**Tipo:** Historia de Usuario
**Prioridad:** 🔴 Alta
**Unidad:** 3
**Servicio:** LLM Gateway Service (módulo LangGraph extendido)
**Dependencias:** T-009, T-015, T-016, T-018

#### Descripción
**Como** administrador del hogar inteligente, **quiero** que el agente autónomo tome secuencias de acciones por sí mismo (activar actuadores, enviar notificaciones, ajustar umbrales) basándose en el estado actual, historial y predicciones, **para** que el sistema reaccione proactivamente sin intervención humana.

#### Criterios de Aceptación

```gherkin
Escenario: Agente ejecuta múltiples acciones ante evento crítico
  Dado que el sensor de gas reporta 480 ppm
  Y la predicción indica tendencia al alza (proyectado 510 ppm en 30 min)
  Y es de noche (23:00)
  Cuando el LangGraph Agent evalúa el contexto completo (estado + historial + predicción)
  Entonces el agente decide ejecutar estas acciones en orden:
    - activar_actuador("led", true)
    - activar_actuador("buzzer", true)
    - enviar_notificacion("⚠️ Gas crítico: 480 ppm. Tendencia al alza. Verificar cocina.")
    - registrar_evento("Alerta crítica de gas activada automáticamente")
  Y cada acción se ejecuta correctamente y se registra en el log

Escenario: Agente ajusta umbral dinámicamente
  Dado que la temperatura promedio de los últimos 7 días es 30°C
  Y el umbral actual es 28°C (generando alertas constantes)
  Cuando el LangGraph Agent analiza el patrón histórico
  Entonces decide ajustar el umbral de temperatura a 32°C
  Y publica el nuevo umbral vía MQTT
  Y registra el razonamiento: "Umbral ajustado por contexto histórico para reducir falsos positivos"

Escenario: Log de decisiones del agente en InfluxDB
  Dado que el agente tomó una decisión
  Cuando ejecuta las acciones
  Entonces guarda en InfluxDB un registro con: timestamp, razonamiento, lista de acciones ejecutadas, estado del gemelo al momento de la decisión
  Y este registro es consultable desde Grafana

Escenario: Agente se activa automáticamente cada 5 minutos (scheduler interno)
  Dado que el LLM Gateway Service está corriendo
  Y el scheduler interno (APScheduler/asyncio) está configurado a 5 minutos
  Cuando transcurren 5 minutos
  Entonces el LangGraph Agent consulta el Digital Twin vía MCP tool get_sensor_state
  Y evalúa el estado completo del hogar
  Y ejecuta acciones si corresponde
  Y registra el ciclo en logs (incluso si no tomó acciones)

Escenario: Agente se activa por webhook ante evento crítico
  Dado que el LLM Gateway expone POST /llm/decide como webhook
  Cuando Node-RED detecta un evento crítico y llama al webhook
  Entonces el LangGraph Agent evalúa la situación inmediatamente sin esperar el ciclo de 5 min
  Y la prioridad del análisis es elevada (timeout más corto en Ollama, reintentos agresivos)
```

---

### T-018: Microservicio Alert Manager

**Tipo:** Historia Técnica
**Prioridad:** 🟡 Media
**Unidad:** 3
**Servicio:** Alert Manager Service (Python)
**Dependencias:** T-001, T-013

#### Contexto
Actualmente el envío de notificaciones Telegram está acoplado a Node-RED. Un Alert Manager dedicado centraliza la lógica de notificaciones, aplica deduplicación, rate limiting, y expone una API para que cualquier servicio (LLM Gateway, Prediction Engine, Grafana) pueda enviar alertas sin conocer detalles de Telegram.

#### Descripción
Microservicio que: se suscribe a `smarthome/equipo69/alerta`, mantiene estado de alertas activas (evita spam), aplica cooldown de 5 minutos por tipo de alerta, envía mensajes vía Telegram Bot API, y expone `POST /alertas` para otros servicios. Futuro: email, webhook.

#### Criterios de Aceptación

```gherkin
Escenario: Alerta se envía por Telegram sin duplicados
  Dado que el Alert Manager está corriendo
  Y el bot de Telegram está configurado
  Cuando se publica una alerta de gas en smarthome/equipo69/alerta
  Entonces el Alert Manager envía un mensaje de Telegram al chat configurado
  Cuando se publica la misma alerta 2 minutos después
  Entonces el Alert Manager NO reenvía el mensaje (cooldown de 5 min activo)

Escenario: API REST para enviar alertas
  Dado que el Alert Manager expone POST /alertas
  Cuando el Prediction Engine envía {"sensor": "temperatura", "valor": 31.2, "tipo": "preventiva"}
  Entonces el Alert Manager procesa la solicitud
  Y envía la notificación por Telegram si el cooldown lo permite

Escenario: Múltiples tipos de alerta coexisten
  Dado que hay una alerta de gas activa (en cooldown)
  Cuando se publica una alerta de temperatura (tipo diferente)
  Entonces el Alert Manager envía la notificación de temperatura inmediatamente
  Y mantiene cooldowns independientes por tipo de alerta
```

---

### T-019: ~~Integración n8n~~ — ELIMINADA

> **Motivo:** LangGraph Agent (T-017) incluye su propio scheduler interno con `asyncio`/`APScheduler`. n8n es redundante en esta arquitectura. La spec original asume que no hay un servicio dedicado para el agente; nosotros sí lo tenemos.

---

### T-020: Dashboard Grafana completo

**Tipo:** Historia de Usuario
**Prioridad:** 🔴 Alta
**Unidad:** 3
**Servicio:** Grafana
**Dependencias:** T-013, T-014, T-016, T-017

#### Descripción
**Como** administrador del sistema, **quiero** visualizar en Grafana las series de tiempo de todos los sensores, las predicciones superpuestas, el log de decisiones del agente y el estado del gemelo digital, **para** monitorear el hogar y auditar las decisiones automáticas del sistema.

#### Criterios de Aceptación

```gherkin
Escenario: Panel de series de tiempo con datos de sensores
  Dado que Grafana está conectado a InfluxDB
  Y los sensores están publicando datos
  Cuando se abre el dashboard de SmartHome
  Entonces se muestran gráficos de temperatura, humedad y gas de las últimas 6 horas
  Y los gráficos se actualizan automáticamente cada 10 segundos

Escenario: Panel de predicción con valores reales superpuestos
  Dado que el Prediction Engine está publicando proyecciones
  Cuando se observa el panel de predicción en Grafana
  Entonces se muestra la serie de temperatura real (línea sólida)
  Y se muestra la proyección a 30 minutos (línea punteada)
  Y ambas series son visualmente distinguibles

Escenario: Panel de log de decisiones del agente
  Dado que el LangGraph Agent ha tomado decisiones
  Cuando se abre el panel de log en Grafana
  Entonces se muestra una tabla con: timestamp, razonamiento, acciones ejecutadas
  Y cada fila es una decisión del agente

Escenario: Panel de estado del gemelo digital
  Dado que el Digital Twin está sincronizado
  Cuando se abre el panel de estado en Grafana
  Entonces se muestra una tabla con el último valor de cada variable (temp, humedad, gas, movimiento, persona, led, buzzer)
  Y incluye el timestamp de última actualización
```

---

### T-021: Alertas Grafana configuradas

**Tipo:** Historia Técnica
**Prioridad:** 🟡 Media
**Unidad:** 3
**Servicio:** Grafana
**Dependencias:** T-018, T-020

#### Contexto
Grafana debe tener al menos una alerta configurada que dispare notificación cuando temperatura o gas supere el umbral. La notificación puede ser vía webhook al Alert Manager o correo directo.

#### Descripción
Configurar alert rules en Grafana: (a) temperatura > 28°C por más de 2 minutos consecutivos, (b) gas > 400 ppm por más de 1 minuto. Configurar contact point vía webhook al Alert Manager (`POST /alertas`) o SMTP.

#### Criterios de Aceptación

```gherkin
Escenario: Alerta de temperatura se dispara
  Dado que la alerta de temperatura está configurada (umbral 28°C, 2 min)
  Y la temperatura reportada es 30°C durante más de 2 minutos
  Cuando Grafana evalúa la alert rule
  Entonces el estado de la alerta cambia a "firing"
  Y se envía una notificación al contact point configurado

Escenario: Alerta se resuelve automáticamente
  Dado que una alerta de temperatura está en estado "firing"
  Cuando la temperatura baja a 27°C por más de 2 minutos
  Entonces el estado de la alerta cambia a "ok"
  Y se envía una notificación de resolución
```

---

### T-022: Análisis de aplicación industrial

**Tipo:** Historia Técnica
**Prioridad:** 🟢 Baja
**Unidad:** 3
**Servicio:** Documentación
**Dependencias:** T-013 a T-021 (sistema funcionando)

#### Contexto
La rúbrica exige investigar cómo el sistema SmartHome podría escalarse a un contexto industrial. El equipo debe elegir un dominio (servidores, agricultura, microrred, edificio inteligente) y documentar la adaptación.

#### Descripción
Elegir un contexto industrial (se recomienda "Monitoreo de sala de servidores" por cercanía con el stack actual), dibujar diagrama de arquitectura adaptada, justificar protocolos a escala industrial, identificar desafíos de escalabilidad, y explicar cómo el agente LLM aporta valor operacional.

#### Criterios de Aceptación

```gherkin
Escenario: Sección industrial completa en el informe
  Dado que se eligió un contexto industrial
  Cuando se redacta la sección correspondiente del informe
  Entonces incluye: diagrama de arquitectura adaptada, justificación de protocolos, al menos 3 desafíos de escalabilidad identificados, valor operacional del agente LLM
  Y el diagrama es claro y técnicamente correcto
```

---

### T-023: Informe técnico Unidad 2

**Tipo:** Historia Técnica
**Prioridad:** 🟡 Media
**Unidad:** 2
**Servicio:** Documentación
**Dependencias:** T-001 a T-012

#### Contexto
El informe de Unidad 2 agrega 5-8 páginas al informe de Unidad 1. Debe cubrir: MQTT seguro, comparativa CoAP vs MQTT, arquitectura LLM, análisis de seguridad, capturas del dashboard NL funcionando, problemas encontrados y reflexión crítica.

#### Descripción
Redactar las secciones nuevas del informe técnico con diagramas, capturas de pantalla, tablas comparativas, y reflexión crítica sobre cuándo el LLM es más útil que reglas clásicas.

#### Criterios de Aceptación

```gherkin
Escenario: Informe Unidad 2 completo según rúbrica
  Dado que todas las funcionalidades de Unidad 2 están implementadas
  Cuando se revisa el informe contra la rúbrica
  Entonces cubre los 7 puntos listados en la sección 6c del documento de requerimientos
  Y tiene entre 5 y 8 páginas adicionales
  Y cada sección incluye evidencia (capturas, diagramas, tablas)
```

---

### T-024: Informe consolidado final

**Tipo:** Historia Técnica
**Prioridad:** 🟡 Media
**Unidad:** 3
**Servicio:** Documentación
**Dependencias:** T-023, T-013 a T-022

#### Contexto
El informe final consolida las 3 unidades en un solo documento de 20-30 páginas. Debe agregar las secciones nuevas de Unidad 3 y unificar el formato.

#### Descripción
Integrar los informes de Unidades 1, 2 y 3 en un documento consolidado. Agregar secciones: arquitectura Docker, gemelo digital, predicción, agente autónomo, dashboard Grafana, análisis industrial, reflexión crítica sobre LLM como controlador IoT (latencia, no-determinismo, fallos de parseo JSON), y conclusiones generales.

#### Criterios de Aceptación

```gherkin
Escenario: Informe final completo según rúbrica Unidad 3
  Dado que las 3 unidades están implementadas y documentadas
  Cuando se revisa el informe consolidado contra la rúbrica
  Entonces cubre los 8 puntos listados en la sección 6c de Unidad 3
  Y tiene entre 20 y 30 páginas totales
  Y la reflexión crítica aborda latencia, no-determinismo y fallos de parseo del LLM
  Y las conclusiones integran aprendizajes de las 3 unidades
```

---

## 📊 Resumen de dependencias

```
Unidad 2:
T-001 ──┬── T-002
        ├── T-003
        ├── T-005 ─── T-004
        └── T-007 ─── T-006
             ├── T-008 ─── T-015 (U3)
             ├── T-009
             └── T-011 ─── T-010
        T-012 (puede empezar después de T-002)

Unidad 3:
T-013 ──┬── T-014
        ├── T-015 ─── T-008 (dato de U2)
        ├── T-016 ─── T-014, T-015
        ├── T-017 ─── T-009, T-015, T-016, T-018
        ├── T-018
        ├── T-020 ─── T-014, T-016, T-017
        └── T-021 ─── T-018, T-020

Documentación:
T-023 ─── T-001..T-012
T-024 ─── T-023, T-013..T-022
T-022 ─── T-013..T-021
```

---

## 🏷️ Labels sugeridas para GitHub Issues

| Label | Descripción |
|-------|-------------|
| `unidad-2` | Tareas de la Unidad 2 |
| `unidad-3` | Tareas de la Unidad 3 |
| `microservicio` | Tareas que implementan un nuevo microservicio |
| `firmware` | Cambios en ESP32/MKR1000 |
| `infraestructura` | Docker, Mosquitto, redes |
| `langgraph` | Tareas relacionadas con LangGraph Agent |
| `documentacion` | Informes y análisis |
| `frontend` | Dashboard, Grafana, UI |
| `user-story` | Historias de usuario |
| `tech-task` | Historias técnicas |
