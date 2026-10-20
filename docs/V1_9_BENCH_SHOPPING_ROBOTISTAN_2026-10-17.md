# LabMate E11 / v1.9–v2.0 bench purchase shortlist (2026-10-17)

**Vendor preference: one Turkish shop, [Robotistan](https://www.robotistan.com/).**
Links and displayed VAT-inclusive prices below are an October 2026
snapshot only, **not an automated cart, stock reservation or price guarantee**.
Products are not installed/connected by this document. The user already
owns the Flipper Zero, a working ESP32-S2 peer, and a production microSD;
don't repurchase those needlessly.

## Tier A — high-value realistic tests from one vendor

| Qty | Product / link | Approx. price incl. VAT per item | Coverage |
| ---: | --- | ---: | --- |
| 1 | [830-hole breadboard](https://www.robotistan.com/breadboard) | 61 TL | HW-01/04/06/07: isolated 3.3 V prototyping |
| 1 | [M-M 40-wire 20cm Dupont](https://www.robotistan.com/40-pin-ayrilabilen-erkek-erkek-m-m-jumper-kablo-200-mm) | 58 TL | GPIO+sensor+external stimulus |
| 1 | [M-F 40-wire 20cm Dupont](https://www.robotistan.com/40-pin-ayrilabilen-disi-erkek-m-f-jumper-kablo-200-mm) | 56 TL | GPIO+breakout |
| 1 | [F-F 40-wire 20cm Dupont](https://www.robotistan.com/40-pin-ayrilabilen-disi-disi-f-f-jumper-kablo-200-mm) | 48 TL | GPIO+sensor+analyzer |
| 2 | [6x6mm mechanical tactile button](https://www.robotistan.com/4-pinli-push-buton-siyah-6x6x5mm) | 2.19 TL | HW-01 real bounce, not idealized PWM pulses |
| 1 | [4.7k-ohm 1/4W resistors](https://www.robotistan.com/14w-4k7-direnc-paketi-10-adet) | about 0.24 TL listed | HW-07 1-Wire pullup as needed; BME280 pullups depend on module |
| 1 | [BME280 3.3V I2C pressure/temp/humidity module](https://www.robotistan.com/bme280-i2c-presure-temperature-and-humidity-sensor) | 247 TL | HW-06 real I2C3 peripheral ACK; 7-bit 0x76/0x77 depending on SDO |
| 1 | [Mini DS18B20 sensor breakout](https://www.robotistan.com/mini-ds18b20-sicaklik-sensoru-karti) | 72 TL | HW-07 3.3V external VDD-powered, module advertises built-in pullup |
| 1 | [24 MHz 8-channel USB logic analyzer](https://www.robotistan.com/usb-lojik-analizor-24-mhz-8-kanal) | 459 TL | HW-02/04/06/07, serial decode, digital edge and STOP; NOT analog/off voltage measurement |
| 1 | [Dedicated 16 GB microSD test card](https://www.robotistan.com/micro-sd-kart-16gb) | 372 TL | HW-03/05 exception and endurance tests **ONLY**; never sacrifice production card |
| 1 | [125 kHz RFID card](https://www.robotistan.com/125-khz-rfid-kart) | 16 TL | HW-09 LF RFID basic known tag |
| 1 | [13.56 MHz ISO14443A key fob](https://www.robotistan.com/1356mhz-nfc-anahtarlik-s50-1k) | 12 TL | HW-12 NFC basic tests **NOT** ISO15693 test |

**Owner decision — 2026-10-17: DO NOT PURCHASE AN OSCILLOSCOPE.**
Independent PWM duty/period, DC OFF voltage and output accuracy will be
measured with appropriate calibrated/reference equipment at the owner's former
university, **together with an instructor**. This is a **future test plan**,
not hardware already booked or tests already PASS. Record instrument model,
probe attenuation/ground setup, instrument timebase/voltage uncertainty,
3.3 V logic levels, waveform values, STOP/BACK and exact device+FAP
provenance at that visit. The existing 8-channel USB logic analyzer
remains a useful PC-based digital fixture, but does not replace the
university scope for analog OFF-voltage calibration.

**External reference signal generator alternative:** the already-owned ESP32-S2 can produce 3.3 V signals **if its firmware/wiring is independent of LabMate ST2 testing**. Optionally get an extra [Raspberry Pi Pico](https://www.robotistan.com/raspberry-pi-pico) ~250 TL, 3.3V I/O; it allows controlled independent signal timing without altering existing ESP32-S2. Its USB power is separate; join ground only in verified SELV circuits.

## Tier B — do not buy substitutes blindly

| Deferred HW IDs | Required specific hardware | Availability decision |
| --- | --- | --- |
| HW-10/14/19 | Known pinout, 3.3 V **CC1101** board and permitted legal RX test source; TX only if explicitly lawful and independently observed | [Robotistan CC1101 product](https://www.robotistan.com/cc1101-wireless-modul) is shown **OUT OF STOCK** in direct product page. Do not mistake 433MHz simple OOK module or NRF24L01 for an equivalent. |
| HW-11 | Authentic **DS1990A iButton** touch key and contact probe | No exact single-store active listing verified; check genuine type and probe compatibility later |
| HW-15 | Explicit **ISO15693** HF vicinity tag | The linked cheap 13.56 MHz ISO14443A key fob is **not ISO15693**. The [PN5180 module](https://www.robotistan.com/pn5180-nfc-rfid-modul) supports ISO15693, but it is a **reader**, not the tag fixture. Do not buy it as a substitute tag. |
| HW-16 | Safe 3.3 V Wiegand D0/D1 emulator | Could be built using independently verified 3.3 V Pico code and two pins, but requires review before powering or connecting |
| HW-17 | **ICM42688P** SPI breakout with accessible INT/IRQ and verified 3.3 V logic | Exact part not confirmed in vendor results; generic MPU6050/MPU9250 cannot close this test |
| HW-18 | Native JavaScript+NFC/IRQ owners | Mostly software/test sequencing using existing matched E11 firmware; don't purchase hardware prematurely |
| QA-01 | Excel CSV parsing | Excel access or a compatible test environment later, no paid purchase required for immediate GPIO hardware testing |

## 3.3 V and process requirements

- **NEVER connect 5 V / unknown voltage directly to Flipper Zero GPIO**; verify with scope/meter first. USB logic analyzer GND and target GND must be referenced correctly in the same known-safe SELV test setup.
- With BME280, select **3.3 V** power and lines; check module onboard pull-ups before adding any external pullup. The specific I2C3 pin mapping documented by LabMate is PC0 SCL / PC1 SDA; stop other PC1 captures before touching I2C3.
- DS18B20 is externally VDD powered **3.3 V** on PA4; data pullup to 3.3 V only, never 5 V. Some DS18B20 mini breakouts already include an appropriate pull-up; verify before doubling.
- Disconnect all external wires before a firmware change. Do not infer a cable/pin safely routed by its printed color alone; inspect pinout and voltage.
- Spare microSD failure-injection requires a separate known-good backup and independent owner authorization. No destructive test on occupied production S1 or historical CSV files.
- The **hardware backlog** is a mixture of bench fixtures and unfinished custom firmware native-service verification; buying the Tier A basket can close core sensor/PWM/storage/device tests, **not automatically all HW-01…HW-19**.
- Record each physical test with actual device firmware and FAP SHA256, wiring, stimulus, measured values, STOP/BACK/restart, BUSY/ERR and final data preservation. Mark EXPLICITLY deferred rather than inventing PASS.

**Value priority:** Owner plans to buy the practical Tier A items **without any oscilloscope**; defer university independent electrical measurement until the instructor-led visit. Existing ESP32-S2 reduces need for a new controller. Confirm store checkout stock/prices, USB data cable, analyzer probe clips and sensor breakout pull-ups before buying. Nothing in this list has been purchased or measured yet.
