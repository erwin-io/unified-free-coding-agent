# MicroPython firmware starter

Target boards: Raspberry Pi Pico/RP2040 or ESP32 using MicroPython.
Source is in `src/`. Host unit tests use CPython with no hardware.

## Host validation

```powershell
python -m unittest discover -s tests -v
python -m compileall -q src
```

## Optional device work

Install `python -m pip install mpremote` (or a separate tools venv). Identify the exact port and board before using `mpremote connect COMx repl`.

Use `tools/device.ps1 -Port COMx -Action list` for read-only listing and `-Action upload -ConfirmUpload` for explicit writes. A connected MicroPython-enabled board is required. This does not install or replace a firmware image; initial MicroPython flashing is board-specific.

No automatic code upload or erase occurs during normal agent setup.
