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