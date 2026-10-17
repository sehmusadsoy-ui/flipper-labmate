// LabMate E11 H0 v3: stage-separated PA7 read-only diagnostic.
// No GPIO init, pin-mode change, output write, PWM, IRQ or firmware operation.
// Do not run H1 until this free-state diagnostic has been reviewed.
print("E11_H3_BEGIN");
let eventLoop = require("event_loop");
print("E11_H3_EVENT_LOOP_OK");
let gpio = require("gpio");
print("E11_H3_GPIO_OK");
let pa7 = gpio.get("PA7");
print("E11_H3_PIN_OK");
let value = pa7.read();
print("E11_H3_READ_OK");
