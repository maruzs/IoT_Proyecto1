#ifndef MKR1000_ALERT_SYSTEM_H
#define MKR1000_ALERT_SYSTEM_H

/**
 * alert_system.h — Evaluacion de umbrales y control de actuadores
 *
 * Compara lecturas contra constantes de config.h y enciende/apaga
 * LED y buzzer. Tambien expone un helper generico para cambiar
 * el estado de cualquier actuador (usado por el callback MQTT).
 */

#include "sensor_reader.h"

/**
 * Evalua lecturas contra UMBRAL_GAS, UMBRAL_TEMP y UMBRAL_SONIDO.
 * Enciende LED y buzzer si se supera algun umbral.
 *
 * @return Mensaje de alerta si hay anomalia, nullptr si todo esta normal.
 */
const char* evaluateAndActuate(const SensorData& data);

/** Encapsula digitalWrite con booleano legible (true = HIGH). */
void setActuatorState(int pin, bool state);

#endif
