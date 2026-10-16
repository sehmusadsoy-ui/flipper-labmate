#!/usr/bin/env python3
"""E11 pinned native OneWireSlave PB14+EXTI14 and owned callback lifecycle.

Adds GPIO callback compare-and-register/compare-and-remove primitives, never
replacing a pre-existing EXTI handler. Firmware source only; no flash/SD/USB.
Other OneWire GPIO choices and protocol-layer BUSY display remain OPEN.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_subghz_tx_lease import EXPECTED as TX_PRE, H, R, S as SUB

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
GH="targets/f7/furi_hal/furi_hal_gpio.h"
GC="targets/f7/furi_hal/furi_hal_gpio.c"
OH="lib/one_wire/one_wire_slave.h"
OC="lib/one_wire/one_wire_slave.c"
DALLAS="lib/ibutton/protocols/dallas/protocol_group_dallas.c"
API="targets/f7/api_symbols.csv"
MARK="/* E11 native OneWire PB14+EXTI14 owner. */"
EXPECTED=TX_PRE | {H,R,SUB}

def once(src:str,old:str,new:str)->str:
    if src.count(old)!=1:
        raise ValueError("Unreviewed pinned OneWire/GPIO source anchor "+repr(old[:95]))
    return src.replace(old,new,1)

def patch(h:str,r:str,gh:str,gc:str,oh:str,oc:str,dallas:str,api:str):
    if MARK in oc or "FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14" in h:
        raise ValueError("OneWire stage already present")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3 (FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2|FuriHalLeasePb3)\n",
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3 (FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2|FuriHalLeasePb3)\n"
        "/* Internal iButton 1-Wire GPIO PB14 shares EXTI14 on all ports. */\n"
        "enum { FuriHalLeasePb14 = (1U << 27), FuriHalLeaseExti14 = (1U << 28) };\n"
        "#define FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14 (FuriHalLeasePb14|FuriHalLeaseExti14)\n")
    r=once(r,
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14 ||\n")
    gh=once(gh,
        "void furi_hal_gpio_add_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx);",
        "void furi_hal_gpio_add_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx);\n"
        "/* E11: atomically refuse an occupied EXTI slot without overwriting it. */\n"
        "bool furi_hal_gpio_try_add_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx);\n"
        "/* E11: remove only the expected registered callback + matching ctx. */\n"
        "bool furi_hal_gpio_try_remove_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx);")
    gc=once(gc,
        "void furi_hal_gpio_add_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx) {",
        """/* E11 compare-and-register, does not alter the existing strict legacy API. */
bool furi_hal_gpio_try_add_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx) {
    if(!gpio || !cb) return false;
    FURI_CRITICAL_ENTER();
    const uint8_t pin_num=furi_hal_gpio_get_pin_num(gpio);
    if(gpio_interrupt[pin_num].callback != NULL) {
        FURI_CRITICAL_EXIT();
        return false;
    }
    gpio_interrupt[pin_num].callback=cb;
    gpio_interrupt[pin_num].context=ctx;
    LL_EXTI_EnableIT_0_31(GET_EXTI_LINE(gpio->pin));
    FURI_CRITICAL_EXIT();
    return true;
}

/* E11 compare-and-remove: never disable somebody else's EXTI callback. */
bool furi_hal_gpio_try_remove_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx) {
    if(!gpio || !cb) return false;
    FURI_CRITICAL_ENTER();
    const uint8_t pin_num=furi_hal_gpio_get_pin_num(gpio);
    if(gpio_interrupt[pin_num].callback != cb ||
       gpio_interrupt[pin_num].context != ctx) {
        FURI_CRITICAL_EXIT();
        return false;
    }
    LL_EXTI_DisableIT_0_31(GET_EXTI_LINE(gpio->pin));
    LL_EXTI_ClearFlag_0_31(GET_EXTI_LINE(gpio->pin));
    gpio_interrupt[pin_num].callback=NULL;
    gpio_interrupt[pin_num].context=NULL;
    FURI_CRITICAL_EXIT();
    return true;
}

void furi_hal_gpio_add_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx) {""")
    oc=once(oc,
        '#include <furi_hal.h>\n',
        '#include <furi_hal.h>\n#include <furi_hal_resources.h>\n')
    oc=once(oc,
        """    void* command_callback_context;
};""",
        """    void* command_callback_context;

    /* E11 native OneWire PB14+EXTI14 owner. */
    uint32_t e11_owner;
    bool e11_fault;
};""")
    oc=once(oc,
        """static void onewire_slave_exti_callback(void* context) {
    OneWireSlave* bus = context;

    const volatile bool input_state""",
        """static void onewire_slave_exti_callback(void* context) {
    OneWireSlave* bus = context;
    /* Denied or stale callback must neither spin nor drive GPIO. */
    if(!bus->e11_owner || bus->e11_fault) return;

    const volatile bool input_state""")
    oc=once(oc,
        """    bus->error = OneWireSlaveErrorNone;

    return bus;""",
        """    bus->error = OneWireSlaveErrorNone;
    bus->e11_owner = 0U;
    bus->e11_fault = false;

    return bus;""")
    oc=once(oc,
        """    onewire_slave_stop(bus);
    free(bus);
}""",
        """    onewire_slave_stop(bus);
    /* A failed exact release / replaced callback must not leave
     * an EXTI ISR pointing at freed memory. Deliberate fail-closed
     * leak is safer than a use-after-free on an unknown native owner.
     */
    if(bus->e11_owner) return;
    free(bus);
}""")
    oc=once(oc,
        """void onewire_slave_start(OneWireSlave* bus) {
    furi_check(bus);

    furi_hal_gpio_add_int_callback(bus->gpio_pin, onewire_slave_exti_callback, bus);
    furi_hal_gpio_write(bus->gpio_pin, true);
    furi_hal_gpio_init(bus->gpio_pin, GpioModeInterruptRiseFall, GpioPullNo, GpioSpeedLow);
}

