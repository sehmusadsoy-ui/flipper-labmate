// LabMate v1.8 ST2 external 115200 baud RX-load fixture.
// Independent of the working 9600-baud and 115200-baud interoperability sketches.
// ESP32-S2-WROVER OFFICIAL Flipper Wi-Fi Developer Board only.
// Flash via standalone board USB-C after removing board from Flipper.
// Never attach the board to Flipper while also powered via USB-C without
// separately verified power isolation. No GPIO jumper or 5V wiring needed.
//
// Flipper UART TX13 -> ESP32 GPIO44 RX, Flipper RX14 <- ESP32 GPIO43 TX.
// With LabMate UART at 115200 8N1: ESP32_READY sent every ~3 seconds.
// Explicit TX "AT\r\n" returns ESP32_OK, arms one bounded load event.
// After 1200ms, the ESP sends <=20480 ASCII bytes over <=2500ms.
// No repeated load without another explicit AT. Not guaranteed to overflow
// the Flipper's 256B RX queue: this is a live sustained-load test, not DROP proof.
#include <Arduino.h>
#include <string.h>

static constexpr int UART_RX_GPIO = 44;
static constexpr int UART_TX_GPIO = 43;
static constexpr uint32_t UART_BAUD = 115200U;
static constexpr uint32_t READY_PERIOD_MS = 3000U;
static constexpr uint32_t ARM_DELAY_MS = 1200U;
static constexpr uint32_t BURST_MAX_DURATION_MS = 2500U;
static constexpr size_t BURST_MAX_BYTES = 20480U;
static constexpr size_t UART_LINE_CAP = 31U;
static constexpr char BURST_PATTERN[] = "0123456789ABCDEF0123456789ABCDEF";
static_assert(sizeof(BURST_PATTERN) - 1U == 32U, "Expected 32-byte ASCII pattern");

static HardwareSerial peer(1); // Real 3.3 V UART1 on GPIO44/43; not USB CDC.
static char inputLine[UART_LINE_CAP + 1U] = {};
static size_t inputLen = 0U;
static uint32_t lastReady = 0U;
static uint32_t armAt = 0U;
static uint32_t burstAt = 0U;
static size_t burstBytesQueued = 0U;

enum class StressState : uint8_t {
    Idle,
    Armed,
    Sending,
};
static StressState state = StressState::Idle;

static void sendReady() {
    peer.print("ESP32_READY\r\n");
    lastReady = millis();
}

static void handleLine() {
    inputLine[inputLen] = '\0';
    if(strcmp(inputLine, "AT") == 0) {
        if(state == StressState::Idle) {
            peer.print("ESP32_OK\r\nSTRESS_ARMED\r\n");
            state = StressState::Armed;
            armAt = millis();
        } else {
            peer.print("STRESS_BUSY\r\n"); // Existing bounded job is not retriggered.
        }
    }
    inputLen = 0U;
}

static void receiveFromFlipper() {
    while(peer.available()) {
        const char ch = static_cast<char>(peer.read());
        if(ch == '\r') continue;
        if(ch == '\n') {
            if(inputLen) handleLine();
            continue;
        }
        if(ch < 32 || ch > 126) continue;
        if(inputLen >= UART_LINE_CAP) {
            inputLen = 0U; // Ignore excessively long command; never overflow.
            continue;
        }
        inputLine[inputLen++] = ch;
    }
}

static void updateStress() {
    const uint32_t now = millis();
    if(state == StressState::Armed) {
        if((uint32_t)(now - armAt) < ARM_DELAY_MS) return;
        peer.print("BURST_BEGIN\r\n");
        burstBytesQueued = 0U;
        burstAt = now;
        state = StressState::Sending;
    }

    if(state == StressState::Sending) {
        // Bounded work per Arduino loop: TX backpressure is respected.
        uint8_t blocks = 0U;
        while(burstBytesQueued + 32U <= BURST_MAX_BYTES &&
              peer.availableForWrite() >= 32 &&
              blocks < 2U &&
              (uint32_t)(millis() - burstAt) < BURST_MAX_DURATION_MS) {
            const size_t written =
                peer.write(reinterpret_cast<const uint8_t*>(BURST_PATTERN), 32U);
            if(written != 32U) break;
            burstBytesQueued += written;
            blocks++;
        }
        if(burstBytesQueued >= BURST_MAX_BYTES ||
           (uint32_t)(millis() - burstAt) >= BURST_MAX_DURATION_MS) {
            peer.print("\r\nBURST_END\r\n");
            state = StressState::Idle;
            lastReady = millis();
        }
    }
}

void setup() {
    Serial.begin(115200); // USB CDC debug only, not required for on-Flipper tests.
    peer.begin(UART_BAUD, SERIAL_8N1, UART_RX_GPIO, UART_TX_GPIO);
    lastReady = millis();
    Serial.println("LabMate ST2 ESP32-S2 115200 peer. 1x bounded load on AT.");
}

void loop() {
    receiveFromFlipper();
    updateStress();
    if(state == StressState::Idle &&
       (uint32_t)(millis() - lastReady) >= READY_PERIOD_MS) {
        sendReady();
    }
}
