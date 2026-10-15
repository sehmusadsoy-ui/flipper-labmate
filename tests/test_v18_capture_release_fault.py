#!/usr/bin/env python3
"""E11: exercise actual shared capture STOP and acquisition C on host.
No firmware/Flipper hardware is accessed. Focus: sticky lease-release fault.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def body(path: str, name: str) -> str:
    src=(ROOT/path).read_text(encoding="utf-8")
    begin=src.index(name)
    idx=src.index("{",begin)
    n=0
    for i in range(idx,len(src)):
        if src[i]=="{": n+=1
        elif src[i]=="}":
            n-=1
            if not n: return src[begin:i+1]
    raise AssertionError(name)

STUB=r"""
#include <stdbool.h>
#include <stdint.h>
#include <assert.h>
#define GPIO_COUNT 8
typedef enum { LabMateCaptureNone,LabMateCapturePulse } LabMateCaptureOwner;
typedef struct {
    bool counter_active,button_active,frequency_irq_active,frequency_hw_active;
    bool pulse_irq_active,capture_blocked,capture_release_fault;
    unsigned capture_pin_index,gpio_index;
    LabMateCaptureOwner capture_owner;
} LabMateApp;
static bool labmate_capture_all_stopped(bool l,bool h,bool p) {
    return !l && !h && !p;
}
static bool labmate_capture_can_acquire(
    LabMateCaptureOwner owner,LabMateCaptureOwner requested,uint8_t index,
    bool low,bool high,bool pulse) {
    return owner==LabMateCaptureNone && requested==LabMateCapturePulse &&
        index==1U && !low && !high && !pulse;
}
#define STOP_FUNCTION(n) static void n(LabMateApp* app) {(void)app;}
STOP_FUNCTION(labmate_frequency_high_stop)
STOP_FUNCTION(labmate_frequency_low_stop)
STOP_FUNCTION(labmate_pulse_capture_stop)
STOP_FUNCTION(labmate_event_counter_stop)
STOP_FUNCTION(labmate_button_capture_stop)
"""
TEST=r"""
int main(void) {
    LabMateApp app={.gpio_index=1U,.capture_owner=LabMateCaptureNone,
                    .capture_pin_index=GPIO_COUNT};
    assert(labmate_capture_can_start(&app,LabMateCapturePulse));
    assert(!app.capture_blocked);
    app.capture_release_fault=true;
    assert(!labmate_capture_can_start(&app,LabMateCapturePulse));
    assert(app.capture_blocked);
    labmate_capture_stop_all(&app);
    assert(app.capture_release_fault && app.capture_blocked);
    assert(app.capture_owner==LabMateCaptureNone && app.capture_pin_index==GPIO_COUNT);
    assert(!labmate_capture_can_start(&app,LabMateCapturePulse));
    app.capture_release_fault=false; /* new fresh-app state */
    labmate_capture_stop_all(&app);
    assert(!app.capture_blocked);
    assert(labmate_capture_can_start(&app,LabMateCapturePulse));
    app.frequency_irq_active=true;
    labmate_capture_stop_all(&app);
    assert(app.capture_blocked);
    return 0;
}
"""
def main() -> None:
    capture=body("src/labmate_capture_session.c",
                 "void labmate_capture_stop_all(LabMateApp* app) {")
    acquire=body("src/labmate_capture_core.c",
                 "bool labmate_capture_can_start(LabMateApp* app, LabMateCaptureOwner requested) {")
    assert "app->capture_blocked = app->capture_release_fault;" in capture
    assert "!app->capture_release_fault" in acquire
    with tempfile.TemporaryDirectory(prefix="labmate_e11_fault_") as d:
        folder=Path(d)
        src=folder/"harness.c"
        src.write_text(STUB+"\n"+acquire+"\n"+capture+"\n"+TEST)
        exe=folder/"harness"
        subprocess.run([os.environ.get("CC","cc"),"-std=c11","-Wall","-Wextra",
                        "-Werror","-pedantic","-O0",str(src),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 SHARED STOP/CAN_START ACTUAL PRODUCTION C HOST PASS:")
    print("failed lease release stays blocked across STOP and later capture attempt.")
    print("NO real firmware service conflict or Flipper hardware result.")

if __name__=="__main__":
    main()
