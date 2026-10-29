---
name: cpp-development
description: Develop portable C++17 with CMake/CTest, and prepare hardware-specific embedded C++ work using an explicit board toolchain.
---
Inspect CMakeLists.txt, compiler and C++ standard. Use CMake configure/build
and CTest for portable native projects; capture actual exit codes.
For Arduino, ESP32, RP2040 and other microcontrollers, inspect platformio.ini,
Arduino CLI or board-specific build systems and exact board identity. Never
assume native tests prove embedded timing, memory or I/O behavior.
Do not flash devices, erase bootloaders, or change hardware pin mappings
without an owner-approved hardware profile. Preserve existing tests and ABI/API.
