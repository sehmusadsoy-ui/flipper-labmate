/* Exact production capture_stop_all(), exercising final release decisions. */
#include "labmate_capture_release_gate.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define GPIO_COUNT 8U
typedef enum {
    LabMateCaptureNone=0,LabMateCaptureFrequencyLow,LabMateCaptureFrequencyHigh,
    LabMateCapturePulse,LabMateCaptureCounter,LabMateCaptureButton,LabMateCaptureScope
} LabMateCaptureOwner;
typedef struct { unsigned dummy; } ScopeNative;
typedef struct {
    ScopeNative scope_native;
    LabMateCaptureOwner capture_owner;
    uint8_t capture_pin_index;
    bool capture_release_fault,capture_blocked;
    bool frequency_irq_active,frequency_hw_active,pulse_irq_active,counter_active,button_active;
} LabMateApp;
static bool scope_ok,bridge_ok,low_pending,high_pending,pulse_pending,button_pending;
static unsigned stops;
static bool labmate_scope_native_stop_confirmed(ScopeNative* s,LabMateCaptureOwner owner){(void)s;(void)owner;return scope_ok;}
static bool labmate_scope_bridge_stop(LabMateApp* a){(void)a;if(bridge_ok)scope_ok=true;return bridge_ok;}
static void labmate_frequency_high_stop(LabMateApp* a){++stops;if(a->frequency_hw_active){a->frequency_hw_active=false;if(high_pending)a->capture_release_fault=true;}}
static void labmate_frequency_low_stop(LabMateApp* a){++stops;if(a->frequency_irq_active){a->frequency_irq_active=false;if(low_pending)a->capture_release_fault=true;}}
static void labmate_pulse_capture_stop(LabMateApp* a){++stops;if(a->pulse_irq_active){a->pulse_irq_active=false;if(pulse_pending)a->capture_release_fault=true;}}
static void labmate_event_counter_stop(LabMateApp* a){++stops;if(a->counter_active){a->counter_active=false;if(high_pending)a->capture_release_fault=true;}}
static void labmate_button_capture_stop(LabMateApp* a){++stops;if(a->button_active){a->button_active=false;if(button_pending)a->capture_release_fault=true;}}
static bool labmate_frequency_low_lease_pending(void){return low_pending;}
static bool labmate_frequency_tim2_lease_pending(void){return high_pending;}
static bool labmate_pulse_lease_pending(void){return pulse_pending;}
static bool labmate_button_lease_pending(void){return button_pending;}
#include "stop_all.inc"
static void reset(void){scope_ok=true;bridge_ok=false;low_pending=false;high_pending=false;pulse_pending=false;button_pending=false;stops=0;}
int main(void){
    unsigned cases=0;LabMateApp a;
    reset();a=(LabMateApp){.capture_owner=LabMateCaptureFrequencyLow,.capture_pin_index=1};
    labmate_capture_stop_all(&a);
    assert(a.capture_owner==LabMateCaptureNone && a.capture_pin_index==GPIO_COUNT && !a.capture_blocked && stops==5);cases++;
    reset();a=(LabMateApp){.capture_owner=LabMateCaptureFrequencyLow,.capture_pin_index=1,.frequency_irq_active=true};
    labmate_capture_stop_all(&a);
    assert(!a.frequency_irq_active && a.capture_owner==LabMateCaptureNone && !a.capture_blocked);cases++;
    reset();low_pending=true;a=(LabMateApp){.capture_owner=LabMateCaptureFrequencyLow,.capture_pin_index=1,.frequency_irq_active=true};
    labmate_capture_stop_all(&a);assert(a.capture_owner==LabMateCaptureFrequencyLow && a.capture_blocked && a.capture_release_fault);cases++;
    reset();pulse_pending=true;a=(LabMateApp){.capture_owner=LabMateCapturePulse,.capture_pin_index=3,.pulse_irq_active=true};
    labmate_capture_stop_all(&a);assert(a.capture_owner==LabMateCapturePulse && a.capture_blocked && a.capture_release_fault);cases++;
    reset();high_pending=true;a=(LabMateApp){.capture_owner=LabMateCaptureFrequencyHigh,.capture_pin_index=4,.frequency_hw_active=true};
    labmate_capture_stop_all(&a);assert(a.capture_owner==LabMateCaptureFrequencyHigh && a.capture_blocked && a.capture_release_fault);cases++;
    reset();button_pending=true;a=(LabMateApp){.capture_owner=LabMateCaptureButton,.capture_pin_index=1,.button_active=true};
    labmate_capture_stop_all(&a);assert(a.capture_owner==LabMateCaptureButton && a.capture_blocked && a.capture_release_fault);cases++;
    reset();high_pending=true;a=(LabMateApp){.capture_owner=LabMateCaptureCounter,.capture_pin_index=4,.counter_active=true};
    labmate_capture_stop_all(&a);assert(a.capture_owner==LabMateCaptureCounter && a.capture_blocked && a.capture_release_fault);cases++;
    reset();a=(LabMateApp){.capture_owner=LabMateCapturePulse,.capture_pin_index=3,.capture_release_fault=true};
    labmate_capture_stop_all(&a);assert(a.capture_owner==LabMateCapturePulse && a.capture_blocked);cases++;
    reset();scope_ok=false;a=(LabMateApp){.capture_owner=LabMateCaptureScope,.capture_pin_index=1};
    labmate_capture_stop_all(&a);assert(a.capture_owner==LabMateCaptureScope && a.capture_release_fault && a.capture_blocked);cases++;
    reset();scope_ok=false;bridge_ok=true;a=(LabMateApp){.capture_owner=LabMateCaptureScope,.capture_pin_index=1};
    labmate_capture_stop_all(&a);assert(scope_ok && a.capture_owner==LabMateCaptureNone && !a.capture_blocked);cases++;
    printf("Phase2K extracted STOP-all integration PASS: %u scope/capture/lease scenarios\n",cases);
    return cases==10U?0:1;
}
