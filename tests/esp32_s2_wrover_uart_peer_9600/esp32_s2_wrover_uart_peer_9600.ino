// E4 dedicated 9600-baud variant. Separate sketch from 115200 E1-E3 peer.
// Only flashed to detached ESP32-S2-WROVER via its own USB-C port.
// LabMate v1.8: external UART peer for the official ESP32-S2-WROVER
// Flipper Wi-Fi Developer Board. TEST SKETCH ONLY: uploading overwrites
// the existing Blackmagic/Marauder firmware on the ESP32.
// Wiring is already on the official board's Flipper header:
// Flipper USART TX13 -> ESP32-S2 GPIO44 (RX)
// ESP32-S2 GPIO43 (TX) -> Flipper USART RX14, common GND.
// Select "ESP32S2 Dev Module", "USB CDC On Boot: Enabled",
// "Upload Mode: Internal USB" in Arduino IDE (as supported by core).
// The USB Serial Monitor is separate from the hardware UART under test.
#include <Arduino.h>
#include <string.h>

static constexpr int UART_RX_GPIO = 44;
static constexpr int UART_TX_GPIO = 43;
static constexpr size_t UART_LINE_CAP = 31;
static HardwareSerial peer(1); // ESP32-S2 UART1; GPIO matrix maps it to 44/43.
static uint32_t currentBaud = 9600;
static uint32_t lastReady = 0;
static char peerLine[UART_LINE_CAP + 1] = {};
static size_t peerLen = 0;
static char usbLine[16] = {};
static size_t usbLen = 0;

static void sendReady() {
    peer.print("ESP32_READY\r\n");
    lastReady = millis();
}

static void configurePeer(uint32_t baud) {
    peer.flush();
    peer.end();
    currentBaud = baud;
    peerLen = 0;
    peer.begin(currentBaud, SERIAL_8N1, UART_RX_GPIO, UART_TX_GPIO);
    Serial.printf("Peer UART: %lu 8N1 RX=44 TX=43\n", (unsigned long)currentBaud);
    sendReady();
}

static void onPeerByte(char ch) {
    if(ch == '\r') return;
    if(ch == '\n') {
        if(peerLen == 0) return;
        peerLine[peerLen] = '\0';
        Serial.print("ESP32 RX <- Flipper: ");
        Serial.println(peerLine);
        if(strcmp(peerLine, "AT") == 0) {
            peer.print("ESP32_OK\r\n");
            Serial.println("ESP32 TX -> Flipper: ESP32_OK");
        }
        peerLen = 0;
        return;
    }
    if(ch < 32 || ch > 126) return;
    if(peerLen == UART_LINE_CAP) {
        peerLen = 0;
        peer.print("ESP32_OVERFLOW\r\n");
        return;
    }
    peerLine[peerLen++] = ch;
}

static void onUsbCommand() {
    usbLine[usbLen] = '\0';
    if(strcmp(usbLine, "9600") == 0) configurePeer(9600);
    else if(strcmp(usbLine, "38400") == 0) configurePeer(38400);
    else if(strcmp(usbLine, "115200") == 0) configurePeer(115200);
    else if(strcmp(usbLine, "READY") == 0) sendReady();
    else if(usbLen) Serial.println("USB command: 9600 / 38400 / 115200 / READY");
    usbLen = 0;
}

void setup() {
    Serial.begin(115200); // Native USB CDC, if enabled in Arduino Tools.
    peer.begin(currentBaud, SERIAL_8N1, UART_RX_GPIO, UART_TX_GPIO);
    lastReady = millis();
    Serial.println("LabMate ESP32-S2 external UART peer (default 9600 8N1)");
    Serial.println("USB commands: 9600 / 38400 / 115200 / READY");
}

void loop() {
    while(peer.available()) onPeerByte((char)peer.read());
    while(Serial.available()) {
        const char ch = (char)Serial.read();
        if(ch == '\r') continue;
        if(ch == '\n') onUsbCommand();
        else if(usbLen + 1U < sizeof(usbLine)) usbLine[usbLen++] = ch;
        else usbLen = 0;
    }
    // Slow, bounded, recognizable test traffic. No network operations.
    if((uint32_t)(millis() - lastReady) >= 3000U) sendReady();
}
