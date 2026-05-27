/**
 * config.h — MKR1000 Firmware Configuration
 *
 * Centralized constants: pins, thresholds, EQUIPO_ID, and MQTT topic macros.
 * Change EQUIPO_ID once and all topics update automatically via C string
 * concatenation.
 */

#ifndef MKR1000_CONFIG_H
#define MKR1000_CONFIG_H

// ---------------------------------------------------------------------------
// Identity
// ---------------------------------------------------------------------------
#define EQUIPO_ID "equipoXX"   // Cambia XX por tu número de equipo

// ---------------------------------------------------------------------------
// Pins
// ---------------------------------------------------------------------------
#define PIN_GAS     A0         // Sensor MQ-2 (analógico)
#define PIN_SONIDO  A1         // Sensor MAX4466 (analógico)
#define PIN_LED     6          // LED de alerta / control remoto
#define PIN_BUZZER  5          // Buzzer de alerta

// ---------------------------------------------------------------------------
// Alert Thresholds
// ---------------------------------------------------------------------------
#define UMBRAL_GAS    400    // Valor MQ-2 que dispara alerta
#define UMBRAL_TEMP   30.0f  // °C que dispara alerta
#define UMBRAL_SONIDO 500    // Valor MAX4466 que dispara alerta

// ---------------------------------------------------------------------------
// Timing
// ---------------------------------------------------------------------------
#define PUBLISH_INTERVAL_MS 2000  // Intervalo entre publicaciones MQTT

// ---------------------------------------------------------------------------
// MQTT Topics (C preprocessor string-literal concatenation)
// Adjacent string literals are merged by the compiler at zero SRAM cost.
// ---------------------------------------------------------------------------
#define TOPIC_BASE           "smarthome/" EQUIPO_ID
#define TOPIC_DATOS          TOPIC_BASE "/datos"
#define TOPIC_CONTROL_LED    TOPIC_BASE "/control/led"
#define TOPIC_CONTROL_BUZZER TOPIC_BASE "/control/buzzer"
#define TOPIC_ALERTA         TOPIC_BASE "/alerta"

#endif // MKR1000_CONFIG_H
