/**
 * camera_server.cpp — ESP32-CAM Camera Initialization
 *
 * initCamera() configura la cámara AI-Thinker usando constantes de config.h.
 * Sin servidor HTTP: el proyecto usa snapshots bajo demanda vía MQTT.
 */

#include "camera_server.h"
#include "config.h"
#include "Arduino.h"

bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = CAM_Y2_GPIO_NUM;
    config.pin_d1 = CAM_Y3_GPIO_NUM;
    config.pin_d2 = CAM_Y4_GPIO_NUM;
    config.pin_d3 = CAM_Y5_GPIO_NUM;
    config.pin_d4 = CAM_Y6_GPIO_NUM;
    config.pin_d5 = CAM_Y7_GPIO_NUM;
    config.pin_d6 = CAM_Y8_GPIO_NUM;
    config.pin_d7 = CAM_Y9_GPIO_NUM;
    config.pin_xclk = CAM_XCLK_GPIO_NUM;
    config.pin_pclk = CAM_PCLK_GPIO_NUM;
    config.pin_vsync = CAM_VSYNC_GPIO_NUM;
    config.pin_href = CAM_HREF_GPIO_NUM;
    config.pin_sscb_sda = CAM_SIOD_GPIO_NUM;
    config.pin_sscb_scl = CAM_SIOC_GPIO_NUM;
    config.pin_pwdn = CAM_PWDN_GPIO_NUM;
    config.pin_reset = CAM_RESET_GPIO_NUM;
    config.xclk_freq_hz = CAM_XCLK_FREQ_HZ;
    config.pixel_format = PIXFORMAT_JPEG;

    if (psramFound()) {
        config.frame_size = CAM_FRAME_SIZE_PSRAM;
        config.jpeg_quality = CAM_JPEG_QUALITY_PSRAM;
        config.fb_count = CAM_FB_COUNT_PSRAM;
    } else {
        config.frame_size = CAM_FRAME_SIZE_NO_PSRAM;
        config.jpeg_quality = CAM_JPEG_QUALITY_NO_PSRAM;
        config.fb_count = CAM_FB_COUNT_NO_PSRAM;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Fallo camara: 0x%x\n", err);
        return false;
    }
    return true;
}
