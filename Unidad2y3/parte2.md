# Parte 2: Unidad 3 - IoT en la Industria - Gemelo Digital y Agente Autónomo

## 1. Introducción

En esta fase final el sistema SmartHome evoluciona hacia una arquitectura de nivel productivo. Se incorporan tres capacidades clave:

1. Un **gemelo digital** del hogar que mantiene una representación virtual sincronizada con los sensores físicos.
2. Un **agente IoT autónomo** basado en el LLM local que ejecuta acciones en cadena de forma proactiva.
3. Un **stack de servicios en contenedores** que replica la arquitectura de plataformas industriales locales.

Estas características se relacionan con aplicaciones industriales reales como el monitoreo de plantas de manufactura, gestión de edificios inteligentes, microrredes eléctricas y agricultura de precisión.

## 2. Problema a resolver

Llevar el hogar inteligente al nivel industrial resolviendo las siguientes necesidades:

* **Predicción:** Anticipar cuándo se superarán umbrales críticos basándose en tendencias históricas (proyección a 30 minutos).
* **Agente autónomo:** El LLM debe poder ejecutar secuencias de acciones por sí mismo (ajustar umbrales, activar actuadores, enviar notificaciones) sin intervención manual.
* **Gemelo digital:** Representación virtual del hogar actualizada en tiempo real que sirve como contexto enriquecido para el agente.
* **Infraestructura containerizada:** Todo el stack debe desplegarse con Docker Compose en una sola máquina.

## 3. Objetivo

Implementar un sistema IoT de nivel industrial que integre un gemelo digital, predicción de series de tiempo y un agente autónomo basado en LLM local, desplegado completamente en contenedores Docker sobre la red del laboratorio.

### Objetivos específicos

1. Desplegar el stack completo de servicios (Mosquitto, InfluxDB, Grafana, n8n, Node-RED) usando Docker Compose.
2. Implementar un gemelo digital del hogar como objeto JSON persistente sincronizado con los sensores en tiempo real.
3. Exponer el estado del gemelo digital a través de una API REST accesible por el agente LLM.
4. Desarrollar un script de predicción de series de tiempo para temperatura y gas con proyección a 30 minutos.
5. Implementar el agente autónomo en n8n, capaz de ejecutar acciones en cadena a partir del razonamiento del LLM.
6. Configurar un dashboard en Grafana con visualización histórica, predicciones y log de decisiones del agente.
7. Analizar cómo la arquitectura del sistema puede escalarse o adaptarse a un contexto industrial real.
8. Documentar el sistema completo (Unidades 1, 2 y 3) en un informe técnico consolidado.

---

## 4. Funcionalidades mínimas requeridas

### 4.1 Stack de servicios con Docker Compose

Todo el sistema debe poder iniciarse con un único comando: `docker compose up -d`. El archivo `docker-compose.yml` debe incluir:

```yaml
version: '3.8'
services:
  mosquitto:
    image: eclipse-mosquitto
    ports: ["8883:8883"]
    volumes: ["./mosquitto:/mosquitto/config"]
  influxdb:
    image: influxdb:2.7
    ports: ["8086:8086"]
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_ORG: smarthome
      DOCKER_INFLUXDB_INIT_BUCKET: sensores
  grafana:
    image: grafana/grafana
    ports: ["3000:3000"]
    depends_on: [influxdb]
  n8n:
    image: n8nio/n8n
    ports: ["5678:5678"]
  nodered:
    image: nodered/node-red
    ports: ["1880:1880"]

```

> **Nota técnica:** Ollama no necesita correr dentro de Docker; puede ejecutarse directamente en el sistema operativo del host y ser accedido desde los contenedores usando la dirección `host.docker.internal:11434` (en Linux: `172.17.0.1:11434`).

### 4.2 Gemelo Digital del Hogar

El gemelo digital es un objeto JSON persistente que mantiene el estado completo y el historial reciente. Se implementa en Node-RED o como un archivo JSON. Debe:

* Mantenerse sincronizado con los datos MQTT en tiempo real.
* Almacenar los últimos 60 registros de cada sensor (historial de 1 hora a resolución de 1 minuto).
* Exponer el estado completo a través de una API REST en Node-RED (endpoint **GET** `/gemelo/estado`).
* Incluir un campo `resumen_llm` que el agente actualice con cada ciclo de razonamiento.

