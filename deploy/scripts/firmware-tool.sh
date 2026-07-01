#!/usr/bin/env bash
# =============================================================================
# firmware-tool.sh — Firmware lifecycle helper for MKR1000 + ESP32-CAM
# =============================================================================
# Usage:
#   ./deploy/scripts/firmware-tool.sh generate
#   ./deploy/scripts/firmware-tool.sh build [--no-upload]
#   ./deploy/scripts/firmware-tool.sh upload [--port-mkr=<port>] [--port-esp=<port>]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOY_DIR="${PROJECT_ROOT}/deploy"
CERTS_DIR="${PROJECT_ROOT}/deploy/mosquitto/certs"
ENV_FILE="${DEPLOY_DIR}/.env"

MKR_DIR="${PROJECT_ROOT}/src/mkr1000_firmware"
ESP_DIR="${PROJECT_ROOT}/src/esp32cam_firmware"
MKR_SECRETS="${MKR_DIR}/src/secrets.h"
ESP_SECRETS="${ESP_DIR}/src/secrets.h"

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[0;33m%s\033[0m\n' "$*"; }

check() {
    local msg="$1"; shift
    if "$@"; then
        green "✓ ${msg}"
    else
        red "✗ ${msg}"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Environment handling
# ---------------------------------------------------------------------------
source_env() {
    if [[ ! -f "${ENV_FILE}" ]]; then
        red "ERROR: ${ENV_FILE} not found."
        exit 1
    fi

    # ponytail: export all vars while sourcing so they're visible to this script
    set -a
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
    set +a

    # Map existing .env names to the canonical names this script expects.
    # ponytail: project .env uses MQTT_USER_MKR1000; spec uses MKR1000_MQTT_USER.
    : "${MQTT_SERVER:=${MQTT_BROKER_IP:-}}"
    : "${MKR1000_MQTT_USER:=${MQTT_USER_MKR1000:-}}"
    : "${MKR1000_MQTT_PASS:=${MQTT_PASS_MKR1000:-}}"
    : "${ESP32CAM_MQTT_USER:=${MQTT_USER_ESP32CAM:-}}"
    : "${ESP32CAM_MQTT_PASS:=${MQTT_PASS_ESP32CAM:-}}"

    # Defaults for optional ports
    : "${MKR1000_MQTT_PORT:=1884}"
    : "${ESP32CAM_MQTT_PORT:=8883}"
}

validate_env() {
    local missing=""
    for var in WIFI_SSID WIFI_PASSWORD MQTT_SERVER MKR1000_MQTT_USER MKR1000_MQTT_PASS ESP32CAM_MQTT_USER ESP32CAM_MQTT_PASS; do
        if [[ -z "${!var:-}" ]]; then
            missing="${missing} ${var}"
        fi
    done

    if [[ -n "${missing}" ]]; then
        red "ERROR: missing required environment variables:${missing}"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Command: generate
# ---------------------------------------------------------------------------
cmd_generate() {
    source_env
    validate_env

    if [[ ! -f "${CERTS_DIR}/ca.crt" ]]; then
        yellow "CA cert missing; running generate-certs.sh first..."
        "${SCRIPT_DIR}/generate-certs.sh"
    fi

    local ca_cert
    ca_cert=$(cat "${CERTS_DIR}/ca.crt")

    green "Generating ${MKR_SECRETS}"
    cat > "${MKR_SECRETS}" <<EOF
#ifndef MKR1000_SECRETS_H
#define MKR1000_SECRETS_H

#define WIFI_SSID     "${WIFI_SSID}"
#define WIFI_PASSWORD "${WIFI_PASSWORD}"

#define MQTT_SERVER   "${MQTT_SERVER}"
#define MQTT_PORT     ${MKR1000_MQTT_PORT}
#define MQTT_USER     "${MKR1000_MQTT_USER}"
#define MQTT_PASSWORD "${MKR1000_MQTT_PASS}"

#endif
EOF

    green "Generating ${ESP_SECRETS}"
    cat > "${ESP_SECRETS}" <<EOF
#ifndef ESP32CAM_SECRETS_H
#define ESP32CAM_SECRETS_H

#define WIFI_SSID     "${WIFI_SSID}"
#define WIFI_PASSWORD "${WIFI_PASSWORD}"

#define MQTT_SERVER   "${MQTT_SERVER}"
#define MQTT_PORT     ${ESP32CAM_MQTT_PORT}
#define MQTT_USER     "${ESP32CAM_MQTT_USER}"
#define MQTT_PASSWORD "${ESP32CAM_MQTT_PASS}"

// CA autofirmado del broker Mosquitto (puerto 8883)
const char CA_CERT[] = R"EOF(
${ca_cert}
)EOF";

#endif
EOF

    green "secrets.h generated successfully."
}

# ---------------------------------------------------------------------------
# Command: build
# ---------------------------------------------------------------------------
cmd_build() {
    local no_upload=false
    for arg in "$@"; do
        case "$arg" in
            --no-upload) no_upload=true ;;
            *) red "Unknown build option: $arg"; exit 1 ;;
        esac
    done

    if ! command -v arduino-cli &>/dev/null; then
        red "ERROR: arduino-cli not found in PATH."
        exit 1
    fi

    cmd_generate

    green "Compiling MKR1000 firmware..."
    arduino-cli compile --fqbn arduino:samd:mkr1000 "${MKR_DIR}/"

    green "Compiling ESP32-CAM firmware..."
    arduino-cli compile --fqbn esp32:esp32:esp32cam "${ESP_DIR}/"

    if [[ "$no_upload" == true ]]; then
        green "Build complete (--no-upload: skipping upload)."
        return 0
    fi

    cmd_upload
}

# ---------------------------------------------------------------------------
# Command: upload
# ---------------------------------------------------------------------------
find_port() {
    local fqbn="$1"
    arduino-cli board list 2>/dev/null \
        | awk -v fqbn="$fqbn" '$0 ~ fqbn { print $1; exit }'
}

cmd_upload() {
    local port_mkr="" port_esp=""

    for arg in "$@"; do
        case "$arg" in
            --port-mkr=*) port_mkr="${arg#*=}" ;;
            --port-esp=*) port_esp="${arg#*=}" ;;
            *) red "Unknown upload option: $arg"; exit 1 ;;
        esac
    done

    if [[ -z "$port_mkr" ]]; then
        port_mkr=$(find_port "arduino:samd:mkr1000")
    fi
    if [[ -z "$port_esp" ]]; then
        port_esp=$(find_port "esp32:esp32:esp32cam")
    fi

    if [[ -n "$port_mkr" ]]; then
        green "Uploading MKR1000 to ${port_mkr}..."
        arduino-cli upload -p "$port_mkr" --fqbn arduino:samd:mkr1000 "${MKR_DIR}/"
        green "MKR1000 upload complete."
    else
        yellow "MKR1000 port not detected; skipping."
    fi

    if [[ -n "$port_esp" ]]; then
        green "Uploading ESP32-CAM to ${port_esp}..."
        arduino-cli upload -p "$port_esp" --fqbn esp32:esp32:esp32cam "${ESP_DIR}/"
        green "ESP32-CAM upload complete."
    else
        yellow "ESP32-CAM port not detected; skipping."
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: firmware-tool.sh <command> [options]

Commands:
  generate              Generate secrets.h for both firmwares from deploy/.env + CA certs
  build [--no-upload]   Compile firmwares. Uploads if boards detected (or use --no-upload to skip)
  upload [--port-mkr=<port>] [--port-esp=<port>]
                        Upload pre-compiled binaries to boards
EOF
}

main() {
    if [[ $# -lt 1 ]]; then
        usage
        exit 1
    fi

    local cmd="$1"
    shift

    case "$cmd" in
        generate) cmd_generate "$@" ;;
        build)    cmd_build "$@" ;;
        upload)   cmd_upload "$@" ;;
        -h|--help|help) usage ;;
        *)        red "Unknown command: $cmd"; usage; exit 1 ;;
    esac
}

main "$@"
