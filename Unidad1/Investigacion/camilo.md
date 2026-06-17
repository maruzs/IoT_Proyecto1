¡Excelente elección! El **ESP32-CAM** es uno de los módulos más versátiles y económicos para proyectos de visión artificial e Internet de las Cosas (IoT). Al tener el shield con micro USB (usualmente llamado **ESP32-CAM-MB**), te has ahorrado el dolor de cabeza de usar un convertidor FTDI externo.

Aquí tienes la guía completa para dominarlo:

---

## 1. Información del componente

El ESP32-CAM combina un microcontrolador potente con conectividad inalámbrica y capacidad de procesamiento de imágenes.

* **Procesador:** ESP32-S (Dual-core de 32 bits, hasta 240 MHz).
* **Memoria:** 520 KB SRAM interna + **4 MB de PSRAM** externa (crucial para procesar fotos de alta resolución).
* **Cámara:** Sensor **OV2640** (incluido por defecto), soporta hasta 2 MP.
* **Almacenamiento:** Ranura para tarjeta MicroSD.
* **Flash:** LED integrado de alta potencia para fotos nocturnas.
* **Shield (MB):** Facilita la programación vía USB y añade un botón de **Reset** y uno de **Boot**.

---

## 2. Cómo se ocupa (Conexión)

Gracias a tu shield micro USB, la conexión es directa:

1. Encaja el módulo ESP32-CAM sobre el shield (asegúrate de que la cámara apunte hacia afuera).
2. Conecta el cable micro USB a tu computadora.
3. **Importante:** La antena de Wi-Fi integrada es pequeña; asegúrate de estar cerca del router para las primeras pruebas.

---

## 3. Cómo se programa

El ESP32-CAM se programa principalmente mediante el **IDE de Arduino**. Sigue estos pasos:

### Configuración del IDE:

1. Ve a **Archivo > Preferencias**.
2. En "Gestor de URLs Adicionales de Tarjetas", pega: `[https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json](https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json)`
3. Ve a **Herramientas > Placa > Gestor de tarjetas**, busca "ESP32" e instálalo.
4. Selecciona la placa: **AI Thinker ESP32-CAM**.

### Proceso de carga:

Con el shield USB, ya no necesitas puentes manuales. Solo asegúrate de seleccionar el puerto COM correcto en el IDE y presiona "Subir".

---

## 4. Librerías asociadas

A diferencia de otros sensores, la cámara no usa una librería simple de "instalar desde el gestor". Se apoya en el **ESP32 Camera Driver** que ya viene incluido cuando instalas el soporte para placas ESP32 en Arduino.

Las cabeceras principales que verás en los códigos son:

* `esp_camera.h`: El motor principal para capturar frames.
* `WiFi.h`: Para transmitir la imagen por red.
* `esp_http_server.h`: Para crear el servidor web donde verás el video.

---

## 5. Ejemplo "Hola Mundo": CameraWebServer

El mejor "Hola Mundo" para este dispositivo es el ejemplo oficial que crea un servidor de streaming de video.

### Pasos para ejecutarlo:

1. En el IDE de Arduino, ve a **Archivo > Ejemplos > ESP32 > Camera > CameraWebServer**.
2. Se abrirán varias pestañas. En la pestaña principal, busca estas líneas y edítalas:
* **Selecciona el modelo:** Descomenta `#define CAMERA_MODEL_AI_THINKER` y comenta las demás.
* **Credenciales:** Pon el nombre y contraseña de tu Wi-Fi:
```cpp
const char* ssid = "TU_WIFI";
const char* password = "TU_PASSWORD";

```




3. Carga el código a la placa.
4. Abre el **Monitor Serie** (ajustado a **115200 baudios**).
5. Presiona el botón de **Reset** en el shield.
6. Verás que se conecta al Wi-Fi y te dará una **dirección IP** (ej. `[http://192.168.1.15](http://192.168.1.15)`).

### Ver la cámara:

1. Escribe esa IP en el navegador de tu PC o celular (conectados a la misma red).
2. Desplázate hasta abajo en el menú de la izquierda y haz clic en **"Start Stream"**.

> **Tip de experto:** Si la imagen se ve con rayas o el módulo se reinicia solo, es probable que el puerto USB de tu PC no esté entregando suficiente corriente. Intenta usar un puerto USB 3.0 o un cargador de pared de 5V/2A.

¿Lograste obtener la dirección IP en el monitor serie o tuviste algún error al compilar?

```

```
