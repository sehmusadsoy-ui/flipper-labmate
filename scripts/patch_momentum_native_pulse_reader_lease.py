#!/usr/bin/env python3
"""E11 native PulseReader TIM2 + DMA4/5 + DMAMUX0 + GPIO/EXTI lease.

Pinned Momentum source patch only; no USB/flash or Stable changes.
Limited to canonical eight external connector GPIO pointers. This does not
intercept other direct-register clients, and cannot make their races safe.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

PINNED="d3f89dfe2ef6b01839201598e9be1590cba80322"
HEADER="targets/f7/furi_hal/furi_hal_resources.h"
SOURCE="targets/f7/furi_hal/furi_hal_resources.c"
PULSE="lib/pulse_reader/pulse_reader.c"
EXPECTED_DIRTY={
    "targets/furi_hal_include/furi_hal_i2c.h",
    "targets/f7/furi_hal/furi_hal_i2c.c",
    "targets/f7/furi_hal/furi_hal_resources.h",
    "targets/f7/furi_hal/furi_hal_resources.c",
    "targets/f7/furi_hal/furi_hal_gpio.h",
    "targets/f7/furi_hal/furi_hal_gpio.c",
    "targets/f7/furi_hal/furi_hal_pwm.c",
    "targets/f7/api_symbols.csv",
    "applications/system/js_app/modules/js_gpio.c",
}
MARKER="/* LabMate E11 native PulseReader single composite-resource claim. */"
HEADER_ADDITION="""/* Native PulseReader also uses TIM2 + DMA1 channels 4 and 5 +
 * DMAMUX request generator 0 and the selected external pin's EXTI line.
 * These claims guard COOPERATING clients, not direct LL accesses.
 */
enum {
    FuriHalLeaseDma1Ch4 = (1U << 16),
    FuriHalLeaseDma1Ch5 = (1U << 17),
    FuriHalLeaseDmamuxReq0 = (1U << 18),
    FuriHalLeaseExti3 = (1U << 19),
    FuriHalLeaseExti6 = (1U << 20),
    FuriHalLeaseExti7 = (1U << 21),
};
#define FURI_HAL_LEASE_PULSE_CORE (FuriHalLeaseTim2 | FuriHalLeaseDma1Ch4 | FuriHalLeaseDma1Ch5 | FuriHalLeaseDmamuxReq0)
/* Nonconnector pins keep the historical native reader capability.
 * CORE owns timer/DMA only: their GPIO/EXTI paths remain unarbitrated.
 */
#define FURI_HAL_LEASE_PULSE_NONCONNECTOR FURI_HAL_LEASE_PULSE_CORE
#define FURI_HAL_LEASE_PULSE_PC0 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePc0 | FuriHalLeaseExti0)
#define FURI_HAL_LEASE_PULSE_PC1 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePc1 | FuriHalLeaseExti1)
#define FURI_HAL_LEASE_PULSE_PC3 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePc3 | FuriHalLeaseExti3)
#define FURI_HAL_LEASE_PULSE_PB2 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePb2 | FuriHalLeaseExti2)
#define FURI_HAL_LEASE_PULSE_PB3 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePb3 | FuriHalLeaseExti3)
#define FURI_HAL_LEASE_PULSE_PA4 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePa4 | FuriHalLeaseExti4)
#define FURI_HAL_LEASE_PULSE_PA6 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePa6 | FuriHalLeaseExti6)
#define FURI_HAL_LEASE_PULSE_PA7 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePa7 | FuriHalLeaseExti7)

"""
SOURCE_ALLOW="""           mask == FURI_HAL_LEASE_PULSE_NONCONNECTOR ||
           mask == FURI_HAL_LEASE_PULSE_PC0 ||
           mask == FURI_HAL_LEASE_PULSE_PC1 ||
           mask == FURI_HAL_LEASE_PULSE_PC3 ||
           mask == FURI_HAL_LEASE_PULSE_PB2 ||
           mask == FURI_HAL_LEASE_PULSE_PB3 ||
           mask == FURI_HAL_LEASE_PULSE_PA4 ||
           mask == FURI_HAL_LEASE_PULSE_PA6 ||
           mask == FURI_HAL_LEASE_PULSE_PA7 ||
