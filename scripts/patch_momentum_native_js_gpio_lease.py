#!/usr/bin/env python3
"""E11: migrate native Momentum JavaScript GPIO external pin users.

Exact pinned, prepatched Momentum source only. No device writes.
Protects GPIO read/write/init/analog/IRQ on eight listed connector pins,
without claiming exclusive control over direct-register legacy services.
Avoids resetting unowned pins when the JS module is destroyed.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PINNED = "d3f89dfe2ef6b01839201598e9be1590cba80322"
TARGET = "applications/system/js_app/modules/js_gpio.c"
EXPECTED_DIRTY = {
    "targets/furi_hal_include/furi_hal_i2c.h",
    "targets/f7/furi_hal/furi_hal_i2c.c",
    "targets/f7/furi_hal/furi_hal_resources.h",
    "targets/f7/furi_hal/furi_hal_resources.c",
    "targets/f7/furi_hal/furi_hal_gpio.h",
    "targets/f7/furi_hal/furi_hal_gpio.c",
    "targets/f7/furi_hal/furi_hal_pwm.c",
    "targets/f7/api_symbols.csv",
}
MARKER = "/* LabMate E11 native JS GPIO connector-owner contract. */"

HELPERS = """/* LabMate E11 native JS GPIO connector-owner contract. */
static uint32_t js_gpio_e11_monitor_mask(const GpioPin* pin) {
    if(pin == &gpio_ext_pc0) return FURI_HAL_LEASE_MONITOR_PC0;
    if(pin == &gpio_ext_pc1) return FURI_HAL_LEASE_MONITOR_PC1;
    if(pin == &gpio_ext_pc3) return FURI_HAL_LEASE_MONITOR_PC3;
    if(pin == &gpio_ext_pb2) return FURI_HAL_LEASE_MONITOR_PB2;
    if(pin == &gpio_ext_pb3) return FURI_HAL_LEASE_MONITOR_PB3;
    if(pin == &gpio_ext_pa4) return FURI_HAL_LEASE_MONITOR_PA4;
    if(pin == &gpio_ext_pa6) return FURI_HAL_LEASE_MONITOR_PA6;
    if(pin == &gpio_ext_pa7) return FURI_HAL_LEASE_MONITOR_PA7;
    return 0U; /* Existing behavior on non-E11 connector pins */
}

/* The first actual GPIO operation claims the pin; get() is side-effect-free.
 * The pin is held for the JS module lifetime. A native PWM started by this
 * manager cannot coexist with its generic pin claim. Never claim a pin
 * that a cooperating native PWM service already has running.
 */
/* EXTI is keyed by line number, NOT by GPIO port. PC3/PB3 both
 * configure EXTI3 and must not take over each other's capture.
 */
static uint32_t js_gpio_e11_exti_mask(const GpioPin* pin) {
    if(pin == &gpio_ext_pc0) return FURI_HAL_LEASE_JS_EXTI0;
    if(pin == &gpio_ext_pc1) return FURI_HAL_LEASE_JS_EXTI1;
    if(pin == &gpio_ext_pc3) return FURI_HAL_LEASE_JS_EXTI3;
    if(pin == &gpio_ext_pb2) return FURI_HAL_LEASE_JS_EXTI2;
    if(pin == &gpio_ext_pb3) return FURI_HAL_LEASE_JS_EXTI3;
    if(pin == &gpio_ext_pa4) return FURI_HAL_LEASE_JS_EXTI4;
    if(pin == &gpio_ext_pa6) return FURI_HAL_LEASE_JS_EXTI6;
    if(pin == &gpio_ext_pa7) return FURI_HAL_LEASE_JS_EXTI7;
    return 0U;
}

static bool js_gpio_e11_claim_exti(JsGpioPinInst* data) {
    const uint32_t mask = js_gpio_e11_exti_mask(data->pin);
    if(!mask) return true; /* Non-E11 pins keep legacy semantics */
    if(data->lease_fault || !data->lease_handle) return false;
    if(data->exti_lease_handle) return data->exti_lease_mask == mask;
    /* Claim only the EXTI bit: the pin has its own live lease. */
    const uint32_t handle = furi_hal_resource_lease_try_acquire(mask);
    if(!handle) return false;
    data->exti_lease_handle = handle;
    data->exti_lease_mask = mask;
    return true;
}

static bool js_gpio_e11_claim(JsGpioPinInst* manager_data) {
    const uint32_t mask = js_gpio_e11_monitor_mask(manager_data->pin);
    if(!mask) return true;
    if(manager_data->lease_fault || manager_data->pwm_owned) return false;
    if(manager_data->lease_handle) return manager_data->lease_mask == mask;
    if(manager_data->pwm_output != FuriHalPwmOutputIdNone &&
       furi_hal_pwm_is_running(manager_data->pwm_output)) return false;
    const uint32_t handle = furi_hal_resource_lease_try_acquire(mask);
    if(!handle) return false;
    manager_data->lease_handle = handle;
    manager_data->lease_mask = mask;
    return true;
}

