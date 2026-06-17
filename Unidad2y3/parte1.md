# Parte 1: Unidad 2 - Protocolos de Comunicación, Seguridad y LLM Local

## 1. Introducción

En esta segunda fase se extiende el sistema SmartHome construido en la Unidad 1 con dos mejoras fundamentales.

Primero, se reemplaza la comunicación MQTT básica por una versión con autenticación y cifrado TLS, y se experimenta con CoAP como protocolo alternativo orientado a dispositivos con recursos limitados.

Segundo, se incorpora un Modelo de Lenguaje Local (LLM) ejecutándose completamente en el computador del equipo, sin acceso a internet, que actuará como el "cerebro" del sistema SmartHome: interpretará el estado del hogar, tomará decisiones de control y responderá preguntas en lenguaje natural.

## 2. Problema a resolver

El sistema SmartHome de la Unidad 1 funciona, pero sus reglas de control son rígidas (estructuras if/else fijas). La familia ahora quiere:

* **Consultar el sistema en lenguaje natural:** "¿Cual es la temperatura del living?", "¿Hay alguien en la casa?".
* **Decisiones contextuales e inteligentes:** Si es de noche, hay movimiento y el gas está elevado, el LLM decide qué actuadores activar y redacta el mensaje de alerta.
* **Comunicación segura:** MQTT con autenticación y cifrado extremo a extremo.
* **Protocolo alternativo:** Explorar CoAP para al menos un sensor de bajo consumo.

## 3. Objetivo

Extender el sistema SmartHome con protocolos de comunicación seguros (MQTT-TLS, CoAP), integrar un modelo de lenguaje ejecutándose localmente (Ollama) para automatización inteligente y consultas en lenguaje natural, y asegurar la infraestructura IoT mediante buenas prácticas de seguridad.

### Objetivos específicos

1. Configurar el broker Mosquitto con autenticación por usuario/contraseña y cifrado TLS.
2. Actualizar el firmware del ESP32 y los flujos de Node-RED para conectarse al broker seguro.
3. Implementar CoAP en al menos un nodo sensor ESP32 y comparar su rendimiento con MQTT.
4. Instalar y configurar Ollama con un modelo liviano (`phi3:mini` o `llama3.2:3b`) para inferencia local.
5. Integrar el LLM en Node-RED para que reemplace las reglas if/else por razonamiento en lenguaje natural.
6. Agregar al dashboard un campo de consulta en lenguaje natural respondido por el LLM.
7. Documentar las medidas de seguridad implementadas y analizar al menos una vulnerabilidad del stack IoT.
8. Extender el informe técnico con las secciones de protocolos, seguridad y LLM.

---

## 4. Funcionalidades mínimas requeridas

### 4.1 MQTT seguro con autenticación y TLS

1. Configurar Mosquitto con usuario y contraseña usando `mosquitto_passwd`.
2. Generar un certificado TLS autofirmado y activar el broker en el puerto 8883.
3. Actualizar el firmware del ESP32 y los flujos de Node-RED para conectarse con TLS.
4. Configurar ACLs en Mosquitto para limitar qué clientes pueden publicar o suscribirse a cada tópico.

Los mensajes mantienen el mismo formato JSON y la misma jerarquía de tópicos de la Unidad 1. Se agregan dos tópicos nuevos:

* `smarthome/equipoXX/llm/decision`
* `smarthome/equipoXX/llm/respuesta`

*Ejemplo de generación del certificado autofirmado:*

```bash
openssl req -new -x509 -days 365 -extensions v3_ca -keyout ca.key -out ca.crt

```

### 4.2 CoAP en al menos un nodo sensor

* Configurar un ESP32 para publicar datos de temperatura o humedad usando el protocolo CoAP (puerto UDP 5683) mediante la librería `CoAP-simple-library`.
* En Node-RED, recibir los recursos CoAP con el nodo `node-red-contrib-coap` y redirigir los datos al broker MQTT.
* Registrar en el informe una comparación del tamaño de los mensajes y el consumo de ancho de banda entre MQTT y CoAP para el mismo dato.

