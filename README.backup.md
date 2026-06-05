# Inventario

## Inventario Placas/ Sensores

| Componente     | Nombre           | Voltaje |
| -------------- | ---------------- | ------- |
| Placa Port.    | Arduino MKR 1000 | 3.3v    |
| S. Gas         | MQ Sensor        | 5v      |
| Camara         | ESP 32-CAM       | USB     |
| S. Temperatura | SHT30            | 3.3v    |
| S. Humedad     | SHT30            | 3.3v    |
| Microfono      | MAX4466          | 3.3v    |

## Inventario Componentes

| Componente     | Cantidad |
| -------------- | -------- |
| Potenciometros | 4        |
| Led Amarillo   | 7        |
| Led Verde      | 9        |
| Led Rojos      | 10       |
| Led Azules     | 4        |


---

## Diagrama de pines — MKR1000

### Sensores

| Componente | Pin Sensor | Pin MKR1000 | Tipo de Señal |
| ---------- | ---------- | ----------- | ------------- |
| MQ Sensor (Gas)   | VCC / GND / AO / DO | VCC / GND / **A0** / **A2** | AO: Analógica, DO: Digital |
| MAX4466 (Sonido)  | VCC / GND / OUT | VCC / GND / **A1** | Analógica |
| SHT30 (Temp/Hum)  | VCC / GND / SDA / SCL | VCC / GND / **11** / **12** | I2C |

### Actuadores

| Componente | Pin MKR1000 | Tipo de Señal |
| ---------- | ----------- | ------------- |
| LED Alerta | **6** | Digital (PWM) |
| Buzzer     | **5** | Digital (PWM) |

### Pines SHT30 — Detalle por color de cable

| Color del Cable | Función I2C | Pin MKR1000 |
| --------------- | ----------- | ----------- |
| 🔴 Rojo   | VCC (3.3V) | VCC |
| ⚫ Negro  | GND        | GND |
| 🟡 Amarillo | SCL (Reloj) | **12** |
| 🟢 Verde  | SDA (Datos) | **11** |

### Pines disponibles para reasignar

| Categoría | Pines disponibles |
| --------- | ----------------- |
| Entradas analógicas | A0, A1, A2, A3, A4, A5 |
| Digitales PWM | 0–25 (excepto 11, 12 reservados para I2C) |

> Para cambiar un pin, editá solo `src/mkr1000_firmware/src/config.h`.