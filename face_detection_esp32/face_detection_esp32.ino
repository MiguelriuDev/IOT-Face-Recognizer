bool recogniced_user = false;
int PIN_LED = 2;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    recogniced_user = Serial.read() == '1';

    Serial.println(recogniced_user);

    if (recogniced_user)
    {
      digitalWrite(PIN_LED, HIGH);
    }
    else
    {
      digitalWrite(PIN_LED, LOW);
    }
  }
}