"""
PULSE_HELPER="""/* LabMate E11 native PulseReader single composite-resource claim. */
static uint32_t pulse_reader_e11_mask(const GpioPin* gpio) {
    if(!gpio) return 0U;
    if(gpio == &gpio_ext_pc0 || (gpio->port == gpio_ext_pc0.port &&
       gpio->pin == gpio_ext_pc0.pin)) return FURI_HAL_LEASE_PULSE_PC0;
    if(gpio == &gpio_ext_pc1 || (gpio->port == gpio_ext_pc1.port &&
       gpio->pin == gpio_ext_pc1.pin)) return FURI_HAL_LEASE_PULSE_PC1;
    if(gpio == &gpio_ext_pc3 || (gpio->port == gpio_ext_pc3.port &&
       gpio->pin == gpio_ext_pc3.pin)) return FURI_HAL_LEASE_PULSE_PC3;
    if(gpio == &gpio_ext_pb2 || (gpio->port == gpio_ext_pb2.port &&
       gpio->pin == gpio_ext_pb2.pin)) return FURI_HAL_LEASE_PULSE_PB2;
    if(gpio == &gpio_ext_pb3 || (gpio->port == gpio_ext_pb3.port &&
       gpio->pin == gpio_ext_pb3.pin)) return FURI_HAL_LEASE_PULSE_PB3;
    if(gpio == &gpio_ext_pa4 || (gpio->port == gpio_ext_pa4.port &&
       gpio->pin == gpio_ext_pa4.pin)) return FURI_HAL_LEASE_PULSE_PA4;
    if(gpio == &gpio_ext_pa6 || (gpio->port == gpio_ext_pa6.port &&
       gpio->pin == gpio_ext_pa6.pin)) return FURI_HAL_LEASE_PULSE_PA6;
    if(gpio == &gpio_ext_pa7 || (gpio->port == gpio_ext_pa7.port &&
       gpio->pin == gpio_ext_pa7.pin)) return FURI_HAL_LEASE_PULSE_PA7;
    /* Other native GPIOs still use the legacy reader. Claim shared
     * TIM2/DMA/DMAMUX resources, but cannot promise pin/EXTI isolation.
     */
    return FURI_HAL_LEASE_PULSE_NONCONNECTOR;
}

"""
def replace_one(s: str,old: str,new: str) -> str:
    if s.count(old)!=1:
        raise ValueError("Source signature not unique: "+repr(old[:100]))
    return s.replace(old,new,1)

def patch(h: str,c: str,p: str) -> tuple[str,str,str]:
    if MARKER in p or "FURI_HAL_LEASE_PULSE_CORE" in h:
        raise ValueError("Already applied")
    h=replace_one(h,"/* Passive GPIO Monitor pin-only claims.",
        HEADER_ADDITION+"/* Passive GPIO Monitor pin-only claims.")
    c=replace_one(c,
        "           mask == FURI_HAL_LEASE_MONITOR_PA7;",
        SOURCE_ALLOW+"           mask == FURI_HAL_LEASE_MONITOR_PA7;")
    p=replace_one(p,"#include <furi_hal_gpio.h>",
        "#include <furi_hal_gpio.h>\n#include <furi_hal_resources.h>")
    p=replace_one(p,"    GpioPull pull;\n    LL_DMA_InitTypeDef",
        """    GpioPull pull;
    uint32_t firmware_lease_handle;
    uint32_t firmware_lease_mask;
    bool capture_active;
    bool firmware_lease_fault;
    LL_DMA_InitTypeDef""")
    p=replace_one(p,"#define GPIO_PIN_MAP(pin, prefix)",
        PULSE_HELPER+"#define GPIO_PIN_MAP(pin, prefix)")
    p=replace_one(p,
        """    signal->timer_value = 0;
    signal->pos = 0;""",
        """    signal->timer_value = 0;
    signal->pos = 0;
    signal->firmware_lease_handle = 0U;
    signal->firmware_lease_mask = 0U;
    signal->firmware_lease_fault = false;
    signal->capture_active = false;""")
    p=replace_one(p,
        """    free(signal->timer_buffer);
    free(signal->gpio_buffer);""",
        """    /* The legacy free() could discard an active DMA capture.
     * Only shut down if this PulseReader still owns the exact lease.
     */
    if(signal->capture_active) pulse_reader_stop(signal);
    /* After a hijack or release failure a DMA target may remain live.
     * Fail closed: leak its buffers rather than risk DMA use-after-free.
     */
    if(signal->firmware_lease_fault) return;
    free(signal->timer_buffer);
    free(signal->gpio_buffer);""")
    p=replace_one(p,
        """uint32_t pulse_reader_samples(PulseReader* signal) {
    uint32_t dma_pos""",
        """uint32_t pulse_reader_samples(PulseReader* signal) {
    if(!signal || !signal->capture_active || signal->firmware_lease_fault)
        return 0U;
    uint32_t dma_pos""")
    p=replace_one(p,
        """void pulse_reader_stop(PulseReader* signal) {
    LL_DMA_DisableChannel""",
        """void pulse_reader_stop(PulseReader* signal) {
    if(!signal || !signal->capture_active || signal->firmware_lease_fault ||
       !signal->firmware_lease_handle) return;
    /* An unrelated native service may have disabled TIM2. The original
     * bus_disable asserts on an already disabled bus; don't corrupt DMA
     * or a foreign GPIO during such a takeover. Keep this claim sticky.
     */
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM2)) {
        signal->capture_active = false;
        signal->firmware_lease_fault = true;
        return;
    }
    LL_DMA_DisableChannel""")
    p=replace_one(p,
        """    furi_hal_gpio_init_simple(signal->gpio, GpioModeAnalog);
}

void pulse_reader_start""",
        """    furi_hal_gpio_init_simple(signal->gpio, GpioModeAnalog);
    signal->capture_active = false;
    if(furi_hal_resource_lease_release(
           signal->firmware_lease_handle, signal->firmware_lease_mask)) {
        signal->firmware_lease_handle = 0U;
        signal->firmware_lease_mask = 0U;
    } else {
        /* Never advertise a free resource if firmware release failed. */
        signal->firmware_lease_fault = true;
    }
}

