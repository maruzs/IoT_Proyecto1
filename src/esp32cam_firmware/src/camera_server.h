/**
 * camera_server.h — ESP32-CAM Camera Initialization
 *
 * Solo expone initCamera(). El stream MJPEG y el servidor HTTP se eliminaron:
 * el proyecto usa snapshots bajo demanda vía MQTT, no streaming.
 */

#ifndef CAMERA_SERVER_H
#define CAMERA_SERVER_H

#include <esp_camera.h>

bool initCamera();

#endif
