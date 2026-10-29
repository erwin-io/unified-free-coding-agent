---
name: micropython-firmware
description: Develop Raspberry Pi Pico/RP2040 and ESP32 MicroPython projects with explicit hardware safety boundaries.
---
Start by reading board model, firmware version, pin map, serial port and voltage
requirements from .agent/ARCHITECTURE.md. If unknown, ask the project owner
before using GPIO, LoRa/SPI/I2C wiring, or filesystem writes on the board.
Separate pure host-tested logic from machine-dependent imports.
Use CPython unittest and compileall for host-level checks only; these do not
prove actual device compatibility or timing. For on-device work, mpremote is
optional; use a real explicit COM port. Never upload/erase/reset/run unknown
firmware without explicit owner authorization. Document the actual board output,
serial logs, and timing measurements separately from simulator results.