void pulse_reader_start""")
    p=replace_one(p,
        """void pulse_reader_start(PulseReader* signal) {
    /* configure DMA""",
        """void pulse_reader_start(PulseReader* signal) {
    if(!signal || signal->capture_active || signal->firmware_lease_fault ||
       signal->firmware_lease_handle) return;
    const uint32_t mask = pulse_reader_e11_mask(signal->gpio);
    if(!mask) return;
    const uint32_t lease = furi_hal_resource_lease_try_acquire(mask);
    if(!lease) return; /* BUSY: no TIM/DMA/DMAMUX/GPIO writes */
    /* Cooperative lease cannot cover legacy direct-register users:
     * preflight the timer bus and both active DMA channels as well.
     */
    if(furi_hal_bus_is_enabled(FuriHalBusTIM2) ||
       LL_DMA_IsEnabledChannel(DMA1, LL_DMA_CHANNEL_4) ||
       LL_DMA_IsEnabledChannel(DMA1, LL_DMA_CHANNEL_5)) {
        if(!furi_hal_resource_lease_release(lease, mask)) {
            signal->firmware_lease_handle = lease;
            signal->firmware_lease_mask = mask;
            signal->firmware_lease_fault = true;
        }
        return;
    }
    signal->firmware_lease_handle = lease;
    signal->firmware_lease_mask = mask;
    signal->capture_active = true;
    /* configure DMA""")
    p=replace_one(p,
        """uint32_t pulse_reader_receive(PulseReader* signal, int timeout_us) {
    uint32_t start_time""",
        """uint32_t pulse_reader_receive(PulseReader* signal, int timeout_us) {
    if(!signal || !signal->capture_active || signal->firmware_lease_fault)
        return PULSE_READER_NO_EDGE;
    uint32_t start_time""")
    return h,c,p

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args()
    root=a.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PINNED: raise ValueError("wrong pinned Momentum HEAD: "+head)
        lines=subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines()
        dirty=set()
        for line in lines:
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("untracked or renamed firmware input")
            dirty.add(line[3:])
        if dirty!=EXPECTED_DIRTY:
            raise ValueError("Unexpected firmware prepatch state: "+repr(sorted(dirty)))
        base=(root/HEADER).read_text()
        if "FURI_HAL_RESOURCE_LEASE_API_V1" not in base:
            raise ValueError("firmware lease API prerequisite absent")
        if "LabMate E11 native JS GPIO connector-owner contract." not in (
            root/"applications/system/js_app/modules/js_gpio.c").read_text():
            raise ValueError("native JS prerequisite absent")
        hs,cs,ps=patch(base,(root/SOURCE).read_text(),(root/PULSE).read_text())
        print("E11 NATIVE PULSE TIM2/DMAMUX/DMA EXTI SOURCE CHECK PASS")
        if a.apply:
            for path,content in ((HEADER,hs),(SOURCE,cs),(PULSE,ps)):
                (root/path).write_text(content)
            print("PATCHED source only; no app install, no USB, no firmware flash.")
        else:
            print("READ ONLY; no source modified.")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("REFUSED E11 native PulseReader: "+str(e),file=sys.stderr)
        return 1
if __name__=="__main__": raise SystemExit(main())
