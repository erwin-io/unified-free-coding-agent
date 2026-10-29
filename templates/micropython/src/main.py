"""MicroPython entrypoint. Firmware controls actual LED only when run on board."""
import time
from machine import Pin
from config import LED_PIN, INTERVAL_MS
from logic import blink_interval_ms


def main():
    led = Pin(LED_PIN, Pin.OUT)
    interval = blink_interval_ms(INTERVAL_MS)
    while True:
        led.toggle()
        time.sleep_ms(interval)


if __name__ == "__main__":
    main()
