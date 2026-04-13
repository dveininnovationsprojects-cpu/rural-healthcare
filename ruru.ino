#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <MPU6050.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <LiquidCrystal_I2C.h> 
#include <math.h>
#include <ArduinoJson.h>

/* ==========================================================================
 * 1. HARDWARE & NETWORK CONFIGURATION
 * ========================================================================== */
const char* ssid = "DV030";
const char* password = "Dvein@012";

// Make sure your laptop IP is still 192.168.1.2 
const char* backendURL = "http://192.168.1.46:5000/api/v1/patient/telemetry/ingest";
const String NODE_ID = "P001"; // Must match your Patient UI

/* ==========================================================================
 * 2. PIN DEFINITIONS & SENSOR OBJECTS
 * ========================================================================== */
// I2C LCD Display (Address 0x27, 16 columns, 2 rows)
LiquidCrystal_I2C lcd(0x27, 16, 2); 

// MPU6050
MPU6050 mpu;

// Temperature Sensor (DS18B20)
#define ONE_WIRE_BUS 4
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// Indicators
#define BUZZER_PIN 15
#define GREEN_LED 23
#define RED_LED   18

/* ==========================================================================
 * 3. SYSTEM VARIABLES & NEW THRESHOLDS 🔥
 * ========================================================================== */
float fallUpperLimit = 1.30; // UPDATED: Very sensitive fall detection
float tempLimit = 33.2;      // UPDATED: Custom Fever/Crisis threshold

float currentTemp = 31.5;    // Base ambient temp
float currentHR = 75.0;
float currentAccel = 1.0;

bool emergencyActive = false;

// Timers (Non-blocking)
unsigned long lastSensorPoll = 0;
unsigned long lastBackendUpdate = 0;
const unsigned long sensorPollInterval = 100; // Poll sensors every 100ms
unsigned long backendInterval = 3000;         // Send to backend every 3 seconds

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  
  // LED & Buzzer Init
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);

  // LCD Init
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Energy aware...");
  lcd.setCursor(0, 1);
  lcd.print("WiFi Connecting");

  // Sensor Init
  mpu.initialize();
  sensors.begin();

  // WiFi Connection
  WiFi.begin(ssid, password);
  int retry = 0;
  while(WiFi.status() != WL_CONNECTED && retry < 30) {
    delay(500);
    Serial.print(".");
    retry++;
  }

  if(WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected!");
    Serial.println(WiFi.localIP());
    
    // Update LCD with IP
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Connected!");
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP().toString());
    delay(2000); // Pause to read IP on screen
  } else {
    Serial.println("\nWiFi Connection Failed!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Failed!");
  }
}

void loop() {
  unsigned long currentMillis = millis();

  // Reconnect WiFi if dropped
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, HIGH);
    WiFi.reconnect();
  }

  // ---------------------------------------------------------
  // FAST POLLING: READ SENSORS (Every 100ms)
  // ---------------------------------------------------------
  if (currentMillis - lastSensorPoll >= sensorPollInterval) {
    lastSensorPoll = currentMillis;

    // Read Acceleration (MPU6050)
    int16_t ax, ay, az;
    mpu.getAcceleration(&ax, &ay, &az);
    float Ax = ax / 16384.0;
    float Ay = ay / 16384.0;
    float Az = az / 16384.0;
    
    // Calculate total G-force vector
    currentAccel = sqrt(Ax*Ax + Ay*Ay + Az*Az);

    // Read Temperature
    sensors.requestTemperatures();
    float t = sensors.getTempCByIndex(0);
    if (t > -10 && t < 85) { 
      currentTemp = t; // Basic filter for bad readings
    }

    // 🔥 VIRTUAL HEART RATE LOGIC (Adjusted to new temp limit) 🔥
    if (currentTemp > tempLimit) {
      // Temp thaanduna HR 100+ thandum
      currentHR =  + random(-2, 3); 
    } else {
      currentHR = 100 + ((currentTemp - tempLimit) * 15.0)+ random(-3, 4); // Normal resting HR
    }

    // Local Emergency Detection (Based on new limits)
    if (currentAccel > fallUpperLimit || currentTemp >= tempLimit) {
      emergencyActive = true;
    } else {
      emergencyActive = false;
    }

    // Hardware Feedback Loop
    handleAlerts();
  }

  // ---------------------------------------------------------
  // SLOW POLLING: UPDATE BACKEND & LCD (Every 3 seconds)
  // ---------------------------------------------------------
  if (currentMillis - lastBackendUpdate >= backendInterval) {
    lastBackendUpdate = currentMillis;
    
    sendToZhopingoBackend();
    updateLCD(); 
  }
}

/* ==========================================================================
 * HARDWARE ALERT CONTROLLER
 * ========================================================================== */
void handleAlerts() {
  if (emergencyActive) {
    digitalWrite(RED_LED, HIGH);
    digitalWrite(GREEN_LED, LOW);
    
    // Pulsating Buzzer Logic (Non-blocking)
    static unsigned long lastBuzz = 0;
    if(millis() - lastBuzz > 200) {
      digitalWrite(BUZZER_PIN, !digitalRead(BUZZER_PIN));
      lastBuzz = millis();
    }
  } else {
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(RED_LED, LOW);
    digitalWrite(BUZZER_PIN, LOW); // Silence
  }
}

/* ==========================================================================
 * HTTP POST TO ZHOPINGO API
 * ========================================================================== */
void sendToZhopingoBackend() {
  if(WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(backendURL);
    http.addHeader("Content-Type", "application/json");

    // Constructing JSON Payload required by Zhopingo Backend
    StaticJsonDocument<200> doc;
    doc["node_id"] = NODE_ID;
    doc["temp"] = currentTemp;
    doc["hr"] = currentHR;
    doc["accel"] = currentAccel;

    String jsonPayload;
    serializeJson(doc, jsonPayload);
    
    Serial.print("Sending: ");
    Serial.println(jsonPayload);

    int httpResponseCode = http.POST(jsonPayload);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.print("Backend Response: ");
      Serial.println(response);
      
      // Parse Backend AI Command (Optional sync)
      StaticJsonDocument<200> resDoc;
      if (!deserializeJson(resDoc, response)) {
        String hwCommand = resDoc["hardware_command"];
        if (hwCommand == "TRIGGER_ALARM") {
          emergencyActive = true; // Let backend force emergency state
        }
      }
    } else {
      Serial.print("HTTP POST Failed, Error Code: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  }
}

/* ==========================================================================
 * LCD DISPLAY RENDERER (Clean 16x2 Formatting)
 * ========================================================================== */
void updateLCD() {
  // We format strings to exactly 16 characters so we don't need lcd.clear()
  // This prevents screen flickering!
  
  // Format Row 1: Temp & HR
  String line1 = "T:" + String(currentTemp, 1) + "C HR:" + String((int)currentHR) + "   ";
  lcd.setCursor(0, 0);
  lcd.print(line1.substring(0, 16)); 

  // Format Row 2: Accel & Status
  String statusMsg = emergencyActive ? "CRISIS!" : "STABLE ";
  String line2 = "A:" + String(currentAccel, 1) + "G " + statusMsg + "     ";
  lcd.setCursor(0, 1);
  lcd.print(line2.substring(0, 16));
}