*Ejemplo de estructura del gemelo digital:*

```json
{
  "ultimo_update": "2025-06-10T22:15:00",
  "estado_actual": {
    "temperatura": 29.5,
    "humedad": 70,
    "gas": 420,
    "movimiento": true,
    "persona": false,
    "led": false,
    "buzzer": false
  },
  "historial_1h": [
    {"ts": "2025-06-10T21:15:00", "temperatura": 27.0, "gas": 310},
    {"ts": "2025-06-10T21:30:00", "temperatura": 28.1, "gas": 350}
  ],
  "alertas_activas": ["gas_alto"],
  "prediccion_30min": {
    "temperatura": 31.2,
    "gas": 480
  },
  "resumen_llm": "Temperatura en aumento. Gas sobre umbral."
}

```

### 4.3 Predicción con series de tiempo

Implementar un script Python que se ejecute cada 10 minutos para:

1. Consultar el historial de las últimas 6 horas desde InfluxDB (o el CSV de la Unidad 1).
2. Calcular una proyección a 30 minutos usando regresión lineal (`numpy.polyfit`) o la librería Prophet para temperatura y gas.
3. Publicar la predicción en el broker MQTT:
* `smarthome/equipoXX/prediccion/temperatura` -> `{"valor": 31.2, "horizon_min": 30}`
* `smarthome/equipoXX/prediccion/gas` -> `{"valor": 480, "horizon_min": 30}`


4. Si la predicción supera el umbral antes de 30 minutos, publicar adicionalmente una alerta preventiva en `smarthome/equipoXX/alerta` con el campo `"tipo": "preventiva"`.
5. Mostrar en Grafana un panel con los valores reales y la proyección superpuesta.

> **Alternativa liviana:** Si el equipo no quiere instalar Prophet, es suficiente con `numpy.polyfit` de grado 1 (regresión lineal simple) sobre los últimos 20 valores. El objetivo es demostrar el concepto, no la precisión.

### 4.4 Agente IoT Autónomo con n8n y Ollama

El agente es un flujo en n8n que se activa cada 5 minutos o ante un evento MQTT crítico. A diferencia de la Unidad 2, puede ejecutar acciones en cadena de forma autónoma.

#### Flujo del agente

1. **Trigger:** Timer de 5 minutos o Webhook desde Node-RED ante evento crítico.
2. **Obtener contexto:** n8n consulta la API REST del gemelo digital.
3. **Razonar:** n8n envía el contexto al LLM con el siguiente prompt de agente:
```
Eres un agente de control de un hogar inteligente.
Tienes disponibles las siguientes herramientas:
- activar_actuador (dispositivo, estado)
- enviar_notificacion (mensaje)
- registrar_evento (descripcion)
- ajustar_umbral (sensor, nuevo_umbral)

Estado del gemelo digital (JSON): <contexto>

Decide que acciones ejecutar. Responde SOLO en JSON:
{
  "acciones": [
    {
      "herramienta": "activar_actuador",
      "parametros": {"dispositivo": "led", "estado": true}
    },
    {
      "herramienta": "enviar_notificacion",
      "parametros": {"mensaje": "Gas critico, verificar cocina"}
    }
  ],
  "razonamiento": "El gas supera 400 ppm con tendencia..."
}

```


4. **Ejecutar:** n8n parsea el array de acciones y ejecuta cada una (publica en MQTT, llama a la API de Telegram, escribe en InfluxDB, etc.).
5. **Registrar:** El razonamiento y las acciones se guardan en InfluxDB y se muestran en Grafana.

> **Nota técnica:** n8n tiene un nodo nativo *HTTP Request* para llamar a la API de Ollama. Para parsear el JSON de respuesta se puede usar el nodo *Code* con JavaScript, sin requerir plugins adicionales.

### 4.5 Dashboard en Grafana

Complementar el dashboard de Node-RED con Grafana conectado a InfluxDB:

* Panel de series de tiempo para temperatura, humedad y gas (últimas 6 horas).
* Panel de predicción: valores reales más proyección a 30 minutos superpuesta.
* Panel de log de decisiones del agente (tabla con timestamp, razonamiento y acciones).
* Panel de estado del gemelo digital (tabla con el último valor de cada variable).
* Al menos una alerta de Grafana configurada que dispare una notificación (correo o webhook) cuando temperatura o gas superen el umbral.

