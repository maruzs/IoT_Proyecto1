# 📋 Parte 1: Checklist Unidad 2 – Protocolos, Seguridad y LLM Local

Esta fase se centra en asegurar las comunicaciones del SmartHome mediante cifrado, incorporar lecturas ligeras con CoAP e integrar un Modelo de Lenguaje Local que reemplace las decisiones estáticas.

## 1. Infraestructura y Seguridad MQTT

* [ ] **Cifrado TLS en Broker:** Configurar Mosquitto de forma segura en el puerto 8883.


* [ ] **Desactivación Insegura:** Deshabilitar por completo el listener en texto plano del puerto 1883.


* [ ] **Autenticación Fuerte:** Crear un archivo de usuarios y contraseñas mediante la herramienta `mosquitto_passwd`.


* [ ] **Generación de Certificados:** Crear un certificado TLS autofirmado válido (`ca.crt` y `ca.key`) con una validez de 365 días.


* [ ] **Políticas de Acceso (ACLs):** Definir reglas de control de acceso por cliente de modo que cada dispositivo disponga de los permisos mínimos indispensables (ej: los sensores solo publican datos y el gateway LLM no controla actuadores directamente).


* [ ] **Tópicos del LLM:** Habilitar el aislamiento para los nuevos tópicos `smarthome/equipoXX/llm/decision` y `smarthome/equipoXX/llm/respuesta`.



## 2. Actualización de Firmware (Nodos IoT)

* [ ] **Firmware ESP32 con TLS:** Modificar el código de los nodos para implementar conexiones mediante librerías seguras (`WiFiClientSecure` o `WiFiSSLClient`).


* [ ] **Inyección de Certificado:** Embeber de forma correcta el certificado CA en el código del firmware.


* [ ] **Externalización de Credenciales:** Asegurar que las contraseñas y datos sensibles de red no se suban explícitamente al repositorio público.


* [ ] **Lógica de Reconexión:** Programar rutinas automáticas de reintento de conexión TLS ante caídas o cortes del enlace WiFi.


* [ ] **Firmware de Cliente CoAP:** Desarrollar o adecuar un firmware que publique métricas de sensores usando el protocolo CoAP sobre UDP en el puerto 5683 mediante `CoAP-simple-library`.



## 3. Cerebro LLM e Integración Local

* [ ] **Instalación de Ollama:** Servir Ollama localmente en la máquina host exponiendo la API en `localhost:11434`.


* [ ] **Descarga del Modelo:** Disponer del modelo liviano seleccionado (`phi3:mini` o `llama3.2:3b`) listo para inferencia sin internet.


* [ ] **Desarrollo del Microservicio LLM Gateway:** Programar el gateway en Python (FastAPI) para centralizar y empaquetar las peticiones hacia Ollama.


* [ ] **Estructuración de Prompts Dinámicos:** Diseñar la lógica que inyecta en tiempo real las variables de temperatura, humedad, gas, movimiento y hora en el contexto del prompt.


* [ ] **Forzado de Formato JSON:** Configurar el parámetro `"format": "json"` en la petición HTTP para obligar al LLM a retornar una estructura parseable exacta.


* [ ] **Manejo de Errores y Timeouts:** Programar reintentos con prompts reforzados si el JSON falla, junto con un timeout estricto de 30 segundos en CPU para evitar bloqueos.


* [ ] **Construcción de Servidor MCP:** Implementar el protocolo *Model Context Protocol* (MCP) en Node-RED para declarar herramientas reutilizables (`get_sensor_state`, `activate_actuator`, etc.).


* [ ] **Lógica de Agente Local (LangGraph):** Integrar el agente para procesar estados y tomar decisiones utilizando de forma segura las herramientas MCP expuestas.



## 4. Interfaz y Orquestación (Node-RED)

* [ ] **Actualización de Nodos MQTT:** Modificar la configuración de Node-RED para migrar al broker con TLS y credenciales de entorno.


* [ ] **Mapeo de CoAP Bridge:** Implementar la pasarela de traducción (nodo CoAP o microservicio dedicado) que redirija la telemetría UDP hacia tópicos del broker MQTT seguro.


* [ ] **Módulo de Consultas NL:** Incorporar un campo de texto en el Dashboard que capture preguntas en lenguaje natural y renderice la respuesta final formateada.


* [ ] **Rol de Gatekeeper:** Verificar que el flujo de Node-RED sea la única entidad que publique directamente en los tópicos físicos de control (`control/led`, `control/buzzer`) basándose en las decisiones del LLM.



## 5. Entregables y Documentación de Unidad 2

* [ ] **Repositorio Estructurado:** Alojar los códigos de firmware, configuraciones de Mosquitto, ACLs y los flujos exportados en la carpeta `unidad2/`.


* [ ] **Informe Técnico (Secciones 1 a 7):**
* [ ] Detalle de la configuración TLS, credenciales y políticas ACL.


* [ ] Tabla comparativa MQTT vs. CoAP (ancho de banda, tamaño de mensaje y latencia).


* [ ] Diagrama de bloques de la arquitectura del LLM, prompts base y capturas de respuestas.


* [ ] Análisis de una vulnerabilidad común de IoT con su respectivo plan de mitigación.


* [ ] Evidencia fotográfica o capturas del Dashboard en lenguaje natural operando.


* [ ] Bitácora de problemas detectados en el parseo o latencia del LLM y sus soluciones.


* [ ] Ensayo o reflexión crítica evaluando el uso de LLM frente al control determinista clásico (`if/else`).




* [ ] **Preparación de la Defensa:** Estructurar la presentación para cumplir con los 8 minutos de demo en vivo y los 7 minutos de examinación técnica.



---

