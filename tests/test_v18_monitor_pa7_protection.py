#!/usr/bin/env python3
"""E11.1e: compile actual GPIO Monitor C against HAL side-effect shims.

Only tests PA7 exclusion when PWM claim is denied, running or unresolved.
Other GPIO pins/legacy firmware owners are NOT protected by this test.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"src/labmate_monitor_gpio.c"

MOCK=r'''
#ifndef E11_MONITOR_MOCK_H
#define E11_MONITOR_MOCK_H
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#define GPIO_COUNT 8U
#define GpioModeAnalog 0
#define GpioModeInput 1
typedef struct { unsigned index; } GpioPin;
typedef struct {
    unsigned gpio_index;
    bool generator_running,generator_blocked,generator_release_fault;
    bool gpio_state,gpio_previous_state;
} LabMateApp;
extern const GpioPin* const labmate_gpio_pins[GPIO_COUNT];
extern unsigned writes[GPIO_COUNT],reads[GPIO_COUNT];
bool labmate_monitor_pin_allowed(uint8_t index,bool pwm_reserved);
uint8_t labmate_monitor_entry_pin(uint8_t index,bool pwm_reserved);
void furi_hal_gpio_init_simple(const GpioPin* pin,int mode);
bool furi_hal_gpio_read(const GpioPin* pin);
#endif
'''
HARNESS=r'''
#include <assert.h>
#include "mock.h"
unsigned writes[GPIO_COUNT],reads[GPIO_COUNT];
static const GpioPin pin_values[GPIO_COUNT]={
    {0},{1},{2},{3},{4},{5},{6},{7}
};
const GpioPin* const labmate_gpio_pins[GPIO_COUNT]={
    &pin_values[0],&pin_values[1],&pin_values[2],&pin_values[3],
    &pin_values[4],&pin_values[5],&pin_values[6],&pin_values[7]
};
bool labmate_monitor_pin_allowed(uint8_t index,bool reserved) {
    return index<GPIO_COUNT && !(reserved && index==7U);
}
uint8_t labmate_monitor_entry_pin(uint8_t index,bool reserved) {
    return labmate_monitor_pin_allowed(index,reserved)?index:1U;
}
void furi_hal_gpio_init_simple(const GpioPin* pin,int mode) {
    assert(pin && (mode==GpioModeInput || mode==GpioModeAnalog));
    writes[pin->index]++;
}
bool furi_hal_gpio_read(const GpioPin* pin) {
    assert(pin); reads[pin->index]++;
    return true;
}
#include "labmate_monitor_gpio.c"
int main(void) {
    LabMateApp app={.gpio_index=7U};
    app.generator_blocked=true;
    labmate_monitor_gpio_release(&app,7U);
    assert(writes[7]==0U);
    labmate_monitor_gpio_activate(&app);
    assert(app.gpio_index==1U && app.gpio_state && writes[7]==0U);
    assert(writes[1]==1U && reads[1]==1U);
    app.generator_blocked=false; app.generator_release_fault=true;
    app.gpio_index=7U;
    labmate_monitor_gpio_activate(&app);
    labmate_monitor_gpio_release(&app,7U);
    assert(app.gpio_index==1U && writes[7]==0U);
    app.generator_release_fault=false;app.generator_running=true;
    app.gpio_index=7U;
    labmate_monitor_gpio_activate(&app);
    labmate_monitor_gpio_release(&app,7U);
    assert(app.gpio_index==1U && writes[7]==0U);
    app.generator_running=false;app.gpio_index=7U;
    labmate_monitor_gpio_activate(&app);
    assert(app.gpio_index==7U && writes[7]==1U && reads[7]==1U);
    labmate_monitor_gpio_release(&app,7U);
    assert(writes[7]==2U);
    assert(labmate_monitor_gpio_read(7U));
    assert(reads[7]==2U);
    assert(!labmate_monitor_gpio_read(GPIO_COUNT));
    return 0;
}
'''

def main():
    source=SOURCE.read_text()
    assert "app->generator_running || app->generator_blocked" in source
    assert "app->generator_release_fault" in source
    session=(ROOT/"src/labmate_capture_session.c").read_text()
    assert "app->generator_running || app->generator_blocked" in session
    assert "app->generator_release_fault" in session
    with tempfile.TemporaryDirectory(prefix="labmate_e11_monitor_") as td:
        root=Path(td)
        (root/"mock.h").write_text(MOCK)
        for h in ("labmate_monitor_gpio.h", "labmate_capture_core.h",
                  "labmate_resource_policy.h","furi_hal.h"):
            (root/h).write_text('#include "mock.h"\n')
        shutil.copy2(SOURCE,root/SOURCE.name)
        (root/"harness.c").write_text(HARNESS)
        exe=root/"run"
        subprocess.run([os.environ.get("CC","cc"),"-std=c11","-Wall",
                        "-Wextra","-Werror","-pedantic","-O0",
                        "-I",str(root),str(root/"harness.c"),"-o",str(exe)],
                       check=True)
        subprocess.run([str(exe)],check=True)
    print("E11.1e ACTUAL GPIO MONITOR C PA7 RESTRICTION HOST PASS:")
    print("denied, running or unresolved PWM never reconfigures PA7.")
    print("Other monitored pins remain non-leased: global ownership is OPEN.")

if __name__=="__main__":
    main()
