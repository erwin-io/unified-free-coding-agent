"""Host-testable firmware logic without board-specific modules."""


def blink_interval_ms(value):
    if not isinstance(value, int) or value < 20 or value > 60000:
        raise ValueError("Blink interval must be 20..60000 milliseconds")
    return value
