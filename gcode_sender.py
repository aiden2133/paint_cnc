import serial
import time
import re
import sys
import termios
import tty
from syringe_stepper import move_motor

SERIAL_PORT = "/dev/ttyACM0"  # Use `ls /dev/tty*` to find
BAUD_RATE = 115200
DISPENSE_REGEX = re.compile(r"M117\s+DISPENSE\s+(\d+(\.\d+)?)")

#for pointillisim dispensing
DISPENSE_AMOUNT = 10

'''
$22=1      ; Enable homing cycle
$23=3      ; Homing direction mask (Z+, X-, Y-)
$5=1       ; Limit pins use pull-up resistors
$21=1      ; Enable hard limits

$100=40.00  ; X steps/mm
$101=40.00  ; Y steps/mm
$102=400.00 ; Z steps/mm
$110=1000   ; X max rate (mm/min)
$111=1000   ; Y max rate
$112=500    ; Z max rate
$130=650    ; X max travel (mm)
$131=700    ; Y max travel
$132=50     ; Z max travel

'''

GRBL_SETUP = [
    "$22=0", "$23=3", "$5=1", "$21=0",
    "$100=40.00", "$101=40.00", "$102=400.00",
    "$110=1000", "$111=1000", "$112=500",
    "$130=650", "$131=700", "$132=50"
]

def setup_grbl(ser):
    for cmd in GRBL_SETUP:
        print(f"Configuring GRBL: {cmd}")
        ser.write((cmd + '\n').encode())
        time.sleep(0.1)

        #read lines
        attempts = 0
        while True:
            resp_bytes = ser.readline()
            if not resp_bytes:
                # No data received, keeps trying until 5 attempts
                attempts += 1
                if attempts > 5:
                    return f"Warning: No response received for command: {cmd}"
                    break
                continue

            try:
                resp = resp_bytes.decode('utf-8', errors='ignore').strip()
            except Exception as e:
                return f"Decode error: {e}"

            print (f"[GRBL] {resp}")
            break

def send_gcode_line(ser, line):
    """
    Sends a single line of G-code to GRBL and waits for 'ok'.
    """
    line = line.strip()
    if not line:
        return

    print(f">> Sending: {line}")
    ser.write((line + '\n').encode())

    while True:
        resp = ser.readline().decode().strip()
        return f"[GRBL] {resp}"

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

def send_gcode_file(gcode_path):
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)
        ser.reset_input_buffer()

        with open(gcode_path, 'r') as f:
            for line in f:
                if line.startswith('M0'):
                    #ability to move motor
                    print("Move syringe motor to correct location (↑/↓)")
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

                    #press enter to remake it
                    print("[GCODE] Paused (M0). Type ENTER to continue...")
                    input()
                    ser.write(b'~')  # Resume GRBL
                    ser.flush()
                    continue
                if line.startswith(';DISPENSE'):
                    move_motor(DISPENSE_AMOUNT)
                    continue

                line = line.strip()
                if not line or line.startswith(';'):
                    continue

                #print(f">> Sending: {line}")
                ser.write((line + '\n').encode())


                #Wait for GRBL response
                resp = ser.readline().decode().strip()
                if resp:
                    print(f"[GRBL] {resp}")


if __name__ == "__main__":
    testing_sender = False
    sending_file = True

    if testing_sender:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            time.sleep(2)  # Wait for Arduino reset
            ser.write(b"\r\n")  # Send empty line to wake GRBL
            time.sleep(0.5)
            while ser.in_waiting:
                response = ser.readline().decode('utf-8', errors='ignore').strip()
                print("Received:", response)

    if sending_file:
        file_name = 'pointillism.gcode'
        send_gcode_file(file_name)