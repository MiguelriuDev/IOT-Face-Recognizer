#include <LiquidCrystal_I2C.h>
#include <Wire.h>
#include <ESP32Servo.h>

#define sdaPin 13
#define sclPin 14
#define pinServo 15
#define ledRojo 2
#define ledVerde 5

Servo servoMotor;

bool recogniced_user = false;
String usuario = "";
LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {
  Wire.begin(sdaPin, sclPin);
  Serial.begin(115200);
  pinMode(ledRojo, OUTPUT);
  pinMode(ledVerde, OUTPUT);
  lcd.init();
  lcd.backlight();
  lcd.clear();
  servoMotor.setPeriodHertz(50);
  servoMotor.attach(pinServo, 500, 2500);
}

void loop() {
  if (Serial.available() > 0) {
    String receivedData = Serial.readStringUntil('\n');
    receivedData.trim();
    
    int separatorIndex = receivedData.indexOf('|');
    if (separatorIndex != -1) {
      String status = receivedData.substring(0, separatorIndex);
      usuario = receivedData.substring(separatorIndex + 1);
      
      recogniced_user = (status == "true");
      
      Serial.println("Status: " + status + ", User: " + usuario);
      apagarLeds();
      if (recogniced_user)
      {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Bienvenido");
        lcd.setCursor(0, 1);
        lcd.print(usuario);
        delay(500);
        digitalWrite(ledVerde, HIGH);
        digitalWrite(ledRojo, LOW);
        servoMotor.write(180);
      }
      else
      {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("No autorizado");
        delay(500);
        digitalWrite(ledRojo, HIGH);
        digitalWrite(ledVerde, LOW);
        servoMotor.write(0);
      }
    }
  }
}

void apagarLeds()
{
  digitalWrite(ledVerde, LOW);
  digitalWrite(ledRojo, LOW);
}
