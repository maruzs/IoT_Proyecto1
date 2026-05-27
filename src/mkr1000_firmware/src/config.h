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
// Pins — MKR1000 Available Pins Reference
// ---------------------------------------------------------------------------
// Digital PWM:     0-25 (all support PWM except 23-25)
// Analog inputs:   A0-A5 (also usable as digital pins 14-19)
// I2C (Wire):      SDA = pin 11, SCL = pin 12 (fixed hardware)
// SPI:             MOSI=8, MISO=10, SCK=9, CS=4 (fixed hardware)
// Serial:          RX=13, TX=14 (same as A5, avoid dual use)
//
// SHT30 uses I2C — pins are fixed by hardware (SDA=11, SCL=12).
// Only MQ-2, MAX4466, LED, and buzzer pins are configurable below.
// ---------------------------------------------------------------------------

// --- Sensor Pins (configurable) ---
#define PIN_GAS       A0   // MQ-2 gas sensor (analog input). Options: A0-A5
#define PIN_SONIDO    A1   // MAX4466 sound sensor (analog input). Options: A0-A5

// --- I2C Pins (fixed by MKR1000 hardware) ---
#define PIN_SDA       11   // SHT30 data line — DO NOT CHANGE
#define PIN_SCL       12   // SHT30 clock line — DO NOT CHANGE

// --- Actuator Pins (configurable) ---
#define PIN_LED       6    // Alert LED (digital output). Options: 0-25
#define PIN_BUZZER    5    // Alert buzzer (digital output). Options: 0-25

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