> **Nota técnica:** CoAP usa UDP en lugar de TCP, lo que lo hace más liviano pero menos confiable. Es ideal para sensores con baterías o redes con ancho de banda limitado (NB-IoT, LoRa backhaul).

### 4.3 Integración del LLM local como controlador inteligente

Esta es la funcionalidad central de la Unidad 2. El LLM reemplaza las reglas if/else de Node-RED por razonamiento contextual en lenguaje natural.

* **Herramienta recomendada:** Ollama (permite descargar y ejecutar modelos de lenguaje de forma local con una sola línea de comandos).
* **Modelos recomendados:** `phi3:mini` (2.3 GB, muy rápido en CPU) o `llama3.2:3b` (2 GB).

*Comandos de instalación e inicio:*

```bash
# Instalacion en Linux / macOS
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelo liviano
ollama pull phi3:mini

# Iniciar servidor (API en http://localhost:11434)
ollama serve

```

#### Arquitectura de integración

```
[Sensores ESP32] --> [MQTT broker] --> [Node-RED] --(Construye prompt / POST /api/generate)--> [Ollama local]
                                          ^                                                     |
                                          |-----------------(Respuesta JSON)--------------------|
                                          |
                                          v
                               [Node-RED publica MQTT]
                            (led, buzzer, alerta, respuesta)

```

#### Funcionamiento paso a paso

1. Node-RED recibe los datos de los sensores cada 30 segundos o ante un evento.
2. Se construye un prompt de contexto con el estado actual del hogar. *Ejemplo:*
```
Eres el sistema de control de una casa inteligente.
Estado actual del hogar:
Temperatura: 32 grados C (umbral normal: 28)
Humedad: 65%
Gas: 450 ppm (umbral de alerta: 400 ppm)
Movimiento detectado: si
Hora local: 02:15
Persona detectada por camara: no

Analiza el estado y responde SOLO en formato JSON valido con exactamente esta estructura:
{
  "nivel_alerta": "normal / medio / critico",
  "activar_led": true / false,
  "activar_buzzer": true / false,
  "mensaje_alerta": "texto corto para la notificacion",
  "razonamiento": "explicacion breve de la decision"
}

```


3. Node-RED envía el prompt a la API de Ollama con un nodo HTTP Request:
* **POST** `http://localhost:11434/api/generate`
* **Payload:**
```json
{
  "model": "phi3:mini",
  "prompt": "<contexto generado dinamicamente>",
  "stream": false,
  "format": "json"
}

```




4. Node-RED parsea la respuesta y publica los comandos MQTT correspondientes:
* `smarthome/equipoXX/control/led` -> `{"estado": true}`
* `smarthome/equipoXX/control/buzzer` -> `{"estado": true}`
* `smarthome/equipoXX/llm/decision` -> `{"nivel": "critico", "razonamiento": "..."}`



> **Consejo de implementación:** Usar `"format": "json"` en la petición a Ollama obliga al modelo a responder en JSON válido, lo que simplifica el parseo en Node-RED. Si el modelo no responde en JSON, revise que el prompt sea lo suficientemente explícito.

### 4.4 Interfaz de consulta en lenguaje natural

Agregar al dashboard de Node-RED un campo de texto donde el usuario pueda escribir preguntas en español sobre el estado del hogar. El sistema debe:

* Tomar la pregunta del usuario desde el dashboard.
* Inyectar automáticamente los datos actuales de los sensores como contexto.
* Enviar el prompt resultante al LLM local.
* Mostrar la respuesta en texto en el dashboard.

*Ejemplos de preguntas requeridas:*

* "¿Es seguro dormir con estos niveles de gas?"
* "Resume el estado del hogar en una frase."
* "¿Qué condición del hogar es más preocupante ahora mismo?"

