#ifndef MKR1000_MESSAGE_BUILDER_H
#define MKR1000_MESSAGE_BUILDER_H

/**
 * message_builder.h — Construccion de payload JSON para publicacion MQTT
 *
 * Usa ArduinoJson 6.x y emite null para sensores fallidos.
 */

#include "sensor_reader.h"
#include <Arduino.h> // <--- AGREGA ESTO AQUÍ

/**
 * Construye el JSON de sensores en `buffer`.
 *
 * @param data      Lecturas de sensores con flags de validez.
 * @param buffer    Buffer de salida (recomendado >= 256 bytes).
 * @param bufferSize Tamano del buffer.
 * @param alertMsg  Mensaje de alerta opcional; si es nullptr, no se incluye el campo.
 */
void buildSensorJSON(const SensorData& data, char* buffer, size_t bufferSize, const char* alertMsg = nullptr);

#endif
