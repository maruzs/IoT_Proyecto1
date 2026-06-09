/**
 * burst_capture.h — Non-blocking burst capture state machine
 *
 * Receives MQTT iniciar_burst command, captures frames at regular
 * intervals and publishes each one via MQTT. Stops after BURST_DURATION_S.
 */

#ifndef BURST_CAPTURE_H
#define BURST_CAPTURE_H

void handleBurstCommand(const char* payload);
void checkBurstTimeout();

#endif
