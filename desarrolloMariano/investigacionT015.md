# Investigación y Plan de Implementación: T-015 Microservicio Digital Twin + API REST

Este documento detalla la investigación, diseño de arquitectura y el roadmap de desarrollo para la tarea **T-015: Microservicio Digital Twin + API REST**, considerando las especificaciones del proyecto:
1. Las predicciones numéricas a 30 minutos se realizan utilizando un **modelo local de Regresión Lineal** para las variables continuas (`temperatura`, `humedad` y `gas`).
2. La variable `sensor_extra` (sonido) **no se predice** porque no es continua.
3. El **LLM local** (`phi3:mini` / `llama3.2:3b` en el `llm-gateway`) se utiliza para responder consultas en **lenguaje natural** sobre el estado y las predicciones (ej: *"¿Cuál será la temperatura en los próximos 30 minutos?"*).
4. Todo se ejecuta de forma **local**.

---

## 1. Análisis del Problema y Requerimientos

### ¿Qué es el Digital Twin en este contexto?
El Digital Twin del hogar inteligente es un microservicio en Python/FastAPI que actúa como el "cerebro de datos" del sistema. Mantiene un **objeto JSON consolidado y persistente en memoria** que refleja:
1. **Estado Actual:** El último valor reportado por los sensores y actuadores (`temperatura`, `humedad`, `gas`, `movimiento`, `persona`, `led`, `buzzer`).
2. **Historial Reciente (1h):** Los últimos 60 registros por sensor (resolución de 1 minuto).
3. **Alertas Activas:** Lista de anomalías vigentes.
4. **Predicción a 30 minutos (Regresión Lineal):** Proyecciones calculadas localmente para `temperatura`, `humedad` y `gas`.
5. **Resumen y Respuestas de Lenguaje Natural:** Facilitado al integrarse con el LLM del compañero, permitiendo que el LLM consulte este Digital Twin para responder preguntas del usuario.

### División de Responsabilidades: Regresión Lineal vs LLM
* **Predicción Numérica (Regresión Lineal Local):**
  - El Digital Twin utilizará un modelo matemático de regresión lineal simple (utilizando `numpy.polyfit` o `scikit-learn` de forma local) sobre los últimos 60 minutos de datos históricos.
  - Esto calcula de forma eficiente, rápida y determinista la proyección del valor a $+30$ minutos.
* **Interfaz de Lenguaje Natural (LLM Local):**
  - El LLM recibe la pregunta del usuario (ej: *"¿Cómo estará el gas en media hora?"*).
  - A través de la API REST del Digital Twin (o por medio de herramientas MCP), el LLM obtiene el contexto de las predicciones calculadas por regresión lineal.
  - El LLM redacta una respuesta coherente en lenguaje natural en español (ej: *"Se proyecta que el gas subirá a 450 ppm en los próximos 30 minutos, lo cual supera el umbral de alerta. Te sugiero ventilar el área."*).

### Graficación de Predicciones
Para permitir la superposición de datos reales y predicciones en Grafana:
* El Digital Twin publicará las predicciones calculadas por regresión lineal en tópicos MQTT dedicados:
  - `smarthome/equipo69/prediccion/temperatura` -> `{"valor": 31.2, "horizon_min": 30}`
  - `smarthome/equipo69/prediccion/humedad` -> `{"valor": 72.5, "horizon_min": 30}`
  - `smarthome/equipo69/prediccion/gas` -> `{"valor": 480.0, "horizon_min": 30}`
* El motor de ingesta registrará estos tópicos de predicción en InfluxDB, permitiendo que Grafana dibuje las curvas correspondientes (línea sólida para real, línea punteada para predicción).

---

## 2. Arquitectura del Servicio

El servicio se construirá en **Python** utilizando **FastAPI** y se integrará en el stack de Docker Compose.

```
                  ┌──────────────────────┐
                  │   Arduino/ESP32-CAM  │
                  └──────────┬───────────┘
                             │ MQTT (T-001)
                             ▼
                  ┌──────────────────────┐
                  │   Mosquitto Broker   │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────────────┐
            │ MQTT: smarthome/equipo69/#              │
            ▼                                         ▼
┌────────────────────────┐                  ┌──────────────────────┐
│     Digital Twin       │                  │     LLM Gateway      │
│ (FastAPI - Port 8003)  │                  │   (FastAPI :8001)    │
├────────────────────────┤                  ├──────────────────────┤
│ * Regresión Lineal     │                  │ * Inferencia Ollama  │
│ * Historial (60 min)   │                  │ * Procesa queries NL │
│ * API /gemelo/estado   │◄─────────────────┤ * Consume API Twin   │
└──────────┬─────────────┘    HTTP REST     └──────────────────────┘
           │
           │ MQTT (Publica predicciones reales vs estimadas)
           ▼
```

### Componentes Clave del Microservicio:
1. **Cliente MQTT (paho-mqtt):** Se conecta de forma asíncrona al broker Mosquitto. Se suscribe a `smarthome/equipo69/datos` para capturar lecturas en tiempo real y a los comandos de control.
2. **Motor de Estado e Historial:**
   - Un hilo o corutina almacena las lecturas y calcula promedios de 1 minuto para guardarlos en colas de tamaño fijo (`collections.deque(maxlen=60)`).
3. **Módulo de Regresión Lineal (`predictor.py`):**
   - Implementa una función local que toma el array de marcas de tiempo relativas y los valores de cada sensor (`temperatura`, `humedad`, `gas`).
   - Calcula la pendiente y el intercepto (`y = m*x + c`) para extrapolar el valor en $t + 30$ minutos.
