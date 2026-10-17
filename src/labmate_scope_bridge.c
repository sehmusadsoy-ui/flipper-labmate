#include "labmate_scope_bridge.h"
#include <furi.h>

/* The Furi kernel's tick unit is NOT guaranteed to be milliseconds.
 * Conversion happens before entering the pure-C timeguard. The app loop
 * currently polls at 10 ticks, but a delayed GUI/storage task results in
 * CLOCK UNSAFE rather than a fabricated time interval.
 */
static uint32_t labmate_scope_bridge_millis(void) {
    const uint32_t hz = furi_kernel_get_tick_frequency();
    if(!hz) return 0U;
    return (uint32_t)(((uint64_t)furi_get_tick() * 1000U) / hz);
}

static LabMateScopePc1Environment labmate_scope_bridge_environment(const LabMateApp* a) {
    return (LabMateScopePc1Environment){
        .selected_pin = LABMATE_MONITOR_PC1_INDEX,
        .capture_owner = a->capture_owner,
        .comm_owner = a->comm_owner,
        .frequency_irq_active = a->frequency_irq_active,
        .frequency_hw_active = a->frequency_hw_active,
        .pulse_irq_active = a->pulse_irq_active,
        .counter_active = a->counter_active,
        .button_active = a->button_active,
        .monitor_active = a->monitor_active,
        .logger_active = a->logger_recording || a->logger_storage || a->logger_file,
        .uart_active = a->uart.active,
        .capture_release_fault = a->capture_release_fault,
        .monitor_release_fault = a->monitor_release_fault,
        /* Firmware-specific availability is checked again in native START.
         * Do not pretend these fields are a hardware capability probe. */
        .firmware_lease_api = false,
        .firmware_try_callback = false,
    };
}

static void labmate_scope_bridge_refresh(LabMateApp* a) {
    uint16_t copied = 0U;
    const LabMateScopeSnapshot snap = labmate_scope_native_read(
        &a->scope_native, a->scope_recent, LABMATE_SCOPE_PLOT_MAX_EDGES, &copied);
    a->scope_display.plot = labmate_scope_plot_project(
        a->scope_recent, copied, snap.count > copied,
        a->scope_lines, LABMATE_SCOPE_PLOT_MAX_LINES);
    a->scope_display.lines = a->scope_lines;
    a->scope_display.total_edges = snap.count;
    if(a->scope_native.active) {
        a->scope_display.state = snap.state == LabMateScopeRecording ?
            LabMateScopeDisplayRunning : LabMateScopeDisplayArmed;
    }
    if(snap.timebase_error || a->scope_native.fault_sticky)
        a->scope_display.state = LabMateScopeDisplayError;
}

bool labmate_scope_bridge_init(LabMateApp* a) {
    if(!a || !labmate_scope_native_init(&a->scope_native)) return false;
    a->scope_display.lines = a->scope_lines;
    a->scope_display.plot.result = LabMateScopePlotNoEdges;
    a->scope_display.state = LabMateScopeDisplayStopped;
    return true;
}

void labmate_scope_bridge_enter(LabMateApp* a) {
    if(!a) return;
    a->scope_display.state =
        a->scope_native.fault_sticky ? LabMateScopeDisplayError :
        LabMateScopeDisplayStopped;
    labmate_scope_bridge_refresh(a);
}

bool labmate_scope_bridge_stop(LabMateApp* a) {
    if(!a) return false;
    if(a->scope_native.active || a->scope_native.owner.handle) {
        if(!labmate_scope_native_stop(&a->scope_native, &a->capture_owner)) {
            a->capture_release_fault = true;
            a->capture_blocked = true;
            a->scope_display.state = LabMateScopeDisplayError;
            return false;
        }
    }
    if(a->scope_native.fault_sticky) {
        a->capture_release_fault = true;
        a->capture_blocked = true;
        a->scope_display.state = LabMateScopeDisplayError;
    } else {
        a->scope_display.state = LabMateScopeDisplayStopped;
    }
    labmate_scope_bridge_refresh(a);
    return !a->scope_native.owner.handle;
}

void labmate_scope_bridge_poll(LabMateApp* a) {
    if(!a || a->screen != LabMateScreenScope) return;
    if(a->scope_native.active) {
        const LabMateScopeGuardResult state = labmate_scope_native_poll(
            &a->scope_native, &a->capture_owner, labmate_scope_bridge_millis());
        switch(state) {
        case LabMateScopeGuardRunning: break;
        case LabMateScopeGuardNoTrigger:
            a->scope_display.state = LabMateScopeDisplayNoTrigger; break;
        case LabMateScopeGuardQuiet:
            a->scope_display.state = LabMateScopeDisplayQuiet; break;
        case LabMateScopeGuardFull:
            a->scope_display.state = LabMateScopeDisplayFull; break;
        case LabMateScopeGuardStopped:
        case LabMateScopeGuardDurationLimit:
            a->scope_display.state = LabMateScopeDisplayStopped; break;
        default:
            a->scope_display.state = LabMateScopeDisplayError; break;
        }
        if(a->scope_native.fault_sticky) {
            a->capture_release_fault = true;
            a->capture_blocked = true;
            a->scope_display.state = LabMateScopeDisplayError;
        }
    }
    labmate_scope_bridge_refresh(a);
}

void labmate_scope_bridge_input(LabMateApp* a, InputEvent event) {
    if(!a) return;
    if(event.key == InputKeyBack) {
        if(labmate_scope_bridge_stop(a))
            a->screen = LabMateScreenMenu;
        return;
    }
    if(event.key != InputKeyOk) return;
    if(a->scope_native.active) {
        (void)labmate_scope_bridge_stop(a);
        return;
    }
    if(a->scope_native.fault_sticky || a->capture_release_fault) {
        a->scope_display.state = LabMateScopeDisplayError;
        return;
    }
    const LabMateScopePc1Environment env = labmate_scope_bridge_environment(a);
    const LabMateScopeNativeStatus state = labmate_scope_native_start(
        &a->scope_native, &env, &a->capture_owner, labmate_scope_bridge_millis());
    if(state == LabMateScopeNativeReady && a->scope_native.active) {
        a->gpio_index = LABMATE_MONITOR_PC1_INDEX;
        a->capture_pin_index = LABMATE_MONITOR_PC1_INDEX;
        a->scope_display.state = LabMateScopeDisplayArmed;
        a->scope_display.plot.result = LabMateScopePlotNoEdges;
        a->scope_display.total_edges = 0U;
    } else {
        a->scope_display.state = state == LabMateScopeNativeBusy ?
            LabMateScopeDisplayBusy :
            state == LabMateScopeNativeUnsupported ? LabMateScopeDisplayUnsupported :
            LabMateScopeDisplayError;
        a->capture_blocked = state == LabMateScopeNativeBusy;
        if(a->scope_native.fault_sticky) {
            a->capture_release_fault = true;
            a->capture_blocked = true;
        }
    }
    labmate_scope_bridge_refresh(a);
}
