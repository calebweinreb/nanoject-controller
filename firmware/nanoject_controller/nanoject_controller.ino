// nanoject_controller.ino
//
// Serial-controlled TTL pulse generator for Arduino-compatible boards
// (Arduino Uno/Mega/Nano, Teensy, etc.).
//
// Protocol (newline-terminated, ASCII):
//   Host -> MCU:
//     START <num_pulses> <interval_ms>   begin a pulse sequence
//     STOP                               interrupt a running sequence
//     TEST                               emit a single pulse
//     PING                               health check
//   MCU -> Host:
//     READY                              sent once at boot
//     OK                                 generic ack
//     PULSE <n>                          emitted after each pulse (1-indexed)
//     DONE                               sequence completed
//     STOPPED                            sequence interrupted
//     ERR <msg>                          parse / param error

// ====== Adjust these in source ======
const int  OUTPUT_PIN     = 18;     // primary TTL output pin
const int  AUX_PINS[]     = {3, 7}; // additional pins held HIGH during each pulse
const int  PULSE_WIDTH_MS = 100;    // pulse duration (ms)
const long BAUD           = 115200;
// ====================================

const int N_AUX_PINS = sizeof(AUX_PINS) / sizeof(AUX_PINS[0]);

bool          running         = false;
unsigned long next_pulse_ms   = 0;
long          pulses_total    = 0;
long          pulses_emitted  = 0;
unsigned long interval_ms     = 0;

void emitPulse() {
  digitalWrite(OUTPUT_PIN, HIGH);
  for (int i = 0; i < N_AUX_PINS; i++) digitalWrite(AUX_PINS[i], HIGH);
  delay(PULSE_WIDTH_MS);
  digitalWrite(OUTPUT_PIN, LOW);
  for (int i = 0; i < N_AUX_PINS; i++) digitalWrite(AUX_PINS[i], LOW);
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.startsWith("START")) {
    int sp1 = cmd.indexOf(' ');
    int sp2 = (sp1 >= 0) ? cmd.indexOf(' ', sp1 + 1) : -1;
    if (sp1 < 0 || sp2 < 0) {
      Serial.println("ERR bad START");
      return;
    }
    long n = cmd.substring(sp1 + 1, sp2).toInt();
    long iv = cmd.substring(sp2 + 1).toInt();
    if (n <= 0 || iv <= 0) {
      Serial.println("ERR bad params");
      return;
    }
    pulses_total   = n;
    interval_ms    = (unsigned long)iv;
    pulses_emitted = 0;
    running        = true;
    next_pulse_ms  = millis();   // first pulse fires immediately
    Serial.println("OK");
  }
  else if (cmd == "STOP") {
    if (running) {
      running = false;
      Serial.println("STOPPED");
    } else {
      Serial.println("OK");
    }
  }
  else if (cmd == "TEST") {
    emitPulse();
    Serial.println("OK");
  }
  else if (cmd == "PING") {
    Serial.println("OK");
  }
  else {
    Serial.print("ERR unknown: ");
    Serial.println(cmd);
  }
}

void setup() {
  pinMode(OUTPUT_PIN, OUTPUT);
  digitalWrite(OUTPUT_PIN, LOW);
  for (int i = 0; i < N_AUX_PINS; i++) {
    pinMode(AUX_PINS[i], OUTPUT);
    digitalWrite(AUX_PINS[i], LOW);
  }
  Serial.begin(BAUD);
  // Some boards need a moment for the USB serial to come up.
  unsigned long t0 = millis();
  while (!Serial && (millis() - t0) < 3000) { /* wait briefly */ }
  Serial.println("READY");
}

void loop() {
  static String buf = "";
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      handleCommand(buf);
      buf = "";
    } else if (c != '\r') {
      buf += c;
      if (buf.length() > 64) buf = "";  // overflow guard
    }
  }

  if (running) {
    unsigned long now = millis();
    if ((long)(now - next_pulse_ms) >= 0) {
      emitPulse();
      pulses_emitted++;
      Serial.print("PULSE ");
      Serial.println(pulses_emitted);
      if (pulses_emitted >= pulses_total) {
        running = false;
        Serial.println("DONE");
      } else {
        next_pulse_ms += interval_ms;
      }
    }
  }
}