### 4.6 Análisis de aplicación industrial

Investigar y documentar cómo escalar el sistema a un entorno industrial eligiendo **uno** de los siguientes contextos:

* Monitoreo de sala de servidores (temperatura, humedad, acceso físico, UPS).
* Automatización agrícola (sensores de suelo, riego automático, invernadero).
* Microrred eléctrica (monitoreo de consumo, generación solar, baterías).
* Edificio inteligente (control de acceso, climatización HVAC, eficiencia energética).

Se debe incluir: diagrama de arquitectura adaptada, protocolos recomendados a esa escala, desafíos de escalabilidad y el valor operacional del agente LLM.

---

## 5. Entregables - Unidad 3

* **a) Prototipo funcional:** Stack Docker Compose levantado, gemelo digital sincronizado, predicción en MQTT y agente autónomo demostrable en sala.
* **b) Código fuente:**
* Archivo `docker-compose.yml` funcional.
* Script Python de predicción de series de tiempo.
* Flujo n8n del agente autónomo en formato `.json`.
* Dashboard Grafana exportado en formato `.json`.
* Flujo Node-RED actualizado (gemelo digital + API REST) en formato `.json`.
* Todo dentro de la carpeta `unidad3/` del repositorio.


* **c) Informe técnico final consolidado (20-30 páginas, incluye Unidades 1, 2 y 3):**
1. Arquitectura del stack Docker Compose (servicios y redes).
2. Diseño e implementación del gemelo digital.
3. Descripción del script de predicción (método y gráficos).
4. Diseño del agente autónomo (prompt, herramientas y decisiones reales).
5. Descripción del dashboard Grafana con capturas.
6. Análisis del contexto industrial elegido con diagrama.
7. Reflexión crítica: limitaciones del LLM como controlador IoT (latencia, no-determinismo, fallas de parseo) vs. reglas clásicas.
8. Conclusiones generales del proyecto.


* **d) Defensa oral final (20 minutos):**
* 10 minutos: demostración en vivo del sistema completo (agente tomando decisiones).
* 10 minutos: preguntas técnicas sobre cualquier aspecto de las tres unidades.



---

## 6. Rúbrica de Evaluación - Unidad 3

| Criterio | Pond. | Logrado (4) | Parcial (2-3) | No logrado (1) |
| --- | --- | --- | --- | --- |
| **Stack Docker Compose** | 15% | Todos los servicios levantados y comunicados entre sí correctamente. | Algunos servicios sin integrar o con errores de red. | Docker no implementado. |
| **Gemelo digital** | 20% | Sincronizado en tiempo real, API REST funcional, historial disponible. | Gemelo estático o sin API REST expuesta. | No implementado. |
| **Predicción de series de tiempo** | 15% | Predicción calculada y publicada en MQTT, visualizada en Grafana vs. valor real. | Predicción calculada pero no integrada al sistema. | Sin predicción. |
| **Agente autónomo (n8n + LLM)** | 25% | Agente ejecuta correctamente acciones en cadena ante eventos reales demostrables. | Agente razona correctamente pero no ejecuta todas las acciones. | Agente no implementado. |
| **Dashboard Grafana** | 10% | Completo con historial, predicción, log de agente y alerta configurada. | Dashboard sin predicción o sin alerta configurada. | Sin Grafana. |
| **Análisis industrial** | 10% | Diagrama de arquitectura adaptada, protocolos justificados, análisis de escalabilidad. | Descripción del contexto sin diagrama ni análisis de protocolos. | Sección ausente. |
| **Informe y defensa final** | 5% | Informe consolidado completo, demostración del agente fluida y explicada. | Faltan secciones del informe o la demostración es incompleta. | Sin entrega o sin defensa. |

### Conversión de Puntaje a Nota (Unidad 3)

Calculado sobre 100 puntos utilizando la escala lineal:


$$Nota = 1.0 + \frac{\text{Puntaje obtenido}}{100} \times 6.0$$

| Puntaje obtenido (%) | Nota |
| --- | --- |
| 100 | 7.0 |
| 83 | 6.0 |
| 67 | 5.0 |
| 50 | 4.0 (mínimo aprobatorio) |
| 33 | 3.0 |
| 17 | 2.0 |
| 0 | 1.0 |