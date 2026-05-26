# Spec: Control Automático — Reglas en Node-RED

## Contexto

El sistema DEBE reaccionar autónomamente a condiciones del ambiente sin intervención humana. Las reglas de control se implementan en Node-RED, evaluando mensajes MQTT entrantes y activando actuadores o alertas según condiciones configurables.

## Requisitos Funcionales

### RF-1: Mínimo dos reglas de control automático

El sistema DEBE implementar al menos DOS reglas de control automático. Ejemplos requeridos:

**Regla 1: Alerta por temperatura alta**
```
SI temperatura > 30°C
ENTONCES:
  - Encender LED de alerta
  - Publicar alerta en smarthome/{equipoXX}/alerta
  - Enviar notificación externa (Telegram o Email)
```

**Regla 2: Alerta por gas alto**
```
SI gas > umbral_gas (ej: 400)
ENTONCES:
  - Activar buzzer
  - Solicitar captura de imagen a la ESP32-CAM
  - Publicar alerta en smarthome/{equipoXX}/alerta
  - Enviar notificación externa (Telegram o Email)
```

### RF-2: Regla adicional recomendada (tercera regla)

**Regla 3: Alerta por detección de persona**
```
SI persona_detectada == true
ENTONCES:
  - Activar buzzer por 3 segundos
  - Encender LED de alerta
  - Publicar alerta en smarthome/{equipoXX}/alerta
  - Enviar notificación con imagen capturada
```

### RF-3: Umbrales configurables

- Los umbrales DEBEN ser configurables en Node-RED (function nodes o context global)
- NO hardcodear valores en medio de la lógica
- Usar `global.get()` o `flow.get()` para almacenar umbrales

### RF-4: Prevención de alertas repetitivas

- Una alerta NO debe dispararse más de una vez por minuto para la misma condición
- Usar un flag de "alerta activa" que se resetea cuando la condición vuelve a la normalidad
- Implementar cooldown entre notificaciones externas (mínimo 60 segundos)

### RF-5: Registro de eventos de control

- Cada vez que se activa una regla, registrar:
  - Timestamp
  - Tipo de regla activada
  - Valor que disparó la regla
  - Umbral comparado
  - Acciones ejecutadas

## Requisitos No Funcionales

### RNF-1: Implementación en Node-RED

- Las reglas DEBEN implementarse como flujos de Node-RED
- Usar `switch` nodes o `function` nodes para evaluación de condiciones
- Cada regla DEBE ser un sub-flujo independiente para facilitar debugging

### RNF-2: Verificabilidad en demo

- Cada regla DEBE poder demostrarse en vivo durante la defensa
- Los umbrales DEBEN ser ajustables para facilitar la demo (ej: bajar umbral de gas temporalmente)

### RNF-3: No bloqueo

- Las reglas NO deben bloquear el flujo principal de sensores
- Las acciones de alerta deben ejecutarse en paralelo

## Escenarios de Aceptación

### Escenario 1: Temperatura alta activa alerta
```
DADO que el umbral de temperatura es 30°C
CUANDO la temperatura supera 30°C
ENTONCES el LED de alerta se enciende
Y se publica una alerta en MQTT
Y se envía una notificación externa
```

### Escenario 2: Gas alto activa múltiples acciones
```
DADO que el umbral de gas es 400
CUANDO el sensor de gas lee un valor > 400
ENTONCES el buzzer se activa
Y se solicita una captura de imagen
Y se publica una alerta en MQTT
```

### Escenario 3: No alertas repetitivas
```
DADO que la temperatura está por encima de 30°C
Y ya se envió una alerta hace 30 segundos
CUANDO llega una nueva lectura de temperatura alta
ENTONCES NO se envía otra notificación externa
PERO el LED de alerta permanece encendido
```

### Escenario 4: Reset de alerta
```
DADO que hay una alerta activa por temperatura
CUANDO la temperatura baja por debajo de 30°C
ENTONCES el LED de alerta se apaga
Y el estado de alerta se resetea
```

### Escenario 5: Demostración en vivo
```
DADO que el sistema está en modo demo
CUANDO se acerca una fuente de calor al sensor de temperatura
ENTONCES la regla de temperatura se activa en menos de 5 segundos
Y las acciones correspondientes se ejecutan
```

## Criterios de Éxito

1. [ ] Al menos 2 reglas de control automático implementadas
2. [ ] Cada regla es verificable en demo
3. [ ] Los umbrales son configurables sin modificar código
4. [ ] No hay alertas repetitivas (cooldown implementado)
5. [ ] Las alertas se resetean cuando la condición normaliza
6. [ ] Los eventos de control se registran con timestamp
