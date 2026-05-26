# Spec: Dashboard Node-RED — Visualización en Tiempo Real

## Contexto

El dashboard de Node-RED es la interfaz principal del sistema. Muestra en tiempo real el estado de todos los sensores, actuadores, cámara y alertas. Debe ser usable durante la demo en vivo.

## Requisitos Funcionales

### RF-1: Valores en tiempo real de variables físicas

El dashboard DEBE mostrar los valores actuales de:
- **Temperatura** (°C) — indicador numérico con unidad
- **Humedad** (%) — indicador numérico con unidad
- **Gas** (valor analógico o ppm) — indicador numérico
- **Sensor extra / Sonido** (nivel dB o valor analógico) — indicador numérico

Cada valor DEBE actualizarse automáticamente al recibir mensajes MQTT.

### RF-2: Estado de movimiento y detección de persona

- **Movimiento**: indicador visual sí/no (ej: LED verde/rojo o icono)
- **Detección de persona**: indicador visual sí/no con última confianza detectada
- Ambos indicadores DEBE cambiar en tiempo real al recibir eventos MQTT

### RF-3: Estado de alerta e indicador visual general

- **Estado de alerta**: indicador que muestra si hay alguna alerta activa
- **Estado general del sistema**: indicador visual (ej: semáforo verde/amarillo/rojo)
  - 🟢 Verde: todo normal
  - 🟡 Amarillo: advertencia (umbral cercano)
  - 🔴 Rojo: alerta activa

### RF-4: Imagen de la cámara

- El dashboard DEBE mostrar la imagen actual de la ESP32-CAM
- La imagen DEBE actualizarse periódicamente (stream o snapshots)
- DEBE incluir un indicador de estado de la cámara (conectada/desconectada)

### RF-5: Botón de captura manual

- Botón que solicita un snapshot a la ESP32-CAM
- Al presionarlo, la imagen capturada se muestra en el dashboard
- El botón DEBE tener feedback visual (ej: "capturando..." → "listo")

### RF-6: Controles manuales de actuadores

- **Botón LED**: toggle ON/OFF para el LED de alerta
- **Botón Buzzer**: toggle ON/OFF para el buzzer
- Ambos botones DEBEN publicar en los tópicos de control MQTT correspondientes
- El estado actual DEBE reflejarse visualmente en el botón

### RF-7: Gráfico histórico

- Gráfico de línea con histórico de al menos una variable (temperatura o gas)
- El gráfico DEBE mostrar los últimos N minutos de datos (configurable)
- Actualización automática al recibir nuevos datos

## Requisitos No Funcionales

### RNF-1: node-red-dashboard

- Usar `node-red-dashboard` (dashboard 2.0 o classic)
- Layout responsive para visualización en pantalla de demo
- Agrupar widgets en secciones lógicas (sensores, cámara, controles, histórico)

### RNF-2: Actualización en tiempo real

- Los valores DEBEN actualizarse sin recargar la página
- Latencia máxima de actualización: 2 segundos desde recepción MQTT

### RNF-3: Organización visual

```
┌─────────────────────────────────────────────┐
│  SMARTHOME - Equipo XX                      │
├─────────────┬───────────────┬───────────────┤
│ SENSORES    │ CÁMARA        │ CONTROLES     │
│ Temp: 25°C  │ [Imagen]      │ LED: [ON/OFF] │
│ Hum: 60%    │ [Capturar]    │ Buzzer: [ON]  │
│ Gas: 320    │ Persona: NO   │               │
│ Sonido: 45  │ Movimiento:NO │               │
├─────────────┴───────────────┴───────────────┤
│ ESTADO: 🟢 NORMAL    |    ALERTA: Ninguna   │
├─────────────────────────────────────────────┤
│ GRÁFICO HISTÓRICO: Temperatura (últimos 10m)│
│ [━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━]  │
└─────────────────────────────────────────────┘
```

## Escenarios de Aceptación

### Escenario 1: Dashboard muestra valores actualizados
```
DADO que el dashboard está abierto en el navegador
CUANDO el MKR1000 publica una nueva lectura de temperatura
ENTONCES el valor de temperatura se actualiza en menos de 2 segundos
```

### Escenario 2: Indicador de persona cambia
```
DADO que no hay personas frente a la cámara
CUANDO el sistema de visión detecta una persona
ENTONCES el indicador de persona cambia a "SÍ" en el dashboard
Y muestra la confianza de detección
```

### Escenario 3: Control manual de LED
```
DADO que el LED está apagado
CUANDO se presiona el botón LED en el dashboard
ENTONCES el LED se enciende
Y el botón muestra estado "ON"
```

### Escenario 4: Estado general cambia a alerta
```
DADO que el sistema está en estado normal (verde)
CUANDO se detecta gas por encima del umbral
ENTONCES el estado general cambia a rojo
Y se muestra el tipo de alerta activa
```

### Escenario 5: Gráfico histórico muestra datos
```
DADO que el sistema ha estado corriendo por 5 minutos
CUANDO se abre el dashboard
ENTONCES el gráfico histórico muestra datos de los últimos 5 minutos
```

## Criterios de Éxito

1. [ ] Dashboard accesible vía navegador en puerto de Node-RED
2. [ ] Las 4 variables físicas se muestran con valores actualizados
3. [ ] Indicadores de movimiento y persona funcionan en tiempo real
4. [ ] Estado general del sistema visible (semáforo)
5. [ ] Imagen de cámara visible y actualizada
6. [ ] Botón de captura manual funciona
7. [ ] Controles manuales de LED y buzzer funcionan
8. [ ] Gráfico histórico muestra datos de al menos una variable
9. [ ] Layout organizado en secciones lógicas
