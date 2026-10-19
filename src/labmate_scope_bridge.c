#include "labmate_scope_bridge.h"
#include "labmate_scope_exit_guard.h"
#include <furi.h>
#include <furi_hal.h>

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
    a->scope_display.plot = labmate_scope_plot_focus(
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

/* Called only after the matching PC1 IRQ callback has been detached
 * and the E11 firmware lease was positively released. Accessing the
 * full 256-edge native array while live is categorically forbidden. */
static void labmate_scope_bridge_latch(LabMateApp* a) {
    if(!a || a->scope_capture_generation == 0U ||
       a->scope_last_generation == a->scope_capture_generation ||
       !labmate_scope_native_reinit_safe(&a->scope_native) ||
       a->capture_owner != LabMateCaptureNone) return;
    a->scope_last_generation = a->scope_capture_generation;
    a->scope_last_valid = false;
    a->scope_last_metrics = (LabMateScopeMetrics){0};
    const LabMateScopeSnapshot s =
        labmate_scope_native_read(&a->scope_native, NULL, 0U, NULL);
    if(a->scope_clock_fault || a->scope_capture_hz == 0U ||
       s.state != LabMateScopeStopped || s.timebase_error ||
       s.count < 3U ||
       s.count > LABMATE_SCOPE_MAX_EDGES) return;
    a->scope_last_metrics = labmate_scope_metrics_from_edges(
        a->scope_native.storage, s.count, a->scope_capture_hz);
    a->scope_last_metrics.truncated = s.overflowed || s.dropped_edges > 0U;
    a->scope_last_valid =
        a->scope_last_metrics.status == LabMateScopeMetricsReady &&
        !a->scope_last_metrics.truncated;
}

bool labmate_scope_bridge_init(LabMateApp* a) {
    if(!a || !labmate_scope_native_init(&a->scope_native)) return false;
    a->scope_display.lines = a->scope_lines;
    a->scope_display.plot.result = LabMateScopePlotNoEdges;
    a->scope_display.state = LabMateScopeDisplayStopped;
    labmate_scope_pair_reset(&a->scope_pair);
    return true;
}

void labmate_scope_bridge_enter(LabMateApp* a) {
    if(!a) return;
    a->scope_show_compare = false;
    a->scope_compare_page = 0U;
    a->scope_show_reference = false;
    a->scope_display.state =
        !labmate_scope_native_stop_confirmed(
            &a->scope_native, a->capture_owner) ?
            LabMateScopeDisplayError : LabMateScopeDisplayStopped;
    labmate_scope_bridge_refresh(a);
}

bool labmate_scope_bridge_stop(LabMateApp* a) {
    if(!a) return false;
    if(a->scope_native.active &&
       (!a->scope_capture_hz || SystemCoreClock != a->scope_capture_hz ||
        (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) == 0U))
        a->scope_clock_fault = true;
    if(a->scope_native.active || a->scope_native.owner.handle) {
        if(!labmate_scope_native_stop(&a->scope_native, &a->capture_owner)) {
            a->capture_release_fault = true;
            a->capture_blocked = true;
            a->scope_display.state = LabMateScopeDisplayError;
            return false;
        }
    }
    /* A zero lease handle alone does not confirm IRQ callback cleanup.
     * Only a fully idle native owner can exit Scope or latch a captured
     * measurement. Never turn unfinished teardown into STOP/BACK success. */
    if(!labmate_scope_native_stop_confirmed(
           &a->scope_native, a->capture_owner)) {
        a->capture_release_fault = true;
        a->capture_blocked = true;
        a->scope_last_valid = false;
        a->scope_display.state = LabMateScopeDisplayError;
        labmate_scope_bridge_refresh(a);
        return false;
    }
    a->scope_display.state =
        a->scope_clock_fault ? LabMateScopeDisplayError :
                               LabMateScopeDisplayStopped;
    if(a->capture_owner == LabMateCaptureNone)
        a->capture_pin_index = GPIO_COUNT;
    labmate_scope_bridge_latch(a);
    labmate_scope_bridge_refresh(a);
    return true;
}

void labmate_scope_bridge_poll(LabMateApp* a) {
    if(!a || a->screen != LabMateScreenScope) return;
    if(a->scope_native.active) {
        if(!a->scope_capture_hz || SystemCoreClock != a->scope_capture_hz ||
           (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) == 0U) {
            a->scope_clock_fault = true;
            (void)labmate_scope_bridge_stop(a);
            a->scope_display.state = LabMateScopeDisplayError;
            labmate_scope_bridge_refresh(a);
            return;
        }
        const LabMateScopeGuardResult state = labmate_scope_native_poll(
            &a->scope_native, &a->capture_owner, labmate_scope_bridge_millis());
        /* A missed watchdog poll or uncertain edge clock invalidates the
         * entire A/B metric candidate, even when captured edges look sane. */
        if(state == LabMateScopeGuardClockUnsafe ||
           state == LabMateScopeGuardCaptureError ||
           state == LabMateScopeGuardInvalid ||
           state == LabMateScopeGuardStopped)
            a->scope_clock_fault = true;
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
        case LabMateScopeGuardSampleComplete:
            /* Native poll has already detached the owned IRQ and lease.
             * The subsequent latch validates full cycles and overflow. */
            a->scope_display.state = LabMateScopeDisplayStopped; break;
        default:
            a->scope_display.state = LabMateScopeDisplayError; break;
        }
        if(state == LabMateScopeGuardInvalid && a->scope_native.active) {
            /* A lost/mismatched app owner may not leave an IRQ running while
             * the UI displays ERROR. Attempt ONLY owned callback teardown. */
            (void)labmate_scope_bridge_stop(a);
            a->scope_display.state = LabMateScopeDisplayError;
        }
        if(!a->scope_native.active &&
           !a->scope_native.owner.handle &&
           a->capture_owner == LabMateCaptureNone)
            a->capture_pin_index = GPIO_COUNT;
        if(a->scope_native.fault_sticky) {
            a->capture_release_fault = true;
            a->capture_blocked = true;
            a->scope_display.state = LabMateScopeDisplayError;
        }
        labmate_scope_bridge_latch(a);
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
    if(event.key == InputKeyDown && !a->scope_native.active) {
        /* Read-only page rotation: PLOT -> A/B -> REFERENCE -> PLOT.
         * Changing display pages never touches the IRQ or capture data. */
        if(a->scope_show_reference) {
            a->scope_show_reference = false;
            a->scope_show_compare = false;
            a->scope_compare_page = 0U;
        } else if(a->scope_show_compare) {
            a->scope_show_compare = false;
            a->scope_show_reference = true;
            a->scope_compare_page = 0U;
        } else {
            a->scope_show_compare = true;
            a->scope_compare_page = 0U;
        }
        return;
    }
    if(event.key == InputKeyUp && !a->scope_native.active) {
        if(a->scope_show_reference) {
            a->scope_reference_preset =
                a->scope_reference_preset == LabMateScopeReference100Hz50 ?
                    LabMateScopeReference1kHz50 : LabMateScopeReference100Hz50;
            return;
        }
        if(a->scope_show_compare) {
            /* Read-only frequency summary -> A times -> B times. */
            a->scope_compare_page = (uint8_t)((a->scope_compare_page + 1U) % 3U);
            return;
        }
    }
    if((event.key == InputKeyLeft || event.key == InputKeyRight) &&
       !a->scope_native.active && !a->scope_show_reference) {
        const bool complete = a->scope_last_valid &&
            labmate_scope_native_reinit_safe(&a->scope_native) &&
            a->capture_owner == LabMateCaptureNone &&
            !a->scope_clock_fault &&
            a->scope_last_generation == a->scope_capture_generation;
        const LabMateScopeMetrics* metric =
            complete ? &a->scope_last_metrics : NULL;
        if(event.key == InputKeyLeft)
            (void)labmate_scope_pair_save_a(
                &a->scope_pair, metric, a->scope_last_generation);
        else
            (void)labmate_scope_pair_save_b(
                &a->scope_pair, metric, a->scope_last_generation);
        a->scope_show_compare = true;
        a->scope_compare_page = 0U; /* show save result before details */
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
    if(furi_kernel_get_tick_frequency() == 0U ||
       a->scope_capture_generation == UINT32_MAX) {
        a->scope_display.state = LabMateScopeDisplayError;
        return; /* no trustworthy clock or run-id generation */
    }
    const LabMateScopePc1Environment env = labmate_scope_bridge_environment(a);
    const LabMateScopeNativeStatus state = labmate_scope_native_start(
        &a->scope_native, &env, &a->capture_owner, labmate_scope_bridge_millis());
    if(state == LabMateScopeNativeReady && a->scope_native.active) {
        ++a->scope_capture_generation;
        a->scope_capture_hz = SystemCoreClock;
        a->scope_clock_fault = a->scope_capture_hz == 0U;
        a->scope_last_valid = false;
        a->scope_show_compare = false;
        a->scope_compare_page = 0U;
        a->scope_show_reference = false;
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
