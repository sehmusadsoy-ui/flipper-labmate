/* Exact production native STOP function bodies are extracted by the runner. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK 1
#define GPIO_COUNT 8U
#define FURI_HAL_LEASE_IRQ_PC1 0x100U
#define GpioModeAnalog 4
#define LL_EXTI_LINE_1 2U

typedef struct { int pin; } GpioPin;
static GpioPin stub_pin = {1};
static const GpioPin* labmate_gpio_pins[GPIO_COUNT] = {&stub_pin,&stub_pin,&stub_pin,&stub_pin,&stub_pin,&stub_pin,&stub_pin,&stub_pin};
typedef enum {
    LabMateCaptureNone = 0,
    LabMateCaptureFrequencyLow,
    LabMateCaptureFrequencyHigh,
    LabMateCapturePulse
} LabMateCaptureOwner;
typedef struct {
    bool frequency_hw_active;
    bool frequency_hw_gate_started;
    bool frequency_irq_active;
    bool pulse_irq_active;
    bool capture_release_fault;
    bool capture_blocked;
    LabMateCaptureOwner capture_owner;
    uint8_t capture_pin_index;
    uint32_t frequency_hw_last_count;
    uint32_t frequency_hw_last_cycle;
    uint32_t frequency_hw_last_poll_count;
    uint32_t frequency_hw_last_poll_cycle;
} LabMateApp;
static uint32_t labmate_frequency_pc1_lease;
static uint32_t labmate_pulse_lease_handle;
static uint32_t labmate_pulse_lease_mask;
static bool release_ok, tim2_pending;
static unsigned release_calls, irq_disables, irq_removes, mode_resets, exti_clears, tim2_stops;
static LabMateCaptureOwner labmate_capture_owner_after_stop(LabMateCaptureOwner current,LabMateCaptureOwner stopping) {
    return current == stopping ? LabMateCaptureNone : current;
}
static void furi_hal_gpio_disable_int_callback(const GpioPin* pin) { assert(pin); irq_disables++; }
static void furi_hal_gpio_remove_int_callback(const GpioPin* pin) { assert(pin); irq_removes++; }
static void labmate_capture_exti_clear(uint32_t line, bool owned) { assert(line && owned); exti_clears++; }
static void furi_hal_gpio_init_simple(const GpioPin* pin,int mode) { assert(pin && mode==GpioModeAnalog); mode_resets++; }
static bool furi_hal_resource_lease_release(uint32_t handle,uint32_t mask) { assert(handle && mask);release_calls++;return release_ok; }
static void labmate_frequency_tim2_shutdown(void) {tim2_stops++;if(release_ok)tim2_pending=false;}
static bool labmate_frequency_tim2_lease_pending(void) {return tim2_pending;}
#include "high_stop.inc"
#include "low_stop.inc"
#include "pulse_stop.inc"

static void reset(void) {
    release_ok=true;tim2_pending=false;release_calls=0;irq_disables=0;irq_removes=0;
    mode_resets=0;exti_clears=0;tim2_stops=0;
    labmate_frequency_pc1_lease=0;labmate_pulse_lease_handle=0;labmate_pulse_lease_mask=0;
}
int main(void) {
    unsigned scenarios=0;
    LabMateApp app;
    reset();
    app=(LabMateApp){.frequency_irq_active=true,.capture_owner=LabMateCaptureFrequencyLow,.capture_pin_index=1};
    labmate_frequency_pc1_lease=14;
    labmate_frequency_low_stop(&app);
    assert(!app.frequency_irq_active && app.capture_owner==LabMateCaptureNone);
    assert(app.capture_pin_index==GPIO_COUNT && !app.capture_release_fault);
    assert(labmate_frequency_pc1_lease==0 && release_calls==1 && irq_disables==1 && irq_removes==1);
    scenarios++;
    reset(); release_ok=false;
    app=(LabMateApp){.frequency_irq_active=true,.capture_owner=LabMateCaptureFrequencyLow,.capture_pin_index=1};
    labmate_frequency_pc1_lease=14;
    labmate_frequency_low_stop(&app);
    assert(!app.frequency_irq_active && app.capture_owner==LabMateCaptureFrequencyLow);
    assert(app.capture_pin_index==1 && app.capture_release_fault && app.capture_blocked);
    assert(labmate_frequency_pc1_lease==14 && release_calls==1);scenarios++;
    reset();
    app=(LabMateApp){.frequency_irq_active=true,.capture_owner=LabMateCaptureFrequencyLow,.capture_pin_index=1};
    labmate_frequency_low_stop(&app);
    assert(app.frequency_irq_active && app.capture_owner==LabMateCaptureFrequencyLow);
    assert(app.capture_blocked && !irq_disables && !release_calls);scenarios++;
    reset();
    app=(LabMateApp){.pulse_irq_active=true,.capture_owner=LabMateCapturePulse,.capture_pin_index=3};
    labmate_pulse_lease_handle=22;labmate_pulse_lease_mask=0x20;
    labmate_pulse_capture_stop(&app);
    assert(!app.pulse_irq_active && app.capture_owner==LabMateCaptureNone);
    assert(app.capture_pin_index==GPIO_COUNT && !app.capture_release_fault);
    assert(!labmate_pulse_lease_handle && !labmate_pulse_lease_mask && release_calls==1);scenarios++;
    reset();release_ok=false;
    app=(LabMateApp){.pulse_irq_active=true,.capture_owner=LabMateCapturePulse,.capture_pin_index=3};
    labmate_pulse_lease_handle=22;labmate_pulse_lease_mask=0x20;
    labmate_pulse_capture_stop(&app);
    assert(!app.pulse_irq_active && app.capture_owner==LabMateCapturePulse);
    assert(app.capture_pin_index==3 && app.capture_release_fault && app.capture_blocked);
    assert(labmate_pulse_lease_handle==22 && labmate_pulse_lease_mask==0x20);scenarios++;
    reset();
    app=(LabMateApp){.pulse_irq_active=true,.capture_owner=LabMateCapturePulse,.capture_pin_index=3};
    labmate_pulse_capture_stop(&app);
    assert(app.pulse_irq_active && app.capture_owner==LabMateCapturePulse && app.capture_blocked);
    assert(!release_calls && !irq_disables);scenarios++;
    reset();tim2_pending=true;
    app=(LabMateApp){.frequency_hw_active=true,.capture_owner=LabMateCaptureFrequencyHigh,.capture_pin_index=4};
    labmate_frequency_high_stop(&app);
    assert(!app.frequency_hw_active && app.capture_owner==LabMateCaptureNone);
    assert(app.capture_pin_index==GPIO_COUNT && !app.capture_release_fault);
    assert(tim2_stops==1 && !tim2_pending);scenarios++;
    reset();tim2_pending=true;release_ok=false;
    app=(LabMateApp){.frequency_hw_active=true,.capture_owner=LabMateCaptureFrequencyHigh,.capture_pin_index=4};
    labmate_frequency_high_stop(&app);
    assert(!app.frequency_hw_active && app.capture_owner==LabMateCaptureFrequencyHigh);
    assert(app.capture_pin_index==4 && app.capture_release_fault && app.capture_blocked);
    assert(tim2_stops==1 && tim2_pending);scenarios++;
    reset();
    app=(LabMateApp){.frequency_hw_active=false,.capture_owner=LabMateCaptureFrequencyHigh,.capture_pin_index=4};
    labmate_frequency_high_stop(&app);
    assert(app.capture_owner==LabMateCaptureFrequencyHigh && !tim2_stops);scenarios++;
    printf("Phase2K extracted native STOP functions PASS: %u success/failure/empty-handle cases\n",scenarios);
    return scenarios==9 ? 0:1;
}
