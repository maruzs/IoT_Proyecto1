# Documentación del Gemelo Digital y Grafana (SmartHome IoT)

Esta documentación describe la arquitectura, decisiones de diseño y detalles de implementación de las tareas **T-015 (Digital Twin)**, **T-020 (Grafana Dashboard)** y **T-021 (Grafana Alerts)**.

---

## 1. Justificación de Decisiones de Diseño

### A. Algoritmo de Predicción: Regresión Lineal (`numpy.polyfit`)
Se seleccionó la **Regresión Lineal Simple** (ajuste polinomial de grado 1) para las predicciones de 30 minutos por las siguientes razones:
* **Eficiencia de Recursos**: Se ejecuta en microsegundos en entornos locales de desarrollo y producción sin necesidad de recursos pesados (GPUs o contenedores pesados como TensorFlow/PyTorch).
* **Corto Plazo**: Las tendencias de temperatura, humedad y gas en un hogar muestran comportamiento lineal o semi-lineal en ventanas de tiempo cortas (menores a 1 hora).
* **Exclusión de Sonido**: La variable de sonido no se incluye en el modelo predictivo. Dado que el sonido es discreto, instantáneo y altamente estocástico (p. ej., un aplauso o un grito), no posee una tendencia continua predecible mediante modelos lineales simples.

### B. Arquitectura de Ingesta Desacoplada (Bridge MQTT a InfluxDB)
En lugar de forzar al servicio del Gemelo Digital a escribir directamente en la base de datos de telemetría (InfluxDB), se implementó un script de puente desacoplado `mqtt_to_influx.py`.
* **Beneficios**: Esto permite que el Gemelo Digital se mantenga enfocado en su tarea principal (mantener el estado en memoria y generar predicciones en base a datos agregados) y que la base de datos reciba los datos de manera asíncrona a través de la red MQTT (siguiendo el patrón arquitectónico del proyecto).

### C. Entorno de Desarrollo y Simulación Local
Para garantizar que cualquier miembro del equipo pueda probar y desplegar los servicios sin contar con el hardware físico (placas Arduino/ESP32) ni saturar su procesador ejecutando modelos masivos de IA en Ollama, se diseñaron dos facilitadores:
1. **`telemetry_feeder.py`**: Un emulador que publica telemetría y eventos de sensores simulados directo al broker MQTT local en los puertos correctos.
2. **`docker-compose-light.yml`**: Un stack dockerizado ultraligero que inicia únicamente Mosquitto, InfluxDB y Grafana, aislando el desarrollo de componentes del resto de la arquitectura.

---

## 2. El Dashboard del Gemelo Digital: ¿Qué es y qué representa?

El panel visual en Grafana tiene como objetivo **visualizar la convergencia entre el estado físico real y el estado simulado/proyectado (Gemelo Digital)**.

### Qué Representa y Muestra:
1. **Paneles de Series Temporales (Temperatura, Humedad, Gas)**:
   * **Valores Reales (Línea Continua)**: Muestra la telemetría histórica exacta recopilada del hogar inteligente a través de los sensores.
   * **Valores Proyectados (Línea Punteada - 30 minutos a futuro)**: Muestra la predicción calculada por el modelo de regresión lineal del Gemelo Digital. Esto permite comparar visualmente hacia dónde tiende el clima/seguridad del hogar en el corto plazo y anticiparse a incidentes.
2. **Línea de Tiempo del Estado de Actuadores**:
   * Muestra el histórico de activación y desactivación de componentes del hogar (LED, Buzzer, presencia de personas detectada por cámaras, movimiento).

---

## 3. Lógica del Gemelo Digital (T-015)

* **Consolidación en Memoria**: El Gemelo Digital mantiene las lecturas crudas en tiempo real y calcula un promedio minuto a minuto (`consolidate_minute_average`). Para testing local acelerado, esto se puede ajustar a intervalos de segundos mediante variables de entorno.
* **Persistencia del Estado**: El estado actual se persiste automáticamente en JSON en la ruta indicada por `SNAPSHOT_PATH` (por defecto `data/twin_snapshot.json` en local) para evitar la pérdida de historial en caso de reinicios del servicio.
* **Cálculo Matemático de Regresión**:
  1. Convierte las marcas de tiempo ISO a minutos transcurridos relativos al primer registro.
  2. Ajusta la recta $y = m \cdot x + c$ utilizando `np.polyfit`.
  3. Evalúa la recta para el punto $x_{\text{último}} + 30.0$ minutos.
  4. Aplica límites físicos para evitar valores imposibles (humedad negativa o mayor a 100%, etc.).

---

## 4. Alertas de Grafana (T-021)

Las alertas están autoprovisionadas en el stack mediante `deploy/grafana/provisioning/alerting/rules.yaml`:
* **Temperatura Alta**: Se activa si el promedio de los últimos 2 minutos supera los **28 °C**.
* **Gas Crítico**: Se activa si el promedio del último minuto supera los **400 ppm**.

**Flujo de las Alertas**:
1. InfluxDB almacena los datos reales.
2. Grafana evalúa periódicamente las consultas Flux contra la base de datos (Query A).
3. Evalúa la condición lógica utilizando el motor matemático integrado `__expr__` (Query B).
4. Cuando el umbral es superado por la duración definida (`for`), la alerta pasa a estado `Alerting` y se comunica mediante webhook/API para gatillar actuadores de emergencia (como el Buzzer o notificaciones).
