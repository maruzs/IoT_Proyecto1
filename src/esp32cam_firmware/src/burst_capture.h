/**
 * burst_capture.h — Non-blocking burst capture state machine
 *
 * Receives MQTT iniciar_burst command, starts HTTP camera server,
 * publishes stream URL, and stops after BURST_DURATION_S.
 */

#ifndef BURST_CAPTURE_H
#define BURST_CAPTURE_H

void handleBurstCommand(const char* payload);
void checkBurstTimeout();

#endif
