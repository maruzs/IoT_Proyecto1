/**
 * burst_capture.cpp — Non-blocking burst capture state machine
 *
 * IDLE → BURSTING on {"accion":"iniciar_burst"}
 * During BURSTING: captures and publishes frames at CAPTURE_INTERVAL_MS.
 * BURSTING → IDLE after BURST_DURATION_S seconds.
 * No delay() used; millis() comparisons in checkBurstTimeout().
 */

#include "burst_capture.h"
#include "config.h"
#include "mqtt_bridge.h"
#include <esp_camera.h>
#include <Arduino.h>

enum BurstState {
    STATE_IDLE,
    STATE_BURSTING
};

static BurstState burstState = STATE_IDLE;
static unsigned long burstStartMs = 0;
static unsigned long lastCaptureMs = 0;

// ~4 fps: suficiente para face_recognition sin saturar MQTT
static const unsigned long CAPTURE_INTERVAL_MS = 250;

void handleBurstCommand(const char* payload) {
    if (strstr(payload, "iniciar_burst") != NULL) {
        if (burstState == STATE_IDLE) {
            burstState = STATE_BURSTING;
            burstStartMs = millis();
            lastCaptureMs = 0;  // fuerza captura inmediata en el primer tick
            Serial.println("Burst iniciado");
        }
    }
}

void checkBurstTimeout() {
    if (burstState != STATE_BURSTING) return;

    unsigned long now = millis();

    // ¿Terminó la ráfaga?
    if (now - burstStartMs >= BURST_DURATION_S * 1000UL) {
        publishToTopic(TOPIC_CAMARA_EVENTO, "{\"estado\":\"burst_complete\"}");
        burstState = STATE_IDLE;
        Serial.println("Burst completo");
        return;
    }

    // Capturar frame al intervalo configurado
    if (now - lastCaptureMs >= CAPTURE_INTERVAL_MS) {
        lastCaptureMs = now;

        camera_fb_t* fb = esp_camera_fb_get();
        if (fb) {
            Serial.print("Frame: "); Serial.print(fb->len); Serial.println(" bytes");
            if (!publishCameraImage(fb->buf, fb->len)) {
                Serial.println("FALLO al publicar frame");
            }
            esp_camera_fb_return(fb);
        } else {
            Serial.println("FALLO: esp_camera_fb_get() devolvió NULL");
        }
    }
}
