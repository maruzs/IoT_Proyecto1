# Integración del Bot de Telegram en Node-RED

Hemos implementado la lógica de Telegram en el flujo de Node-RED. Esto permite que el sistema envíe **alertas automáticas** cuando las variables físicas superen los límites (ej. temperatura > 30°C o gas > 1020 ppm) y responda a **comandos interactivos** desde el celular.

---

## 1. Comandos del Bot en Telegram

Puedes hablarle directamente al bot desde tu cuenta de Telegram usando estos comandos:
* `/status`: Devuelve el reporte en tiempo real de los sensores (temperatura, humedad, gas, sonido y fecha).
* `/ayuda`: Muestra la ayuda del bot.

---

## 2. Cómo agregar el Bot a un Grupo de Telegram

Si quieres que las alertas y comandos funcionen en un grupo compartido con todos los integrantes del proyecto, sigue estos pasos:

1. **Añade el bot al grupo:** Abre tu grupo de Telegram, ve a "Añadir miembros" y busca el usuario de tu bot (ej. `@tu_usuario_bot`).
2. **Obtener el Chat ID del Grupo:**
   - Escribe un mensaje cualquiera en el grupo (ej. `/ayuda`).
   - Abre tu navegador web en la laptop y visita el siguiente enlace (reemplazando con tu API Token):
     `https://api.telegram.org/bot8845478827:AAF-VIRWIy5rhSP1f8kcBNmZYypsXF47x6s/getUpdates`
   - Busca en la respuesta de JSON una sección parecida a esta:
     `"chat":{"id":-100XXXXXXXXXX,"title":"NombreGrupo","type":"group"}`
   - El **ID del grupo** es un número negativo que suele empezar por `-100`. Cópialo completo (incluyendo el signo menos `-`).
3. **Actualizar el Chat ID en Node-RED:**
   - En el archivo `nodered/flows.json`, busca la regla de evaluación automática (`Reglas de Control Automático`).
   - Cambia el valor de `chatId` (línea ~478) que actualmente es `1511171371` por el número negativo de tu grupo.
   - Sincroniza los cambios con `./nodered/sync.sh`.

---

## 3. Guía para Compañeros (Cambiar de Bot)

Si otro integrante del grupo quiere usar su propio bot personal para las pruebas en su casa:

1. Debe obtener su propio API Token y Chat ID con `@BotFather` y `@userinfobot`.
2. En el editor de Node-RED (`http://localhost:1880/`):
   - Hacer doble clic en el nodo **Comandos Telegram** o **Enviar a Telegram**.
   - Editar la configuración del Bot (icono del lápiz ✏️) y cambiar el **Token** (`botkey`) por el suyo.
   - En el nodo de función **Reglas de Control Automático**, actualizar la variable `chatId` con su propio ID numérico.
3. Desplegar los cambios y presionar el botón "Deploy".
