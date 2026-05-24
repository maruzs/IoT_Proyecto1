/**
 * camera_server.cpp — ESP32-CAM Camera Initialization & MJPEG Stream
 *
 * initCamera() configura la cámara AI-Thinker usando constantes de config.h.
 * startCameraServer() inicia el servidor HTTP en puerto 80 para streaming MJPEG.
 */

#include "camera_server.h"
#include "config.h"

// Protocolo de boundary para stream MJPEG
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static httpd_handle_t stream_httpd = NULL;

static esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t* fb = NULL;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t* _jpg_buf = NULL;
    char part_buf[64];

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) return res;

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("Fallo al capturar imagen");
            res = ESP_FAIL;
        } else {
            _jpg_buf_len = fb->len;
            _jpg_buf = fb->buf;
        }

        if (res == ESP_OK) {
            size_t hlen = snprintf(part_buf, 64, _STREAM_PART, _jpg_buf_len);
            res = httpd_resp_send_chunk(req, part_buf, hlen);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char*)_jpg_buf, _jpg_buf_len);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }

        if (fb) {
            esp_camera_fb_return(fb);
            fb = NULL;
            _jpg_buf = NULL;
        }

        if (res != ESP_OK) break;
    }
    return res;
}

bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = CAM_Y2_GPIO_NUM;
    config.pin_d1 = CAM_Y3_GPIO_NUM;
    config.pin_d2 = CAM_Y4_GPIO_NUM;
    config.pin_d3 = CAM_Y5_GPIO_NUM;
    config.pin_d4 = CAM_Y6_GPIO_NUM;
    config.pin_d5 = CAM_Y7_GPIO_NUM;
    config.pin_d6 = CAM_Y8_GPIO_NUM;
    config.pin_d7 = CAM_Y9_GPIO_NUM;
    config.pin_xclk = CAM_XCLK_GPIO_NUM;
    config.pin_pclk = CAM_PCLK_GPIO_NUM;
    config.pin_vsync = CAM_VSYNC_GPIO_NUM;
    config.pin_href = CAM_HREF_GPIO_NUM;
    config.pin_sscb_sda = CAM_SIOD_GPIO_NUM;
    config.pin_sscb_scl = CAM_SIOC_GPIO_NUM;
    config.pin_pwdn = CAM_PWDN_GPIO_NUM;
    config.pin_reset = CAM_RESET_GPIO_NUM;
    config.xclk_freq_hz = CAM_XCLK_FREQ_HZ;
    config.pixel_format = PIXFORMAT_JPEG;

    if (psramFound()) {
        config.frame_size = CAM_FRAME_SIZE_PSRAM;
        config.jpeg_quality = CAM_JPEG_QUALITY_PSRAM;
        config.fb_count = CAM_FB_COUNT_PSRAM;
    } else {
        config.frame_size = CAM_FRAME_SIZE_NO_PSRAM;
        config.jpeg_quality = CAM_JPEG_QUALITY_NO_PSRAM;
        config.fb_count = CAM_FB_COUNT_NO_PSRAM;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Fallo camara: 0x%x\n", err);
        return false;
    }
    return true;
}

void startCameraServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;

    httpd_uri_t index_uri = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = stream_handler,
        .user_ctx = NULL
    };

    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &index_uri);
    }
}
