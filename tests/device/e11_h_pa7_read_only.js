// LabMate E11 Round H: read-only competing client for PA7.
// No init(), write(), pwmWrite(), pwmStop(), interrupts or pin-mode changes.
// Run from the matched Momentum USB CLI while LabMate PWM is explicitly RUN.
// A BUSY error from pa7.read() is the EXPECTED denial while PWM owns PA7.
print("E11_H_PA7_BEGIN");
let gpio = require("gpio");
let pa7 = gpio.get("PA7");
let level = pa7.read();
print("E11_H_PA7_READ_OK " + level);
