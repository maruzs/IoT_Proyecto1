/**
 * camera_server.h — ESP32-CAM Camera & HTTP Stream Server
 *
 * Declara initCamera() y startCameraServer() para el módulo ESP32-CAM.
 */

#ifndef CAMERA_SERVER_H
#define CAMERA_SERVER_H

#include <esp_camera.h>
#include <esp_http_server.h>

bool initCamera();
void startCameraServer();

#endif
