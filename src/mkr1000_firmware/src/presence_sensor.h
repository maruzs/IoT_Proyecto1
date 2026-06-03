#ifndef MKR1000_PRESENCE_SENSOR_H
#define MKR1000_PRESENCE_SENSOR_H

/**
 * presence_sensor.h — Debounced reading of HC-SR501 presence sensor
 *
 * Returns the stable digital state with a 1-second debounce to avoid
 * rapid triggers from sensor noise.
 */

/** Returns the current debounced presence state (true = HIGH, false = LOW). */
bool readPresence();

#endif
