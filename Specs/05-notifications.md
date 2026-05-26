# Spec: Notificaciones Externas — Telegram y/o Email

## Contexto

El sistema DEBE enviar notificaciones externas cuando ocurren eventos críticos (alertas de sensores, detección de personas). Se puede usar Telegram o Email como canal de notificación.

## Requisitos Funcionales

### RF-1: Canal de notificación

El sistema DEBE implementar al menos UNO de los siguientes canales:

**Opción A: Telegram** (recomendado)
- Usar `node-red-contrib-telegrambot`
- Configurar bot token y chat ID
- Enviar mensajes de texto con detalles del evento

**Opción B: Email**
- Usar `node-red-node-email`
- Configurar servidor SMTP, usuario y contraseña
- Enviar emails con asunto y cuerpo descriptivo

### RF-2: Formato de notificación

Cada notificación DEBE incluir:
- **Tipo de evento**: temperatura_alta, gas_alto, persona_detectada, etc.
- **Valor medido**: el valor que disparó la alerta
- **Umbral**: el umbral que se superó
- **Timestamp**: fecha y hora del evento
- **Equipo**: identificador del equipo (equipoXX)

**Ejemplo Telegram**:
```
🚨 ALERTA SmartHome - equipo01
📋 Tipo: Gas alto
📊 Valor: 520 ppm
⚠️ Umbral: 400 ppm
🕐 2026-05-26 10:30:00
```

**Ejemplo Email**:
```
Asunto: 🚨 ALERTA SmartHome - Gas alto - equipo01

Cuerpo:
Tipo de evento: Gas alto
Valor medido: 520 ppm
Umbral superado: 400 ppm
Timestamp: 2026-05-26 10:30:00
Equipo: equipo01
```

### RF-3: Eventos que generan notificación

Las notificaciones DEBEN enviarse para:
- Temperatura por encima del umbral
- Gas por encima del umbral
- Persona detectada por la cámara
- Cualquier alerta publicada en `smarthome/{equipoXX}/alerta`

### RF-4: Cooldown entre notificaciones

- NO enviar más de una notificación del mismo tipo en menos de 60 segundos
- Implementar un mecanismo de debounce o flag de "notificación enviada"
- El cooldown DEBE ser configurable

### RF-5: Notificación con imagen (para detección de persona)

- Cuando se detecta una persona, la notificación DEBE incluir la imagen capturada
- En Telegram: enviar la imagen como foto adjunta
- En Email: enviar la imagen como attachment

## Requisitos No Funcionales

### RNF-1: Credenciales seguras

- Los tokens de Telegram o credenciales SMTP NO deben estar hardcodeados en el flujo
- Usar variables de entorno o credenciales de Node-RED
- NO commitear credenciales en el repositorio

### RNF-2: Resiliencia

- Si el servicio de notificación no está disponible, el sistema NO debe bloquearse
- Registrar errores de envío en el debug de Node-RED
- Reintentar una vez antes de descartar

### RNF-3: Configuración

- El canal de notificación DEBE ser activable/desactivable desde Node-RED
- Permitir cambiar entre Telegram y Email sin modificar la lógica de reglas

## Escenarios de Aceptación

### Escenario 1: Notificación por temperatura alta
```
DADO que Telegram está configurado correctamente
CUANDO la temperatura supera 30°C
ENTONCES se envía un mensaje de Telegram con el formato especificado
Y el mensaje incluye tipo, valor, umbral y timestamp
```

### Escenario 2: Notificación con imagen
```
DADO que se detectó una persona
CUANDO se envía la notificación
ENTONCES el mensaje de Telegram incluye la imagen capturada
Y el texto describe el evento de detección
```

### Escenario 3: Cooldown funciona
```
DADO que se envió una notificación de gas alto hace 30 segundos
CUANDO se detecta gas alto nuevamente
ENTONCES NO se envía otra notificación
Y el evento se registra en debug
```

### Escenario 4: Servicio no disponible
```
DADO que el servidor SMTP no responde
CUANDO se intenta enviar una notificación por email
ENTONCES el sistema NO se bloquea
Y el error se registra en debug
Y las demás funcionalidades siguen operando
```

## Criterios de Éxito

1. [ ] Al menos un canal de notificación configurado y funcionando
2. [ ] Las notificaciones incluyen toda la información requerida
3. [ ] El cooldown evita notificaciones repetitivas
4. [ ] Las credenciales no están hardcodeadas
5. [ ] El sistema no se bloquea si el servicio de notificación falla
6. [ ] Las notificaciones con imagen funcionan para detección de persona
