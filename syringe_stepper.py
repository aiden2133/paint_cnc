import RPi.GPIO as GPIO
import time
import sys
import termios
import tty

# GPIO pins controlling the ULN2003 inputs
pins = [17, 18, 27, 22]

# Sequence for 28BYJ-48 (half-step)
sequence = [
    [1,0,0,1],
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1]
]

GPIO.setmode(GPIO.BCM)
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, 0)


def move_motor(amount_ml, direction="up"):
    """
    Move stepper motor up or down based on amount (ml) and direction.
    """
    steps_per_ml = 512  # Adjust as needed
    steps = int(amount_ml * steps_per_ml)
    delay = 0.002

    if direction == "down":
        step_sequence = reversed(sequence)
    else:
        step_sequence = sequence

    print(f"Moving {direction} for {amount_ml} ml -> {steps} steps")

    try:
        for _ in range(steps):
            for step in step_sequence:
                for pin, val in zip(pins, step):
                    GPIO.output(pin, val)
                time.sleep(delay)
    finally:
        for pin in pins:
            GPIO.output(pin, 0)

def get_key():
    """Read a single keypress from stdin and return it."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch1 = sys.stdin.read(1)
        if ch1 == '\x1b':  # Start of escape sequence
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            return ch1 + ch2 + ch3
        elif ch1 == '\r':
            return 'ENTER'
        else:
            return ch1
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    while True:
        key = get_key()
        if key == '\x1b[A':  # Arrow Up
            move_motor(1, "up")
        elif key == '\x1b[B':  # Arrow Down
            move_motor(1, "down")
        elif key == 'ENTER':
            break
        else:
            print(f"Unknown key: {repr(key)}")