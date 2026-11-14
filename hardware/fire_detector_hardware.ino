
#include <DHT.h>

// Pins
#define DHTPIN 2
#define DHTTYPE DHT11
#define LDR_PIN A0
#define BUZZER 7
#define GREEN_LED 8
#define RED_LED 9
#define YELLOW_LED 10

// Node name sent in the JSON
const char* NODE_ID = "01";

// Settings: tune these for your room
const float TEMP_LIMIT = 35.0;   // alarm at or above this (°C)
const float TEMP_WARN  = 32.0;   // warning at or above this (°C)
const float RISE_LIMIT = 2.0;    // warning if temp rises this much in ~10 s
const int   LIGHT_LIMIT = 800;   // alarm at or above this (0-1023, higher = brighter)
const int   READ_INTERVAL = 2000; // ms between readings (keep 1000 or more)

// Last 5 temperature readings (5 x 2 s = about 10 s)
const int HISTORY = 5;
float tempHistory[HISTORY];
int historyIndex = 0;
bool historyReady = false;

DHT dht(DHTPIN, DHTTYPE);

void setLights(bool green, bool yellow, bool red) {
  digitalWrite(GREEN_LED, green ? HIGH : LOW);
  digitalWrite(YELLOW_LED, yellow ? HIGH : LOW);
  digitalWrite(RED_LED, red ? HIGH : LOW);
}

void setup() {
  Serial.begin(9600);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  dht.begin();
}

void loop() {
  float temp = dht.readTemperature();   // Celsius
  int light = analogRead(LDR_PIN);

  // Sensor fault: yellow light, no buzzer, error line
  if (isnan(temp)) {
    setLights(false, true, false);
    noTone(BUZZER);
    Serial.println("{\"error\":\"dht\"}");
    delay(READ_INTERVAL);
    return;
  }

  // Rate of rise: compare with the reading from about 10 s ago
  if (!historyReady) {
    for (int i = 0; i < HISTORY; i++) tempHistory[i] = temp;
    historyReady = true;
  }
  float rise = temp - tempHistory[historyIndex];
  tempHistory[historyIndex] = temp;
  historyIndex = (historyIndex + 1) % HISTORY;

  // Checks
  bool heatAlarm  = (temp >= TEMP_LIMIT);
  bool lightAlarm = (light >= LIGHT_LIMIT);
  bool heatWarn   = (temp >= TEMP_WARN);
  bool riseWarn   = (rise >= RISE_LIMIT);

  // Decide level and reason
  const char* level;
  const char* reason;
  int hazard = 0;

  if (heatAlarm || lightAlarm) {
    level = "alarm";
    hazard = 1;
    if (heatAlarm && lightAlarm) reason = "both";
    else if (heatAlarm)          reason = "heat";
    else                         reason = "light";
  } else if (riseWarn) {
    level = "warning";
    reason = "rise";
  } else if (heatWarn) {
    level = "warning";
    reason = "heat";
  } else {
    level = "safe";
    reason = "none";
  }

  // Lights and buzzer
  if (hazard) {
    setLights(false, false, true);
    tone(BUZZER, 2000, 500);        // half-second beep each reading
  } else if (level[0] == 'w') {
    setLights(false, true, false);
    noTone(BUZZER);
  } else {
    setLights(true, false, false);
    noTone(BUZZER);
  }

  // Send JSON
  Serial.print("{\"node\":\"");
  Serial.print(NODE_ID);
  Serial.print("\",\"temp\":");
  Serial.print(temp, 1);
  Serial.print(",\"light\":");
  Serial.print(light);
  Serial.print(",\"hazard\":");
  Serial.print(hazard);
  Serial.print(",\"level\":\"");
  Serial.print(level);
  Serial.print("\",\"reason\":\"");
  Serial.print(reason);
  Serial.println("\"}");

  delay(READ_INTERVAL);
}