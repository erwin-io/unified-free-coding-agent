# C++17 CMake project

Cross-platform C++ development baseline with a reusable library, executable and unit tests via CTest. Requires CMake 3.20+, and a working MSVC, GCC or Clang C++ compiler.

```powershell
cmake -S . -B build
cmake --build build --config Debug
ctest --test-dir build -C Debug --output-on-failure
```

For Arduino, ESP32, RP2040 or other embedded C++ targets, configure a **specific board/toolchain** (for example PlatformIO) before building/uploading firmware. This generic template does not flash hardware.