void onewire_slave_stop(OneWireSlave* bus) {
    furi_check(bus);

    furi_hal_gpio_write(bus->gpio_pin, true);
    furi_hal_gpio_init(bus->gpio_pin, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
    furi_hal_gpio_remove_int_callback(bus->gpio_pin);
}""",
        """bool onewire_slave_try_start(OneWireSlave* bus) {
    if(!bus || bus->e11_owner || bus->e11_fault) return false;
    /* This stage supports the pinned internal iButton PB14 only.
     * An unknown gpio_pin may be external or an internal system IRQ
     * and MUST NOT be operated without a reviewed pin+EXTI mask.
     */
    if(bus->gpio_pin != &gpio_ibutton) return false;
    const uint32_t lease=furi_hal_resource_lease_try_acquire(
        FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14);
    if(!lease) return false;
    bus->e11_owner=lease;
    /* Callback slot occupancy is atomically checked before ANY pin
     * output/mode change. No arbitrary stale EXTI callback replacement.
     */
    if(!furi_hal_gpio_try_add_int_callback(
           bus->gpio_pin, onewire_slave_exti_callback, bus)) {
        if(furi_hal_resource_lease_release(
               lease,FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14)) {
            bus->e11_owner=0U;
        } else {
            bus->e11_fault=true;
        }
        return false;
    }
    furi_hal_gpio_write(bus->gpio_pin, true);
    furi_hal_gpio_init(bus->gpio_pin, GpioModeInterruptRiseFall, GpioPullNo, GpioSpeedLow);
    return true;
}

/* Keep the published legacy void interface for existing users. */
void onewire_slave_start(OneWireSlave* bus) {
    (void)onewire_slave_try_start(bus);
}

void onewire_slave_stop(OneWireSlave* bus) {
    furi_check(bus);
    if(!bus->e11_owner || bus->e11_fault) return;
    /* No GPIO reconfiguration if a foreign callback replaced ours. */
    if(!furi_hal_gpio_try_remove_int_callback(
           bus->gpio_pin, onewire_slave_exti_callback, bus)) {
        bus->e11_fault=true;
        return;
    }
    furi_hal_gpio_write(bus->gpio_pin, true);
    furi_hal_gpio_init(bus->gpio_pin, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
    const uint32_t owner=bus->e11_owner;
    if(furi_hal_resource_lease_release(
           owner,FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14)) {
        bus->e11_owner=0U;
    } else {
        bus->e11_fault=true;
    }
}""")
    oh=once(oh,
        "void onewire_slave_start(OneWireSlave* bus);",
        "void onewire_slave_start(OneWireSlave* bus);\n"
        "/* E11: returns false before GPIO writes if PB14 or EXTI14 is BUSY. */\n"
        "bool onewire_slave_try_start(OneWireSlave* bus);")
    dallas=once(dallas,
        """    ibutton_protocols_dallas[id]->emulate(bus, data);
    onewire_slave_start(bus);
}""",
        """    ibutton_protocols_dallas[id]->emulate(bus, data);
    /* The group v1 emulate callback is void: keep ABI, but refuse
     * silently driving a foreign pin and emit an explicit BUSY log.
     */
    if(!onewire_slave_try_start(bus)) {
        FURI_LOG_W("iButtonDallas", "OneWire PB14/EXTI14 BUSY; emulation not started");
    }
}""")
    api=once(api,
        'Function,+,furi_hal_gpio_add_int_callback,void,"const GpioPin*, GpioExtiCallback, void*"\n',
        'Function,+,furi_hal_gpio_add_int_callback,void,"const GpioPin*, GpioExtiCallback, void*"\n'
        'Function,+,furi_hal_gpio_try_add_int_callback,_Bool,"const GpioPin*, GpioExtiCallback, void*"\n'
        'Function,+,furi_hal_gpio_try_remove_int_callback,_Bool,"const GpioPin*, GpioExtiCallback, void*"\n')
    api=once(api,
        'Function,+,onewire_slave_start,void,OneWireSlave*\n',
        'Function,+,onewire_slave_start,void,OneWireSlave*\n'
        'Function,+,onewire_slave_try_start,_Bool,OneWireSlave*\n')
    return h,r,gh,gc,oh,oc,dallas,api

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args();root=args.firmware_root.resolve()
    try:
        sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if sha!=PIN: raise ValueError("Unpinned Momentum checkout")
        seen=set()
        for line in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],
                                            text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Renamed/untracked Momentum source forbidden")
            seen.add(line[3:])
        if seen!=EXPECTED:
            raise ValueError("Unreviewed native source "+repr(sorted(seen^EXPECTED)))
        paths=(H,R,GH,GC,OH,OC,DALLAS,API)
        before=[(root/x).read_text(encoding="utf-8") for x in paths]
        after=patch(*before)
        print("E11 ONE-WIRE PB14+EXTI14 PINNED SOURCE PREFLIGHT PASS")
        if args.apply:
            for x,s in zip(paths,after):
                (root/x).write_text(s,encoding="utf-8")
            print("ONE-WIRE SOURCE PATCH ONLY; NO FLASH, DEVICE OR SD WRITES")
        else:
            print("READ ONLY; NONE WRITTEN")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as ex:
        print("E11 ONE-WIRE SOURCE REFUSED: "+str(ex),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
