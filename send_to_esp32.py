import serial
import time

try:
    ser = serial.Serial('COM4', 115200, timeout=2)
    print("Conectado a COM4")
except serial.SerialException as e:
    print(f"Error conectando a COM4: {e}")
    print("Por favor, cierra cualquier otra aplicacion usando COM4 (Arduino IDE, Monitor Serial, etc.)")
    exit(1)

time.sleep(2)

face_detected = input("Face detected? (true/false): ")

if(face_detected == "true"):
    ser.write(b'1')
    time.sleep(2)
else:
    ser.write(b'0')
    time.sleep(2)

ser.close()