### 4.5 Seguridad en redes IoT

Documentar en el informe técnico las siguientes medidas implementadas:

* Autenticación MQTT (usuario y contraseña) con `mosquitto_passwd`.
* Cifrado TLS en el transporte MQTT (puerto 8883).
* ACLs de Mosquitto que limiten qué clientes pueden publicar y suscribirse a qué tópicos.
* Análisis de al menos una vulnerabilidad conocida en el stack IoT del sistema (ej: MQTT sin autenticación, firmware sin actualización segura, broker expuesto en red pública) con su propuesta de mitigación.

---

## 5. Entregables - Unidad 2

* **a) Prototipo funcional:** Sistema completo en funcionamiento con MQTT seguro, CoAP operativo y LLM respondiendo consultas, demostrable en la sala durante la defensa.
* **b) Código fuente:**
* Firmware ESP32 actualizado con soporte TLS.
* Firmware ESP32 con cliente CoAP.
* Flujo de Node-RED actualizado exportado en formato `.json`.
* Archivo de configuración de Mosquitto (`mosquitto.conf`) y ACLs.
* Todo disponible en el repositorio en la carpeta `unidad2/`.


* **c) Informe técnico (5-8 páginas adicionales):**
1. Configuración de MQTT seguro (TLS + auth + ACLs).
2. Comparativa MQTT vs. CoAP: tamaño de mensaje, latencia, consumo de ancho de banda.
3. Arquitectura de integración del LLM: diagrama, prompt y respuestas.
4. Análisis de seguridad: vulnerabilidad y mitigación.
5. Capturas del dashboard con la interfaz de lenguaje natural.
6. Problemas encontrados en la integración del LLM y resoluciones.
7. Reflexión crítica: utilidad del LLM vs. reglas clásicas.


* **d) Defensa oral (15 minutos):**
* 8 minutos: demostración en vivo (incluye consulta al LLM).
* 7 minutos: preguntas técnicas sobre protocolos y seguridad.



---

## 6. Rúbrica de Evaluación - Unidad 2

| Criterio | Pond. | Logrado (4) | Parcial (2-3) | No logrado (1) |
| --- | --- | --- | --- | --- |
| **MQTT seguro (TLS + auth)** | 20% | Broker activo en puerto 8883 con TLS y autenticación, ESP32 y Node-RED conectados correctamente. | Broker configurado con TLS o autenticación sin TLS. | MQTT sin seguridad, igual que Unidad 1. |
| **ACLs y análisis de seguridad** | 10% | ACLs definidas por cliente, vulnerabilidad analizada con mitigación documentada. | ACLs presentes pero sin análisis de vulnerabilidad. | Sin ACLs ni análisis. |
| **CoAP implementado** | 15% | Sensor publica en CoAP, datos llegan a Node-RED, comparativa documentada en informe. | CoAP configurado pero sin integración completa en Node-RED. | No implementado. |
| **LLM local (Ollama)** | 25% | LLM responde en JSON válido y los comandos MQTT se publican correctamente ante eventos reales. | LLM responde pero los comandos MQTT no se publican o son incorrectos. | LLM no integrado en el flujo. |
| **Consulta en lenguaje natural** | 15% | Campo de texto en el dashboard funcional, respuestas coherentes con el estado actual. | Interfaz presente pero respuestas fuera de contexto o inconsistentes. | Sin interfaz de lenguaje natural. |
| **Informe técnico** | 10% | Secciones nuevas completas, con diagrama de integración LLM y capturas. | Faltan secciones o capturas relevantes. | Informe no actualizado. |
| **Defensa oral** | 5% | Todos participan, demuestran comprensión del LLM y de los protocolos. | Participación desigual o explicaciones superficiales. | Sin defensa o sin dominio técnico. |

### Conversión de Puntaje a Nota (Unidad 2)

La nota se calcula mediante la fórmula:


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