4. **Persistencia (Snapshot):** Guarda a disco en `/app/data/twin_snapshot.json` cada 30 segundos y restaura el estado al iniciar.
5. **API REST (FastAPI):** Expone `GET /gemelo/estado` para que el LLM Gateway, n8n/LangGraph o Grafana consulten el estado actual, el histórico y las predicciones lineales vigentes.

---

## 3. Formato del Estado del Digital Twin

Estructura del JSON retornado por `GET /gemelo/estado`:

```json
{
  "ultimo_update": "2026-06-17T12:54:40Z",
  "estado_actual": {
    "temperatura": 29.5,
    "humedad": 70.0,
    "gas": 420,
    "movimiento": true,
    "persona": false,
    "led": false,
    "buzzer": false,
    "sensor_extra": 128
  },
  "historial_1h": [
    {"ts": "2026-06-17T12:00:00Z", "temperatura": 27.2, "humedad": 65.5, "gas": 300},
    {"ts": "2026-06-17T12:15:00Z", "temperatura": 28.0, "humedad": 67.0, "gas": 350},
    {"ts": "2026-06-17T12:30:00Z", "temperatura": 28.8, "humedad": 68.2, "gas": 390},
    {"ts": "2026-06-17T12:45:00Z", "temperatura": 29.2, "humedad": 69.5, "gas": 410}
  ],
  "alertas_activas": [
    "gas_alto"
  ],
  "prediccion_30min": {
    "valores": {
      "temperatura": 31.2,
      "humedad": 72.5,
      "gas": 480.0
    },
    "metodo": "linear_regression",
    "timestamp_prediccion": "2026-06-17T13:24:40Z"
  }
}
```

---

## 4. Integración del LLM para Consultas en Lenguaje Natural

Cuando el usuario interactúe con el dashboard preguntando sobre el estado futuro (ej: *"¿Subirá la temperatura en la próxima media hora?"*):

1. **Node-RED / Dashboard** captura la pregunta y la envía al `llm-gateway` (`POST /llm/query`).
2. El **LLM Gateway** (o el MCP Server a través de la herramienta `get_sensor_state`) realiza una llamada interna a `GET /gemelo/estado` para obtener el contexto completo (incluyendo el bloque `"prediccion_30min"` calculado matemáticamente por el Digital Twin).
3. Se inyecta este JSON al prompt del LLM local de forma transparente:
   ```
   Pregunta del usuario: "{{PREGUNTA_USUARIO}}"
   
   Contexto del Gemelo Digital (Valores actuales y predicciones calculadas por regresión lineal a 30 minutos):
   {{JSON_GEMELO_DIGITAL}}
   
   Responde la pregunta del usuario en español de manera clara, concisa y usando los datos provistos.
   ```
4. El LLM responde con texto enriquecido que se muestra directamente al usuario en el Dashboard de Node-RED.

---

## 5. Roadmap e Implementation Plan

### Fase 1: Estructura del Microservicio y Conexión MQTT
* **Objetivo:** Inicializar el microservicio, conectarlo al broker seguro y recolectar las variables en memoria.
* **Tareas:**
  1. Crear el directorio `src/digital_twin/` y configurar `requirements.txt` (`fastapi`, `uvicorn`, `paho-mqtt`, `numpy`).
  2. Implementar la clase de conexión MQTT segura (TLS, autenticación) en `mqtt_client.py`.
  3. Crear el buffer en memoria en `state_manager.py` para almacenar el estado y consolidar promedios de 1 minuto para el `historial_1h`.
  4. Crear los endpoints básicos de FastAPI.

### Fase 2: Módulo de Regresión Lineal y Snapshot
* **Objetivo:** Calcular proyecciones lineales localmente y persistir los datos de recuperación.
* **Tareas:**
  1. Desarrollar `predictor.py` con una función matemática (usando `numpy.polyfit` o fórmulas manuales de mínimos cuadrados) que tome el historial y calcule el valor a $+30$ minutos de `temperatura`, `humedad` y `gas`.
  2. Configurar la tarea periódica asíncrona para actualizar la predicción cada 10 minutos y publicarla en MQTT.
  3. Implementar el guardado/carga del snapshot JSON en disco.

### Fase 3: Integración del LLM para Consultas en Lenguaje Natural (NL)
* **Objetivo:** Permitir que el LLM del compañero acceda a las predicciones para contestar preguntas sobre el futuro del hogar.
* **Tareas:**
  1. Configurar/coordinar el endpoint en `llm-gateway` o la herramienta MCP del sidecar para que lea las predicciones del endpoint del Digital Twin.
  2. Diseñar y validar prompts en el LLM local para asegurar respuestas precisas basadas en los datos de la regresión lineal.

### Fase 4: Despliegue en Docker Compose y Dashboard Grafana
* **Objetivo:** Desplegar en producción local y configurar la visualización de las proyecciones.
* **Tareas:**
  1. Crear el `Dockerfile` del Digital Twin y agregarlo a `deploy/docker-compose.yml`.
  2. Asegurar la ingesta de los tópicos de predicción MQTT hacia InfluxDB.
  3. Configurar el dashboard en Grafana con los gráficos superpuestos (valores reales vs proyectados).
  4. Validar el flujo extremo a extremo.

---

Elaborado por: **Mariano**  
Fecha de modificación: 17 de Junio, 2026
