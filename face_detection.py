import cv2
import numpy as np
import os
import pickle
import time
from datetime import datetime
import serial
import threading

class FaceDetector:
    def __init__(self):
        # Inicializar clasificadores
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        # Directorios
        self.dataset_dir = 'authorized_faces'
        self.encodings_file = 'face_encodings.pkl'
        
        # Variables
        self.authorized_faces = {}
        self.current_frame = None
        self.face_locations = []
        self.face_names = []
        self.processing = False
        
        # Sistema de estabilización
        self.detection_history = []
        self.max_history = 5
        self.detection_threshold = 0.6
        
        # Comunicación ESP32
        self.esp32_port = 'COM4'
        self.esp32_baudrate = 115200
        self.esp32_connected = False
        
        # Crear directorios necesarios
        os.makedirs(self.dataset_dir, exist_ok=True)
        
        # Cargar rostros autorizados existentes
        self.load_authorized_faces()
        
        # Inicializar comunicación ESP32
        self.init_esp32()
        
    def init_esp32(self):
        """Inicializar comunicación con ESP32"""
        try:
            self.esp32 = serial.Serial(self.esp32_port, self.esp32_baudrate, timeout=2)
            self.esp32_connected = True
            print(f"Conectado a {self.esp32_port}")
        except serial.SerialException as e:
            print(f"Error conectando a ESP32: {e}")
            self.esp32_connected = False
    
    def send_to_esp32(self, authorized):
        """Enviar señal a ESP32"""
        if self.esp32_connected:
            try:
                signal = b'1' if authorized else b'0'
                self.esp32.write(signal)
                print(f"Señal enviada a ESP32: {'Autorizado' if authorized else 'No autorizado'}")
            except Exception as e:
                print(f"Error enviando a ESP32: {e}")
    
    def load_authorized_faces(self):
        """Cargar rostros autorizados guardados"""
        if os.path.exists(self.encodings_file):
            try:
                with open(self.encodings_file, 'rb') as f:
                    self.authorized_faces = pickle.load(f)
                print(f"Cargados {len(self.authorized_faces)} rostros autorizados")
                
                # Entrenar el reconocedor
                if self.authorized_faces:
                    faces = []
                    labels = []
                    label_map = {}
                    
                    for idx, (name, encodings) in enumerate(self.authorized_faces.items()):
                        label_map[idx] = name
                        for encoding in encodings:
                            faces.append(encoding)
                            labels.append(idx)
                    
                    if faces:
                        self.recognizer.train(faces, np.array(labels))
                        self.label_map = label_map
                        
            except Exception as e:
                print(f"Error cargando rostros: {e}")
                self.authorized_faces = {}
    
    def save_authorized_faces(self):
        """Guardar rostros autorizados"""
        try:
            with open(self.encodings_file, 'wb') as f:
                pickle.dump(self.authorized_faces, f)
            print("Rostros autorizados guardados")
        except Exception as e:
            print(f"Error guardando rostros: {e}")
    
    def register_face(self, name, face_images):
        """Registrar nuevo rostro autorizado"""
        if name not in self.authorized_faces:
            self.authorized_faces[name] = []
        
        # Procesar imágenes de rostro
        for face_img in face_images:
            if face_img is not None and face_img.size > 0:
                # Convertir a escala de grises y normalizar
                gray_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
                gray_face = cv2.equalizeHist(gray_face)
                gray_face = cv2.resize(gray_face, (100, 100))
                
                self.authorized_faces[name].append(gray_face)
        
        # Guardar y reentrenar
        self.save_authorized_faces()
        self.train_recognizer()
        print(f"Rostro de '{name}' registrado con {len(face_images)} imágenes")
    
    def train_recognizer(self):
        """Entrenar el reconocedor de rostros"""
        if not self.authorized_faces:
            return False
        
        faces = []
        labels = []
        self.label_map = {}
        
        for idx, (name, encodings) in enumerate(self.authorized_faces.items()):
            self.label_map[idx] = name
            for encoding in encodings:
                faces.append(encoding)
                labels.append(idx)
        
        if faces:
            self.recognizer.train(faces, np.array(labels))
            return True
        return False
    
    def detect_faces(self, frame):
        """Detectar rostros en el frame con parámetros optimizados"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        # Aplicar suavizado para reducir ruido
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Detectar rostros con parámetros más estrictos
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.05,
            minNeighbors=8,
            minSize=(50, 50),
            maxSize=(400, 400),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Filtrar detecciones adicionales
        filtered_faces = []
        for (x, y, w, h) in faces:
            aspect_ratio = w / h
            if 0.7 <= aspect_ratio <= 1.4:
                filtered_faces.append((x, y, w, h))
        
        return filtered_faces, gray
    
    def recognize_faces(self, faces, gray):
        """Reconocer rostros detectados con estabilización"""
        recognized_names = []
        authorized_detected = False
        current_detection = []
        
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            roi_gray = cv2.resize(roi_gray, (100, 100))
            
            # Intentar reconocer
            if hasattr(self, 'label_map') and self.label_map:
                try:
                    label, confidence = self.recognizer.predict(roi_gray)
                    
                    if confidence < 80:
                        name = self.label_map.get(label, "Desconocido")
                        if name != "Desconocido":
                            authorized_detected = True
                            current_detection.append(True)
                        else:
                            current_detection.append(False)
                    else:
                        name = "Desconocido"
                        current_detection.append(False)
                except:
                    name = "Desconocido"
                    current_detection.append(False)
            else:
                name = "Desconocido"
                current_detection.append(False)
            
            recognized_names.append((x, y, w, h, name))
        
        # Sistema de estabilización
        self.detection_history.append(current_detection)
        if len(self.detection_history) > self.max_history:
            self.detection_history.pop(0)
        
        # Determinar detección estable
        if len(self.detection_history) >= 3:
            recent_detections = self.detection_history[-3:]
            if recent_detections:
                avg_confidence = sum(any(detection) for detection in recent_detections) / len(recent_detections)
                authorized_detected = avg_confidence >= self.detection_threshold
        
        return recognized_names, authorized_detected
    
    def draw_results(self, frame, faces_info):
        """Dibujar resultados en el frame"""
        for (x, y, w, h, name) in faces_info:
            # Color según si está autorizado
            if name == "Desconocido":
                color = (0, 0, 255)
            else:
                color = (0, 255, 0)
            
            # Dibujar rectángulo
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            # Dibujar nombre
            cv2.putText(frame, name, (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        return frame
    
    def capture_registration_images(self, name, num_images=10):
        """Capturar imágenes para registro de nuevo rostro"""
        cap = cv2.VideoCapture(0)
        captured_images = []
        
        print(f"Registrando rostro para '{name}'. Capturando {num_images} imágenes...")
        print("Mira a la cámara y mueve ligeramente tu cabeza para diferentes ángulos.")
        
        count = 0
        while count < num_images:
            ret, frame = cap.read()
            if not ret:
                continue
            
            faces, gray = self.detect_faces(frame)
            
            # Mostrar frame con detecciones
            display_frame = frame.copy()
            for (x, y, w, h) in faces:
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            cv2.putText(display_frame, f"Capturando: {count}/{num_images}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Registro de Rostro', display_frame)
            
            # Capturar rostro si se detecta uno
            if len(faces) > 0:
                face_img = frame[y:y+h, x:x+w]
                captured_images.append(face_img)
                count += 1
                time.sleep(0.5)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        return captured_images
    
    def run_detection(self):
        """Ejecutar detección en tiempo real"""
        cap = cv2.VideoCapture(0)
        
        print("Sistema de detección de rostros iniciado")
        print("Presiona 'r' para registrar nuevo rostro")
        print("Presiona 'q' para salir")
        
        last_esp32_signal = 0
        signal_cooldown = 2
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Detectar rostros
            faces, gray = self.detect_faces(frame)
            
            # Reconocer rostros
            faces_info, authorized = self.recognize_faces(faces, gray)
            
            # Dibujar resultados
            frame = self.draw_results(frame, faces_info)
            
            # Enviar señal a ESP32 si hay rostro autorizado
            current_time = time.time()
            if authorized and (current_time - last_esp32_signal > signal_cooldown):
                self.send_to_esp32(True)
                last_esp32_signal = current_time
            elif not authorized and faces_info and (current_time - last_esp32_signal > signal_cooldown):
                self.send_to_esp32(False)
                last_esp32_signal = current_time
            
            # Mostrar información
            status = "AUTORIZADO" if authorized else ("DETECTADO" if faces_info else "SIN DETECCIÓN")
            color = (0, 255, 0) if authorized else ((0, 255, 255) if faces_info else (0, 0, 255))
            
            cv2.putText(frame, f"Estado: {status}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            cv2.putText(frame, f"Rostros: {len(faces_info)}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.putText(frame, "Presiona 'r' para registrar | 'q' para salir", 
                       (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow('Detector de Rostros', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                # Registrar nuevo rostro
                name = input("Ingrese el nombre de la persona: ")
                if name.strip():
                    images = self.capture_registration_images(name)
                    if images:
                        self.register_face(name, images)
                        print(f"Rostro de '{name}' registrado exitosamente")
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Cerrar conexión ESP32
        if self.esp32_connected:
            self.esp32.close()

def main():
    detector = FaceDetector()
    
    while True:
        print("\n=== Sistema de Detección de Rostros ===")
        print("1. Iniciar detección en tiempo real")
        print("2. Registrar nuevo rostro autorizado")
        print("3. Ver rostros autorizados")
        print("4. Salir")
        
        option = input("Seleccione una opción: ")
        
        if option == '1':
            detector.run_detection()
        elif option == '2':
            name = input("Ingrese el nombre de la persona: ")
            if name.strip():
                images = detector.capture_registration_images(name)
                if images:
                    detector.register_face(name, images)
                    print(f"Rostro de '{name}' registrado exitosamente")
        elif option == '3':
            if detector.authorized_faces:
                print("\nRostros autorizados:")
                for name, encodings in detector.authorized_faces.items():
                    print(f"- {name}: {len(encodings)} imágenes")
            else:
                print("No hay rostros autorizados registrados")
        elif option == '4':
            break
        else:
            print("Opción no válida")

if __name__ == "__main__":
    main()