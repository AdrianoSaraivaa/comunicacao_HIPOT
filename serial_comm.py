import serial
import time


def open_serial(port, baudrate=9600, timeout=1):
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=timeout,
    )
    time.sleep(2)
    return ser


def read_line(ser):
    if ser.in_waiting > 0:
        return ser.readline().decode(errors="ignore").strip()
    return None
