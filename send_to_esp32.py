import serial
import serial.tools.list_ports
import time

# Función para encontrar el puerto ESP32
def find_esp32_port():
    ports = serial.tools.list_ports.comports()
    available_ports = []
    
    print("Puertos COM disponibles:")
    for port in ports:
        print(f"  - {port.device}: {port.description}")
        available_ports.append(port.device)
    
    # Intento COM4 primero, luego otros puertos
    preferred_ports = ['COM4'] + [p for p in available_ports if p != 'COM4']
    
    for port in preferred_ports:
        try:
            ser = serial.Serial(port, 115200, timeout=2)
            print(f"\nConectado exitosamente a {port}")
            return ser
        except serial.SerialException:
            print(f"No se pudo conectar a {port}")
            continue
    
    return None

# Intento de conexión
ser = find_esp32_port()

if ser is None:
    print("\nError: No se pudo conectar a ningún puerto COM")
    print("Soluciones posibles:")
    print("1. Verifica que el ESP32 esté conectado via USB")
    print("2. Instala los drivers CH340/CP2102 si es necesario")
    print("3. Desconecta y vuelve a conectar el ESP32")
    print("4. Cierra el Monitor Serial o Arduino IDE si están usando el puerto")
    exit(1)

time.sleep(2)

face_detected = input("Face detected? (true/false): ")
username = input("Username: ") if face_detected == "true" else "unknown"

# Enviar datos en formato: status|username
data_to_send = f"{face_detected}|{username}\n"
ser.write(data_to_send.encode('utf-8'))
print(f"Sent: {data_to_send.strip()}")
time.sleep(2)

ser.close()