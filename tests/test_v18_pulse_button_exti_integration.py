#!/usr/bin/env python3
"""E11.1d: compile actual Pulse/Button start/stop C with HAL instrumentation.
CI/host only: neither IRQ timing nor independent Momentum service is modeled.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "PULSE": ("src/labmate_pulse_capture.c",
              "labmate_pulse_capture_start", "labmate_pulse_capture_stop",
              "pulse_gpio_callback", "LabMateCapturePulse"),
    "BUTTON": ("src/labmate_button_capture.c",
               "labmate_button_capture_start", "labmate_button_capture_stop",
               "labmate_button_irq", "LabMateCaptureButton"),
}

def extract(text: str, declaration: str) -> str:
    pos = text.index(declaration)
    brace = text.index("{", pos)
    level = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            level += 1
        elif text[i] == "}":
            level -= 1
            if level == 0:
                return text[pos:i+1]
    raise AssertionError("unterminated function: " + declaration)

PRELUDE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define GPIO_COUNT 8
#define GpioModeInterruptRiseFall 1
#define GpioPullNo 0
#define GpioPullUp 1
#define GpioSpeedVeryHigh 3
#define GpioModeAnalog 0
#define FURI_HAL_LEASE_IRQ_PC0 0x10U
#define FURI_HAL_LEASE_IRQ_PC1 0x20U
#define FURI_HAL_LEASE_IRQ_PB2 0x40U
#define FURI_HAL_LEASE_IRQ_PA4 0x80U
#ifdef TEST_APIS
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK 1
#endif
typedef struct { uint32_t pin; } GpioPin;
typedef enum { LabMateCaptureNone, LabMateCapturePulse, LabMateCaptureButton } LabMateCaptureOwner;
typedef struct { uint32_t opaque; } ButtonState;
typedef struct { uint32_t opaque; } ButtonStats;
typedef struct {
    unsigned gpio_index, capture_pin_index;
    LabMateCaptureOwner capture_owner;
    bool pulse_irq_active, pulse_irq_seen, pulse_irq_high_valid, pulse_irq_low_valid;
    bool pulse_irq_level, pulse_irq_wide_window;
    uint32_t pulse_irq_high_cycles, pulse_irq_low_cycles, pulse_irq_edges;
    uint32_t pulse_irq_high_sum, pulse_irq_low_sum, pulse_irq_last_cycle;
    uint32_t pulse_irq_tick_cycle, pulse_irq_last_tick;
    uint32_t pulse_irq_high_samples, pulse_irq_low_samples;
    bool button_active, button_session_started;
    ButtonState button_irq;
    ButtonStats button_stats;
    uint32_t button_bounce_us, button_settle_ms, button_hold_ms;
    bool capture_blocked, capture_release_fault;
} LabMateApp;
static const GpioPin pc0={1U}, pc1={2U}, pb2={4U}, pa4={16U};
const GpioPin* labmate_gpio_pins[GPIO_COUNT]={
    &pc0, &pc1, NULL, &pb2, NULL, &pa4, NULL, NULL
};
unsigned gpio_writes, gpio_reads, callback_writes, callback_attempts;
unsigned exti_writes, lease_attempts, lease_releases, button_inits, button_resumes;
uint32_t current_mask, expected_mask;
bool lease_available, callback_available, release_succeeds=true;
static bool labmate_capture_can_start(LabMateApp* app, LabMateCaptureOwner requested) {
    if(app->capture_release_fault || app->capture_owner!=LabMateCaptureNone) return false;
    if(requested==LabMateCaptureButton) return app->gpio_index==1U;
    return requested==LabMateCapturePulse &&
        (app->gpio_index==0U || app->gpio_index==1U ||
         app->gpio_index==3U || app->gpio_index==5U);
}
#ifdef TEST_APIS
static struct {uint32_t CYCCNT;} dwt_stub={123U};
#define DWT (&dwt_stub)
static uint32_t furi_get_tick(void) {return 456U;}
static bool furi_hal_gpio_read(const GpioPin* pin) {
    assert(pin!=NULL && lease_available);
    gpio_reads++;
    return true;
}
static LabMateCaptureOwner labmate_capture_owner_after_stop(
    LabMateCaptureOwner current, LabMateCaptureOwner stopping) {
    return current==stopping?LabMateCaptureNone:current;
}
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask==expected_mask);
    lease_attempts++;
    if(!lease_available) return 0U;
    current_mask=mask;
    return 99U;
}
static bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask) {
    assert(handle==99U && mask==expected_mask && mask==current_mask);
    lease_releases++;
    if(release_succeeds) current_mask=0U;
    return release_succeeds;
}
static void pulse_gpio_callback(void* ctx) {(void)ctx;}
static void labmate_button_irq(void* ctx) {(void)ctx;}
static bool furi_hal_gpio_try_add_int_callback(
    const GpioPin* pin, void(*cb)(void*), void* context) {
    assert(pin && cb && context && current_mask==expected_mask);
    assert(gpio_writes==0U && exti_writes==0U);
    callback_attempts++;
    if(!callback_available) return false;
    callback_writes++; /* nonasserting callback registration enables IT */
    return true;
}
static void labmate_capture_exti_clear(uint32_t line, bool rising) {
    assert(line != 0U && rising);
    exti_writes++;
}
#define furi_hal_gpio_init(p,...) ((void)(p),++gpio_writes)
#define furi_hal_gpio_init_simple(p,...) ((void)(p),++gpio_writes)
#define furi_hal_gpio_enable_int_callback(p) ((void)(p),++callback_writes)
#define furi_hal_gpio_disable_int_callback(p) ((void)(p),++callback_writes)
#define furi_hal_gpio_remove_int_callback(p) ((void)(p),++callback_writes)
static void labmate_button_state_init(ButtonState* st, bool b) {
    assert(st && b);
    button_inits++;
}
static void labmate_button_state_resume(ButtonState* st, bool b) {
    assert(st && b);
    button_resumes++;
}
static void labmate_button_snapshot(ButtonState* st, ButtonStats* stats) {
    assert(st && stats);
}
#endif
'''

TEST = r'''
static unsigned mutating_calls(void) {
    return gpio_writes+callback_writes+exti_writes;
}
int main(void) {
    LabMateApp app={0};
    app.capture_pin_index=GPIO_COUNT;
#ifdef MODE_BUTTON
    app.gpio_index=1U;
    expected_mask=FURI_HAL_LEASE_IRQ_PC1;
#else
    app.gpio_index=0U;
    expected_mask=FURI_HAL_LEASE_IRQ_PC0;
    app.pulse_irq_edges=22U;
#endif
    START(&app);
    assert(app.capture_blocked && !ACTIVE(app));
    assert(mutating_calls()==0U && lease_releases==0U);
    STOP(&app);
    assert(mutating_calls()==0U);
#ifdef TEST_APIS
    assert(lease_attempts==1U && callback_attempts==0U);
    app.capture_blocked=false;
    lease_available=true; callback_available=false;
    START(&app); /* occupied independent legacy EXTI callback */
    assert(app.capture_blocked && !ACTIVE(app));
    assert(mutating_calls()==0U && callback_attempts==1U);
    assert(lease_releases==1U && current_mask==0U);
    assert(app.capture_owner==LabMateCaptureNone &&
           app.capture_pin_index==GPIO_COUNT);
#ifdef MODE_BUTTON
    assert(!app.button_session_started && button_inits==0U);
#else
    assert(app.pulse_irq_edges==22U); /* denied start does not reset metrics */
#endif
    app.capture_blocked=false;
    callback_available=true;
    START(&app);
    assert(!app.capture_blocked && ACTIVE(app));
    assert(app.capture_owner==EXPECTED_OWNER);
    assert(app.capture_pin_index==app.gpio_index);
    assert(gpio_writes==1U && callback_attempts==2U);
    unsigned before=mutating_calls(), claims=lease_attempts;
    START(&app);
    assert(mutating_calls()==before && lease_attempts==claims);
    STOP(&app);
    assert(!ACTIVE(app) && app.capture_owner==LabMateCaptureNone &&
           app.capture_pin_index==GPIO_COUNT);
    assert(lease_releases==2U && current_mask==0U);
    before=mutating_calls();
    STOP(&app);
    assert(mutating_calls()==before && lease_releases==2U);
#ifdef MODE_BUTTON
    assert(app.button_session_started && button_inits==1U && button_resumes==0U);
    app.capture_blocked=false;
    START(&app);
    assert(ACTIVE(app) && button_inits==1U && button_resumes==1U);
    STOP(&app);
#else
    const unsigned indices[]={1U,3U,5U};
    const uint32_t masks[]={FURI_HAL_LEASE_IRQ_PC1,FURI_HAL_LEASE_IRQ_PB2,
                            FURI_HAL_LEASE_IRQ_PA4};
    for(unsigned i=0U;i<3U;i++) {
        app.gpio_index=indices[i];
        expected_mask=masks[i];
        app.capture_blocked=false;
        START(&app);
        assert(ACTIVE(app) && app.capture_pin_index==indices[i]);
        STOP(&app);
        assert(!ACTIVE(app) && !app.capture_release_fault);
    }
#endif
    app.capture_blocked=false;
    release_succeeds=false;
    START(&app);
    assert(ACTIVE(app));
    STOP(&app);
    assert(!ACTIVE(app) && app.capture_release_fault && app.capture_blocked);
    before=mutating_calls();
    claims=lease_attempts;
    START(&app);
    assert(!ACTIVE(app) && mutating_calls()==before && lease_attempts==claims);
#else
    assert(lease_attempts==0U && callback_attempts==0U);
    lease_available=true;callback_available=true;
    app.capture_blocked=false;
    START(&app);
    assert(app.capture_blocked && !ACTIVE(app) && mutating_calls()==0U);
#endif
    return 0;
}
'''

def main() -> None:
    for name, (file_name, start, stop, irq_name, owner) in MODULES.items():
        text=(ROOT/file_name).read_text(encoding="utf-8")
        assert "FURI_HAL_RESOURCE_LEASE_API_V1" in text
        assert "FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK" in text
        assert "app->capture_release_fault = true;" in text
        assert "if(!app->" in text and irq_name in text
        start_source=extract(text, "void "+start+"(LabMateApp* app) {")
        stop_source=extract(text, "void "+stop+"(LabMateApp* app) {")
        assert start_source.index("furi_hal_resource_lease_try_acquire(") < start_source.index(
            "furi_hal_gpio_try_add_int_callback(")
        assert start_source.index("furi_hal_gpio_try_add_int_callback(") < start_source.index(
            "furi_hal_gpio_init(")
        assert stop_source.index("furi_hal_gpio_remove_int_callback(") < stop_source.index(
            "furi_hal_resource_lease_release(")
        helper=""
        if name=="PULSE":
            helper="#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)\n"
            helper+=extract(text,"static uint32_t labmate_pulse_mask_for_pin(uint8_t index) {")
            helper+="\nstatic uint32_t labmate_pulse_lease_handle;\n"
            helper+="static uint32_t labmate_pulse_lease_mask;\n#endif\n"
        else:
            helper="#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)\n"
            helper+="static uint32_t labmate_button_lease_handle;\n#endif\n"
        for apis in (False, True):
            with tempfile.TemporaryDirectory(prefix="labmate_e11_"+name.lower()+"_") as tmp:
                path=Path(tmp)
                defs="#define START "+start+"\n#define STOP "+stop+"\n"
                defs+="#define EXPECTED_OWNER "+owner+"\n"
                defs+="#define ACTIVE(app) ((app)."+("button_active" if name=="BUTTON" else "pulse_irq_active")+")\n"
                source=PRELUDE+defs+helper+"\n"+start_source+"\n"+stop_source+"\n"+TEST
                harness=path/"harness.c";harness.write_text(source,encoding="utf-8")
                output=path/"harness"
                cmd=[os.environ.get("CC","cc"),"-std=c11","-Wall","-Wextra",
                     "-Werror","-pedantic","-O0",
                     "-DMODE_"+name+"=1"]
                if apis: cmd.append("-DTEST_APIS=1")
                subprocess.run(cmd+[str(harness),"-o",str(output)],check=True)
                subprocess.run([str(output)],check=True)
    print("E11.1d PULSE+BUTTON ACTUAL START/STOP C HOST PASS:")
    print("missing SDK / denied owner / occupied callback: zero HAL writes;")
    print("all 4 Pulse pins, Button RESUME, STOP, duplicate calls, failed release.")
    print("NOT firmware-global ownership or on-device evidence.")

if __name__=="__main__":
    main()
