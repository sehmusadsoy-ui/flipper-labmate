#!/usr/bin/env python3
"""Execute real native NFC PA2/EXTI2 IRQ start, owned stop and event callback C.

GPIO callback CAS is independently compiled in OneWire test. No device NFC
RFID/USB/SD test performed here. Exact pinned Momentum applied source only.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#define UNUSED(x) ((void)(x))
#define FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2 ((1U<<29)|(1U<<8))
typedef struct {uint32_t pin;int port;} GpioPin;
static const GpioPin gpio_nfc_irq_rfid_pull={1U<<2,1};
typedef void(*GpioExtiCallback)(void*);
typedef struct {int unused;} FuriHalSpiBusHandle;
enum { FuriHalNfcEventInternalTypeIrq=2,GpioModeInterruptRise=1,
 GpioModeAnalog=2,GpioPullNo=0,GpioPullDown=1,GpioSpeedLow=0,
 GpioSpeedVeryHigh=4 };
static uint32_t event_count;
static uint32_t furi_hal_nfc_event_set(uint32_t ev) {
 assert(ev==FuriHalNfcEventInternalTypeIrq);return ++event_count;
}
static bool furi_hal_gpio_read_port_pin(int port,uint32_t pin) {
 assert(port==1 && pin==(1U<<2));return false;
}
static uint32_t st25r3916_get_irq(const FuriHalSpiBusHandle* handle) {
 (void)handle;return 0U;
}
static int claims,releases,mode_writes,adds,removes,denials;
static bool claim_ok,release_ok=true,add_ok=true,remove_ok=true;
static GpioExtiCallback active_cb;
static void* active_ctx;
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2);
 claims++;return claim_ok?919U:0U;
}
static bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask) {
 assert(h==919U && mask==FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2);
 releases++;return release_ok;
}
static bool furi_hal_gpio_try_add_int_callback(
 const GpioPin* gpio,GpioExtiCallback cb,void* ctx) {
 assert(gpio==&gpio_nfc_irq_rfid_pull && cb);
 adds++;
 if(!add_ok || active_cb) {denials++;return false;}
 active_cb=cb;active_ctx=ctx;
 return true;
}
static bool furi_hal_gpio_try_remove_int_callback(
 const GpioPin* gpio,GpioExtiCallback cb,void* ctx) {
 assert(gpio==&gpio_nfc_irq_rfid_pull && cb);
 removes++;
 if(!remove_ok || active_cb!=cb || active_ctx!=ctx) return false;
 active_cb=NULL;active_ctx=NULL;
 return true;
}
static void furi_hal_gpio_init(
 const GpioPin* gpio,int mode,int pull,int speed) {
 assert(gpio==&gpio_nfc_irq_rfid_pull);
 assert((mode==GpioModeInterruptRise && pull==GpioPullDown && speed==GpioSpeedVeryHigh) ||
        (mode==GpioModeAnalog && pull==GpioPullNo && speed==GpioSpeedLow));
 mode_writes++;
}
"""
RUN=r"""
static void unexpected(void* ctx) {(void)ctx;}
static void reset(void) {
 event_count=0;
 claims=releases=mode_writes=adds=removes=denials=0;
 claim_ok=false;release_ok=add_ok=remove_ok=true;
 active_cb=NULL;active_ctx=NULL;
 e11_nfc_irq_handle=0U;e11_nfc_irq_fault=false;
}
int main(void) {
 reset();
 assert(!furi_hal_nfc_try_init_gpio_isr());
 furi_hal_nfc_deinit_gpio_isr();
 furi_hal_nfc_int_callback(NULL);
 assert(!event_count && !mode_writes && !adds && !removes && claims==1);
 reset();claim_ok=true;add_ok=false;
 assert(!furi_hal_nfc_try_init_gpio_isr());
 assert(adds==1 && releases==1 && !mode_writes && !e11_nfc_irq_handle);
 furi_hal_nfc_deinit_gpio_isr();assert(removes==0);
 reset();claim_ok=true;
 active_cb=unexpected;active_ctx=(void*)7;
 assert(!furi_hal_nfc_try_init_gpio_isr());
 assert(active_cb==unexpected && active_ctx==(void*)7);
 assert(!mode_writes && !removes && releases==1);
 reset();claim_ok=true;add_ok=false;release_ok=false;
 assert(!furi_hal_nfc_try_init_gpio_isr());
 assert(e11_nfc_irq_fault && e11_nfc_irq_handle==919U);
 add_ok=true;
 assert(!furi_hal_nfc_try_init_gpio_isr() && claims==1);
 furi_hal_nfc_deinit_gpio_isr();assert(!mode_writes);
 reset();claim_ok=true;
 assert(furi_hal_nfc_try_init_gpio_isr());
 assert(active_cb==furi_hal_nfc_int_callback && !active_ctx &&
        e11_nfc_irq_handle==919U && mode_writes==1);
 assert(!furi_hal_nfc_try_init_gpio_isr() && claims==1);
 active_cb(active_ctx);assert(event_count==1);
 furi_hal_nfc_deinit_gpio_isr();
 assert(!active_cb && !e11_nfc_irq_handle && mode_writes==2 &&
        releases==1 && removes==1);
 furi_hal_nfc_deinit_gpio_isr();assert(removes==1 && mode_writes==2);
 assert(furi_hal_nfc_try_init_gpio_isr());
 furi_hal_nfc_deinit_gpio_isr();
 reset();claim_ok=true;
 assert(furi_hal_nfc_try_init_gpio_isr());
 active_cb=unexpected;
 furi_hal_nfc_deinit_gpio_isr();
 assert(e11_nfc_irq_fault && e11_nfc_irq_handle==919U && releases==0 &&
        mode_writes==1 && active_cb==unexpected);
 reset();claim_ok=true;release_ok=false;
 assert(furi_hal_nfc_try_init_gpio_isr());
 furi_hal_nfc_deinit_gpio_isr();
 assert(e11_nfc_irq_fault && e11_nfc_irq_handle==919U && !active_cb);
 int before=mode_writes;
 furi_hal_nfc_deinit_gpio_isr();
 assert(mode_writes==before && !furi_hal_nfc_try_init_gpio_isr());
 puts("E11 native NFC original IRQ/EXTI C: BUSY/STOP/callback/sticky PASS");
 return 0;
}
"""
MASK=r"""
#define CHECK(x) do{if(!(x)){fprintf(stderr,"NFC allocator fail line %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t n=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2);
 CHECK(n);
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PB2));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_JS_EXTI2));
 CHECK(!furi_hal_resource_lease_release(n,FURI_HAL_LEASE_JS_EXTI2));
 CHECK(furi_hal_resource_lease_release(n,FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2));
 uint32_t other=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14);
 CHECK(other); /* Different EXTI14 and physical PB14, no false alias */
 CHECK(furi_hal_resource_lease_release(other,FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14));
 puts("E11 native firmware NFC PA2/EXTI2 vs PB2/JS EXT2 allocator PASS");
 return 0;
}
"""
def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    src=(root/"targets/f7/furi_hal/furi_hal_nfc_irq.c").read_text()
    nfc=(root/"targets/f7/furi_hal/furi_hal_nfc.c").read_text()
    internal=(root/"targets/f7/furi_hal/furi_hal_nfc_i.h").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    marker="/* E11 native NFC PA2+EXTI2 IRQ owner. */"
    assert marker in src
    assert "FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2" in h
    assert "mask == FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2" in r
    assert "bool furi_hal_nfc_try_init_gpio_isr(void);" in internal
    assert nfc.count("if(!furi_hal_nfc_try_init_gpio_isr())")==2
    assert 'error=FuriHalNfcErrorBusy;' in nfc
    assert "furi_hal_nfc_timers_deinit(); /* Undo only successfully held timers. */" in nfc
    assert "/* E11 native NFC PA2+EXTI2 IRQ owner. */" in src
    assert src.index("furi_hal_resource_lease_try_acquire(") < src.index(
        "furi_hal_gpio_try_add_int_callback(") < src.index(
        "furi_hal_gpio_init(")
    assert "if(!e11_nfc_irq_handle || e11_nfc_irq_fault) return;" in src
    native=src[src.index(marker):]
    with tempfile.TemporaryDirectory(prefix="e11_nfc_irq_") as f:
        d=Path(f);exe=d/"test"
        (d/"native.c").write_text(STUB+"\n"+native+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic",str(d/"native.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        pre=r"""
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static pthread_mutex_t critical=PTHREAD_MUTEX_INITIALIZER;
#define FURI_CRITICAL_ENTER() do{if(pthread_mutex_lock(&critical))abort();}while(0)
#define FURI_CRITICAL_EXIT() do{if(pthread_mutex_unlock(&critical))abort();}while(0)
"""
        masks=h[h.index("enum {\n    FuriHalLeaseTim1"):h.index("/* Returns unique nonzero")]
        allocator=r[r.index("/* Firmware-owned E11 lease primitive"):r.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
        (d/"allocator.c").write_text(pre+masks+allocator+MASK)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic","-pthread",str(d/"allocator.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 native NFC PA2/EXTI2 original C + shared allocator HOST PASS")
    print("NFC RF/device tests, legacy EXTI clients and recovery remain OPEN.")

if __name__=="__main__":
    main()
