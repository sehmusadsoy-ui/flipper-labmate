// LabMate E11 H v2: read-only PA7 native JS GPIO lease probe.
// GPIO JS plugin requires event_loop to be loaded BEFORE gpio.
// No pin init, write, pwmWrite, pwmStop, interrupt or pin mode change.
print("E11_H_PA7_BEGIN");
let eventLoop = require("event_loop");
let gpio = require("gpio");
let pa7 = gpio.get("PA7");
let level = pa7.read();
print("E11_H_PA7_READ_OK " + level);