"""
def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError("Absent or ambiguous native JS GPIO source anchor: " + repr(old[:95]))
    return source.replace(old, new, 1)

def patch_source(s: str) -> str:
    if MARKER in s: raise ValueError("native JS GPIO patch already applied")
    s = replace_once(s, """    FuriHalAdcHandle* adc_handle;
} JsGpioPinInst;""", """    FuriHalAdcHandle* adc_handle;
    uint32_t lease_handle;
    uint32_t lease_mask;
    uint32_t exti_lease_handle;
    uint32_t exti_lease_mask;
    bool lease_fault;
    bool configured;
    bool pwm_owned;
} JsGpioPinInst;""")
    s = replace_once(s, """ARRAY_DEF(ManagedPinsArray, JsGpioPinInst*, M_PTR_OPLIST);""",
                     HELPERS + "ARRAY_DEF(ManagedPinsArray, JsGpioPinInst*, M_PTR_OPLIST);")
    s = replace_once(s,
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);
    furi_hal_gpio_init(manager_data->pin, mode, pull, GpioSpeedVeryHigh);""",
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);
    if(!js_gpio_e11_claim(manager_data))
        JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO pin BUSY");
    /* Register the interrupt callback BEFORE GPIO init changes the
     * EXTI line mapping. Another native owner may be using the line
     * even when the selected connector GPIO itself is unclaimed.
     */
    const bool is_interrupt = mode == GpioModeInterruptRise ||
                              mode == GpioModeInterruptFall ||
                              mode == GpioModeInterruptRiseFall;
    const bool uses_exti = is_interrupt || mode == GpioModeEventRise ||
                           mode == GpioModeEventFall ||
                           mode == GpioModeEventRiseFall;
    if(uses_exti && !js_gpio_e11_claim_exti(manager_data))
        JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO EXTI line BUSY");
    /* Hold the separate EXTI handle until JS manager destruction,
     * even if mode changes, to avoid teardown/upgrade races.
     */
    if(is_interrupt && !manager_data->had_interrupt) {
        if(!furi_hal_gpio_try_add_int_callback(
               manager_data->pin, js_gpio_int_cb, manager_data->interrupt_semaphore))
            JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO EXTI BUSY");
        manager_data->had_interrupt = true;
    } else if(!is_interrupt && manager_data->had_interrupt) {
        furi_hal_gpio_disable_int_callback(manager_data->pin);
        furi_hal_gpio_remove_int_callback(manager_data->pin);
        manager_data->had_interrupt = false;
    }
    furi_hal_gpio_init(manager_data->pin, mode, pull, GpioSpeedVeryHigh);
    manager_data->configured = true;""")
    s = replace_once(s,
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);
    furi_hal_gpio_write(manager_data->pin, level);""",
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);
    if(!js_gpio_e11_claim(manager_data))
        JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO pin BUSY");
    furi_hal_gpio_write(manager_data->pin, level);""")
    s = replace_once(s,
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);
    bool value = furi_hal_gpio_read(manager_data->pin);""",
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);
    if(!js_gpio_e11_claim(manager_data))
        JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO pin BUSY");
    bool value = furi_hal_gpio_read(manager_data->pin);""")
    s = replace_once(s,
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);

    // interrupt handling
    if(!manager_data->had_interrupt) {
        furi_hal_gpio_add_int_callback(
            manager_data->pin, js_gpio_int_cb, manager_data->interrupt_semaphore);
        furi_hal_gpio_enable_int_callback(manager_data->pin);
        manager_data->had_interrupt = true;
    }""",
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);
    if(!js_gpio_e11_claim(manager_data))
        JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO interrupt pin BUSY");
    if(!js_gpio_e11_claim_exti(manager_data))
        JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO EXTI line BUSY");

    // Existing callback-slot owners must not assert or be taken over.
    if(!manager_data->had_interrupt) {
        if(!furi_hal_gpio_try_add_int_callback(
               manager_data->pin, js_gpio_int_cb, manager_data->interrupt_semaphore))
            JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO interrupt BUSY");
        furi_hal_gpio_enable_int_callback(manager_data->pin);
        manager_data->had_interrupt = true;
    }""")
    s = replace_once(s,
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);
    uint16_t millivolts =""",
        """    JsGpioPinInst* manager_data = JS_GET_CONTEXT(mjs);
    if(!js_gpio_e11_claim(manager_data))
        JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO analog pin BUSY");
    uint16_t millivolts =""")
    s = replace_once(s,
        """    if(furi_hal_pwm_is_running(manager_data->pwm_output)) {
        furi_hal_pwm_set_params(manager_data->pwm_output, frequency, duty);
    } else {
        furi_hal_pwm_start(manager_data->pwm_output, frequency, duty);
    }""",
        """    /* A generic JS pin claim and a native PWM claim must not overlap.
     * Also refuse to change another JS/native PWM owner's settings.
     */
    if(manager_data->lease_handle || manager_data->lease_fault)
        JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "GPIO pin owned as digital");
    if(furi_hal_pwm_is_running(manager_data->pwm_output)) {
        if(!manager_data->pwm_owned)
            JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "PWM BUSY");
        furi_hal_pwm_set_params(manager_data->pwm_output, frequency, duty);
    } else {
        if(manager_data->pwm_owned)
            JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "PWM ownership lost");
        furi_hal_pwm_start(manager_data->pwm_output, frequency, duty);
        if(!furi_hal_pwm_is_running(manager_data->pwm_output))
            JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, "PWM BUSY");
        manager_data->pwm_owned = true;
    }""")
    s = replace_once(s,
        """    furi_hal_pwm_stop(manager_data->pwm_output);
}""",
        """    if(manager_data->pwm_owned) {
        if(furi_hal_pwm_is_running(manager_data->pwm_output))
            furi_hal_pwm_stop(manager_data->pwm_output);
        manager_data->pwm_owned = false;
    }
}""")
    s = replace_once(s,
        """    JsGpioPinInst* manager_data = malloc(sizeof(JsGpioPinInst));
    manager_data->pin = pin_record->pin;""",
        """    JsGpioPinInst* manager_data = calloc(1U, sizeof(JsGpioPinInst));
    if(!manager_data)
        JS_ERROR_AND_RETURN(mjs, MJS_INTERNAL_ERROR, "GPIO allocation failed");
    manager_data->pin = pin_record->pin;""")
    s = replace_once(s,
        """            if(manager_data->had_interrupt) {
                furi_hal_gpio_disable_int_callback(manager_data->pin);
                furi_hal_gpio_remove_int_callback(manager_data->pin);
            }
            if(manager_data->pwm_output != FuriHalPwmOutputIdNone) {
                if(furi_hal_pwm_is_running(manager_data->pwm_output))
                    furi_hal_pwm_stop(manager_data->pwm_output);
            }
            furi_hal_gpio_init(manager_data->pin, GpioModeAnalog, GpioPullNo, GpioSpeedLow);""",
        """            if(manager_data->had_interrupt) {
                furi_hal_gpio_disable_int_callback(manager_data->pin);
                furi_hal_gpio_remove_int_callback(manager_data->pin);
            }
            if(manager_data->pwm_owned) {
                if(furi_hal_pwm_is_running(manager_data->pwm_output))
                    furi_hal_pwm_stop(manager_data->pwm_output);
                manager_data->pwm_owned = false;
            }
            /* A merely looked-up pin has never been ours: do not reset it!
             * A live E11 connector pin must still have our exact lease.
             */
            const uint32_t mask = js_gpio_e11_monitor_mask(manager_data->pin);
            if(manager_data->configured && (!mask || manager_data->lease_handle))
                furi_hal_gpio_init(
                    manager_data->pin, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
            if(manager_data->exti_lease_handle) {
                if(!furi_hal_resource_lease_release(
                       manager_data->exti_lease_handle, manager_data->exti_lease_mask)) {
                    /* Do not release the physical pin after an EXTI fault. */
                    manager_data->lease_fault = true;
                } else {
                    manager_data->exti_lease_handle = 0U;
                }
            }
            if(manager_data->lease_handle && !manager_data->lease_fault) {
                if(!furi_hal_resource_lease_release(
                       manager_data->lease_handle, manager_data->lease_mask)) {
                    /* Deliberately retain firmware reservation on error. */
                    manager_data->lease_fault = true;
                } else {
                    manager_data->lease_handle = 0U;
                }
            }""")
    return s

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    root=args.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PINNED: raise ValueError("Not pinned Momentum HEAD: "+head)
        status=subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines()
        dirty=set()
        for line in status:
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Unexpected/untracked firmware input")
            dirty.add(line[3:])
        if dirty!=EXPECTED_DIRTY:
            raise ValueError("Firmware change allowlist mismatch: "+repr(sorted(dirty)))
        header=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
        gpio=(root/"targets/f7/furi_hal/furi_hal_gpio.h").read_text()
        pwm=(root/"targets/f7/furi_hal/furi_hal_pwm.c").read_text()
        if ("FURI_HAL_LEASE_MONITOR_PA7" not in header or
            "FURI_HAL_LEASE_JS_EXTI3" not in header or
            "FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK" not in gpio or
            "LabMate E11 native PWM lease owner:" not in pwm):
            raise ValueError("Missing prerequisite lease/native PWM/IRQ patches")
        dest=root/TARGET
        new=patch_source(dest.read_text())
        print("E11 NATIVE JS GPIO EXACT SOURCE PREFLIGHT PASS")
        if args.apply:
            dest.write_text(new)
            print("PATCHED native JS GPIO: pin claims; occupied callback denial; unowned cleanup guarded")
        else:
            print("READ-ONLY CHECK: no modification")
        return 0
    except (OSError,subprocess.CalledProcessError,ValueError) as e:
        print("REFUSED native JS GPIO: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
