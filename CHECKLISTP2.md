# Parte 2: Checklist Unidad 3 – Gemelo Digital y Agente Autónomo

Esta fase final traslada el sistema a un plano industrial-productivo, implementando contención completa de servicios, representaciones virtuales persistentes, analítica predictiva y un agente proactivo con herramientas encadenadas.

## 1. Infraestructura Containerizada (Docker)

* [ ] **Orquestación Unificada:** Diseñar un archivo `docker-compose.yml` que levante la totalidad del stack mediante un único comando `docker compose up -d`.


* [ ] **Aislamiento de Redes y Volúmenes:** Declarar redes lógicas internas y volúmenes de almacenamiento persistentes para evitar la pérdida de datos al reiniciar contenedores.


* [ ] **Configuración de Servicios Base:** Incluir de manera correcta las imágenes y puertos de Mosquitto (8883), InfluxDB (8086), Grafana (3000) y Node-RED (1880).


* [ ] **Enlace con el Host:** Habilitar el puenteo de red (`host.docker.internal` o IP dedicada) para que las aplicaciones en Docker apunten a la API de Ollama en el host.


* [ ] **Monitoreo de Salud:** Definir pruebas de estado (*healthchecks*) y orden de inicio (`depends_on`) entre la base de datos, el broker y los visualizadores.



## 2. Ingesta de Datos e InfluxDB 2.7

* [ ] **Inicialización Automatizada:** Configurar las variables de entorno de arranque para la organización (`smarthome`) y el bucket inicial (`sensores`).


* [ ] **Pipeline de Ingesta:** Establecer un recolector continuo (Telegraf o microservicio dedicado) conectado al broker MQTT con TLS que inserte métricas de forma directa.


* [ ] **Estrategias de Almacenamiento:** Configurar una política de retención explícita (ej: depuración de históricos tras 7 días o almacenamiento diferenciado para agregaciones masivas).



## 3. Arquitectura de Gemelo Digital (Digital Twin)

* [ ] **Modelo de Estado JSON:** Implementar un objeto JSON persistente que consolide en tiempo real las variables de entorno, estados de actuadores y alarmas activas.


* [ ] **Historial Local en Memoria:** Mantener un arreglo interno con las últimas 60 lecturas de cada sensor (equivalente a 1 hora de historial a resolución de 1 minuto).


* [ ] **Exposición por API REST:** Desarrollar y levantar el endpoint funcional `GET /gemelo/estado` (en Node-RED o mediante un microservicio FastAPI).


* [ ] **Sincronización del Contexto LLM:** Añadir el parámetro dinámico `resumen_llm` dentro del estado del gemelo para que el agente actualice el diagnóstico global del hogar.


* [ ] **Persistencia y Tolerancia a Fallos:** Programar guardados en disco periódicos de la estructura JSON para recuperar el estado anterior ante reinicios abruptos del contenedor.



## 4. Motor de Predicción Analítica

* [ ] **Script Predictivo Independiente:** Crear un script ejecutable en Python programado para procesarse de manera automática en intervalos de 10 minutos.


* [ ] **Extracción de Serie de Tiempo:** Diseñar la consulta en lenguaje Flux hacia InfluxDB para extraer de forma limpia las últimas 6 horas de registros de temperatura y gas.


* [ ] **Cálculo de Proyección:** Aplicar un algoritmo de ajuste matemático (`numpy.polyfit` de grado 1 o la librería Prophet) para estimar los valores con un horizonte a 30 minutos.


* [ ] **Publicación de Estimaciones:** Emitir los resultados calculados hacia los tópicos MQTT de predicción de temperatura y gas.


* [ ] **Alertas Preventivas:** Programar al motor para que publique un JSON con el campo `"tipo": "preventiva"` en caso de que la curva matemática estime una violación de umbrales antes de los 30 minutos.



## 5. Agente Autónomo y Encadenamiento de Acciones

* [ ] **Automatización de Ciclos:** Configurar un planificador (scheduler interno en el gateway o webhook de contingencia) que active al agente cada 5 minutos de forma estricta.


* [ ] **Lectura del Gemelo Virtual:** Garantizar que el agente consuma el estado, el historial de 1 hora y las proyecciones directamente desde la API del Gemelo Digital antes de razonar.


* [ ] **Inyección de Herramientas:** Proveer al modelo las definiciones explícitas para ejecutar acciones autónomas en bloque (`activar_actuador`, `enviar_notificacion`, `registrar_evento`, `ajustar_umbral`).


* [ ] **Ejecución en Cascada:** Validar que el agente logre interpretar la respuesta compleja y disparar múltiples llamadas consecutivas sin requerir intervención manual (ej: prender extractor, sonar alarma y alertar por canales externos ante gas alto).


* [ ] **Pasarela de Alertas Unificada:** Integrar un gestor de alertas (*Alert Manager*) independiente encargado de despachar notificaciones (ej: Telegram API) aplicando políticas de enfriamiento (*cooldown*) de 5 minutos para mitigar el spam.



## 6. Monitoreo Avanzado en Grafana

* [ ] **Conexión de Fuentes:** Vincular correctamente Grafana con la base de datos InfluxDB mediante tokens autorizados.


* [ ] **Panel de Tendencias:** Construir gráficos de series temporales de las últimas 6 horas para los parámetros de temperatura, humedad y gas.


* [ ] **Panel Predictivo Superpuesto:** Diseñar una vista combinada que muestre los datos reales (línea continua) cruzados con los datos proyectados a 30 minutos (línea discontinua).


* [ ] **Auditoría del Agente:** Incorporar una tabla histórica que liste el log de decisiones tomadas por el LLM, mostrando marca de tiempo, razonamiento lógico y acciones invocadas.


* [ ] **Estado de la Réplica:** Desplegar una tabla resumen con el valor de las variables activas del Gemelo Digital.


* [ ] **Reglas de Alerta Internas:** Configurar al menos una regla nativa dentro de Grafana que accione un canal de notificación ante la persistencia de umbrales críticos.



## 7. Entregables y Documentación Final Consolidada

* [ ] **Repositorio Finalizado:** Alojar el manifiesto `docker-compose.yml`, los scripts de predicción en Python, flujos en formato JSON y esquemas de dashboards dentro de la carpeta `unidad3/`.


* [ ] **Informe Técnico Integrador (20-30 páginas totales):**
* [ ] Consolidación formal de los capítulos elaborados para las Unidades 1 y 2.


* [ ] Diagramas de arquitectura del stack Docker Compose detallando mapeo de puertos y aislamiento de redes.


* [ ] Plan de diseño, flujos y estructura de datos del Gemelo Digital.


* [ ] Explicación del modelo analítico predictivo y gráficos comparativos de errores vs. datos reales.


* [ ] Estructura detallada del prompt del agente autónomo, herramientas mapeadas y registros de auditoría de pruebas exitosas.


* [ ] Respuestas detalladas y diagramas de arquitectura para el caso de estudio industrial seleccionado (ej: monitoreo de sala de servidores o automatización agrícola).


* [ ] Análisis crítico profundo enfocado en las limitantes del LLM en entornos de producción (latencia, comportamiento no determinista y excepciones en el parseo de estructuras JSON) frente al control tradicional por código.


* [ ] Conclusiones técnico-operacionales finales del proyecto de ingeniería.




* [ ] **Preparación de Examen de Título / Defensa Final:** Ensayar la presentación técnica del equipo respetando estrictamente los 10 minutos de demostración del agente operativo en vivo y los 10 minutos de defensa frente a la comisión evaluadora.