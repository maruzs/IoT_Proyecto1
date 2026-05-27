## Testing Capabilities

**Strict TDD Mode**: disabled
**Detected**: 2026-05-24

### Test Runner

- Command: `none`
- Framework: `none` — Arduino C/C++ embedded firmware has no native unit test runner in this project.

### Test Layers

| Layer       | Available | Tool        |
| ----------- | --------- | ----------- |
| Unit        | ❌        | —           |
| Integration | ❌        | —           |
| E2E         | ❌        | —           |

### Coverage

- Available: ❌
- Command: `—`

### Quality Tools

| Tool         | Available | Command        |
| ------------ | --------- | -------------- |
| Linter       | ❌        | —              |
| Type checker | ❌        | —              |
| Formatter    | ❌        | —              |

### Notes

- This is an Arduino/ESP32 embedded firmware project. The code is compiled and flashed directly to hardware via Arduino IDE 2.x.
- No `platformio.ini`, `Makefile`, `package.json`, `go.mod`, `pyproject.toml`, or CI configs exist.
- No `.github/workflows` or CI/CD pipeline is configured.
- The only "testing" currently available is manual: individual `.ino` sketches in `src/prueba_*` directories serve as hardware validation scripts (prueba_sht30, prueba_MQ, prueba_max4466, prueba_esp32cam).
- Potential future options: PlatformIO with native/unit testing, ArduinoUnit framework, or CI with `arduino-cli compile --warnings all`.
- `strict_tdd: false` is set because no test runner, coverage tool, or linter is available.
