/*
 * LevvDeck — ESP32 macropad / stream deck firmware
 * ------------------------------------------------------------------------
 * Hardware: ESP32-WROOM-32 DevKitC, 3x3 Cherry MX matrix (COL2ROW),
 *           2x EC11 rotary encoders w/ push, 0.96" SSD1306 OLED (I2C),
 *           2x WS2812B addressable LEDs.
 *
 *  >>> PINOUT BELOW IS THE SAME SOURCE OF TRUTH AS gen_netlist.py <<<
 *  If you change a GPIO here, change PINOUT in gen_netlist.py to match,
 *  regenerate levvdeck.net, and re-run the board pipeline. They must
 *  never diverge.
 *
 * Matrix wiring (COL2ROW): SWx.pad1 -> COLn ; SWx.pad2 -> Dx anode ;
 *                          Dx cathode -> ROWn. Diode conducts COL -> ROW,
 *                          so we drive a column HIGH and read rows that are
 *                          held LOW by pulldowns (HIGH == pressed).
 *
 * Libraries (install via Arduino Library Manager / PlatformIO):
 *   - Adafruit GFX, Adafruit SSD1306
 *   - Adafruit NeoPixel
 * Transport to the host (USB-serial here) is a placeholder: swap sendEvent()
 * for BLE-Keyboard / HID as needed.
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_NeoPixel.h>

// ===================== LOCKED PINOUT (mirror of gen_netlist.py) ===========
// I2C / OLED
#define PIN_I2C_SDA   21
#define PIN_I2C_SCL   22

// Matrix rows / columns
#define PIN_ROW0      13
#define PIN_ROW1      14
#define PIN_ROW2      27
#define PIN_COL0      26
#define PIN_COL1      25
#define PIN_COL2      33

// Encoder 1
#define PIN_ENC1_A    16
#define PIN_ENC1_B    17
#define PIN_ENC1_SW    4

// Encoder 2
#define PIN_ENC2_A    32
#define PIN_ENC2_B    18
#define PIN_ENC2_SW   19

// WS2812 data
#define PIN_WS2812    23
// ==========================================================================

#define NUM_WS2812    2
#define OLED_W        128
#define OLED_H        64
#define OLED_ADDR     0x3C

static const uint8_t ROWS[3] = { PIN_ROW0, PIN_ROW1, PIN_ROW2 };
static const uint8_t COLS[3] = { PIN_COL0, PIN_COL1, PIN_COL2 };

// Logical key numbers (1..9) laid out per the physical matrix.
static const uint8_t KEYMAP[3][3] = {
  { 1, 2, 3 },   // ROW0 x COL0,COL1,COL2
  { 4, 5, 6 },   // ROW1
  { 7, 8, 9 },   // ROW2
};

Adafruit_SSD1306 oled(OLED_W, OLED_H, &Wire, -1);
Adafruit_NeoPixel pixels(NUM_WS2812, PIN_WS2812, NEO_GRB + NEO_KHZ800);

// Debounced key state
bool keyState[3][3] = { { false } };

// Encoder state
struct Encoder {
  uint8_t pinA, pinB, pinSw;
  uint8_t lastAB;
  long position;
  bool lastSw;
};
Encoder enc1 = { PIN_ENC1_A, PIN_ENC1_B, PIN_ENC1_SW, 0, 0, true };
Encoder enc2 = { PIN_ENC2_A, PIN_ENC2_B, PIN_ENC2_SW, 0, 0, true };

// ------------------------------------------------------------------ helpers
void sendEvent(const char *what) {
  // Placeholder transport. Replace with BLE-Keyboard / USB-HID as needed.
  Serial.println(what);
}

void setupMatrix() {
  for (uint8_t c = 0; c < 3; c++) {
    pinMode(COLS[c], OUTPUT);
    digitalWrite(COLS[c], LOW);
  }
  for (uint8_t r = 0; r < 3; r++) {
    pinMode(ROWS[r], INPUT_PULLDOWN);   // idle LOW; diode pulls HIGH when pressed
  }
}

void scanMatrix() {
  char buf[24];
  for (uint8_t c = 0; c < 3; c++) {
    digitalWrite(COLS[c], HIGH);        // drive this column
    delayMicroseconds(30);
    for (uint8_t r = 0; r < 3; r++) {
      bool pressed = digitalRead(ROWS[r]) == HIGH;
      if (pressed != keyState[r][c]) {
        keyState[r][c] = pressed;
        snprintf(buf, sizeof(buf), "KEY %u %s",
                 KEYMAP[r][c], pressed ? "DOWN" : "UP");
        sendEvent(buf);
      }
    }
    digitalWrite(COLS[c], LOW);
  }
}

void setupEncoder(Encoder &e) {
  pinMode(e.pinA, INPUT_PULLUP);
  pinMode(e.pinB, INPUT_PULLUP);
  pinMode(e.pinSw, INPUT_PULLUP);
  e.lastAB = (digitalRead(e.pinA) << 1) | digitalRead(e.pinB);
}

void scanEncoder(Encoder &e, const char *name) {
  // Gray-code quadrature decode.
  static const int8_t table[16] = {
     0, -1,  1,  0,  1,  0,  0, -1,
    -1,  0,  0,  1,  0,  1, -1,  0
  };
  uint8_t ab = (digitalRead(e.pinA) << 1) | digitalRead(e.pinB);
  int8_t delta = table[(e.lastAB << 2) | ab];
  e.lastAB = ab;
  if (delta != 0) {
    e.position += delta;
    if ((e.position & 1) == 0) {          // one detent = 2 transitions
      char buf[24];
      snprintf(buf, sizeof(buf), "%s %s", name, delta > 0 ? "CW" : "CCW");
      sendEvent(buf);
    }
  }
  bool sw = digitalRead(e.pinSw) == LOW;  // active low (other side = GND)
  if (sw != !e.lastSw) {                  // edge detect
    // (kept simple; real debounce omitted for clarity)
  }
  static_cast<void>(sw);
}

void encoderButton(Encoder &e, const char *name) {
  bool sw = digitalRead(e.pinSw) == LOW;
  if (sw != !e.lastSw) {
    e.lastSw = !sw;
    char buf[24];
    snprintf(buf, sizeof(buf), "%s_SW %s", name, sw ? "DOWN" : "UP");
    sendEvent(buf);
  }
}

void drawOled(const char *line) {
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(0, 0);
  oled.println("LevvDeck");
  oled.setCursor(0, 16);
  oled.println(line);
  oled.display();
}

// --------------------------------------------------------------------- main
void setup() {
  Serial.begin(115200);
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);

  pixels.begin();
  pixels.setBrightness(40);
  pixels.clear();
  pixels.show();

  if (oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    drawOled("ready");
  }

  setupMatrix();
  setupEncoder(enc1);
  setupEncoder(enc2);

  sendEvent("LevvDeck online");
}

void loop() {
  scanMatrix();
  scanEncoder(enc1, "ENC1");
  scanEncoder(enc2, "ENC2");
  encoderButton(enc1, "ENC1");
  encoderButton(enc2, "ENC2");

  // Simple heartbeat color on the WS2812 chain.
  static uint32_t t = 0;
  if (millis() - t > 1000) {
    t = millis();
    static uint8_t hue = 0;
    hue += 8;
    for (uint16_t i = 0; i < NUM_WS2812; i++) {
      pixels.setPixelColor(i, pixels.ColorHSV((hue + i * 90) << 8));
    }
    pixels.show();
  }

  delay(2);
}
