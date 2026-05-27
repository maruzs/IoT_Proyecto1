/**
 * config.h — ESP32-CAM Firmware Configuration
 *
 * Centralized constants: camera pins, resolution, EQUIPO_ID, and MQTT topic macros.
 * Change EQUIPO_ID once and all topics update automatically via C string
 * concatenation.
 */

#ifndef ESP32CAM_CONFIG_H
#define ESP32CAM_CONFIG_H

// ---------------------------------------------------------------------------
// Identity
// ---------------------------------------------------------------------------
#define EQUIPO_ID "equipoXX"   // Cambia XX por tu número de equipo

// ---------------------------------------------------------------------------
// Camera Pins (AI-Thinker module)
// ---------------------------------------------------------------------------
#define CAM_PWDN_GPIO_NUM     32
#define CAM_RESET_GPIO_NUM    -1
#define CAM_XCLK_GPIO_NUM      0
#define CAM_SIOD_GPIO_NUM     26
#define CAM_SIOC_GPIO_NUM     27
#define CAM_Y9_GPIO_NUM       35
#define CAM_Y8_GPIO_NUM       34
#define CAM_Y7_GPIO_NUM       39
#define CAM_Y6_GPIO_NUM       36
#define CAM_Y5_GPIO_NUM       21
#define CAM_Y4_GPIO_NUM       19
#define CAM_Y3_GPIO_NUM       18
#define CAM_Y2_GPIO_NUM        5
#define CAM_VSYNC_GPIO_NUM    25
#define CAM_HREF_GPIO_NUM     23
#define CAM_PCLK_GPIO_NUM     22

// ---------------------------------------------------------------------------
// Camera Resolution & Quality
// ---------------------------------------------------------------------------
// FRAMESIZE_VGA  = 640x480  (con PSRAM)
// FRAMESIZE_SVGA = 800x600  (sin PSRAM)
#define CAM_FRAME_SIZE_PSRAM    FRAMESIZE_VGA
#define CAM_FRAME_SIZE_NO_PSRAM FRAMESIZE_SVGA
#define CAM_JPEG_QUALITY_PSRAM  10   // 0-63, menor = más calidad
#define CAM_JPEG_QUALITY_NO_PSRAM 12
#define CAM_FB_COUNT_PSRAM      2    // Doble buffer para mayor FPS
#define CAM_FB_COUNT_NO_PSRAM   1

// ---------------------------------------------------------------------------
// Camera Clock
// ---------------------------------------------------------------------------
#define CAM_XCLK_FREQ_HZ  20000000   // 20 MHz

// ---------------------------------------------------------------------------
// Timing
// ---------------------------------------------------------------------------
#define MQTT_LOOP_DELAY_MS 10

// ---------------------------------------------------------------------------
// MQTT Topics (C preprocessor string-literal concatenation)
// Adjacent string literals are merged by the compiler at zero SRAM cost.
// ---------------------------------------------------------------------------
#define TOPIC_BASE           "smarthome/" EQUIPO_ID
#define TOPIC_CAMARA_EVENTO  TOPIC_BASE "/camara/evento"
#define TOPIC_CAMARA_CONTROL TOPIC_BASE "/camara/control"

#endif // ESP32CAM_CONFIG_H
