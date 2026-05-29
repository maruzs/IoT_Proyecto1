#include "message_builder.h"
#include "config.h"
#include <ArduinoJson.h>
#include <stddef.h>

void buildSensorJSON(const SensorData& data, char* buffer, size_t bufferSize, const char* alertMsg) {
    StaticJsonDocument<256> doc;

    doc["equipo"] = EQUIPO_ID;

    // Temperatura
    if (data.temperatureValid) {
        doc["temperatura"] = data.temperature;
    } else {
        doc["temperatura"] = (char*)0;
    }

    // Humedad
    if (data.humidityValid) {
        doc["humedad"] = data.humidity;
    } else {
        doc["humedad"] = (char*)0;
    }

    // Gas (MQ-2)
    if (data.gasValid) {
        doc["gas"] = data.gas;
    } else {
        doc["gas"] = (char*)0;
    }

    // Gas Digital (MQ-2 DO)
    if (data.gasDigitalValid) {
        doc["gas_digital"] = (data.gasDigital == LOW) ? "ALERTA" : "NORMAL";
    } else {
        doc["gas_digital"] = (char*)0;
    }

    // Sonido (MAX4466), publicado como sensor_extra para compatibilidad
    if (data.soundValid) {
        doc["sensor_extra"] = data.sound;
    } else {
        doc["sensor_extra"] = (char*)0;
    }

    // Alerta condicional: solo aparece cuando hay anomalia
    if (alertMsg != nullptr) {
        doc["alerta"] = alertMsg;
    }

    serializeJson(doc, buffer, bufferSize);
}
