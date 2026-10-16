#!/usr/bin/env python3
"""Compile genuine patched OneWire START/STOP, GPIO callback CAS and allocator C.

Physical iButton GPIO/EXTI tests are separate. No device/flash/writes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
#define furi_check(x) assert(x)
#define FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14 ((1U<<27)|(1U<<28))
enum { GpioModeInterruptRiseFall=1,GpioModeAnalog=2,GpioPullNo=0,GpioSpeedLow=0 };
typedef struct {uint32_t pin;int port;} GpioPin;
typedef void (*GpioExtiCallback)(void*);
typedef struct {GpioExtiCallback callback;void* context;} IrqSlot;
static IrqSlot gpio_interrupt[16];
static const GpioPin gpio_ibutton={1U<<14,2};
static const GpioPin other_gpio={1U<<3,2};
static int irq_enables,irq_disables,irq_clears,gpio_writes,mode_writes;
static int claims,releases,freed;
static bool claim_ok,release_ok=true;
static int furi_hal_gpio_get_pin_num(const GpioPin* gpio) {
 assert(gpio);return gpio==&gpio_ibutton?14:3;
}
#define GET_EXTI_LINE(x) (x)
#define LL_EXTI_EnableIT_0_31(x) ((void)(x),++irq_enables)
#define LL_EXTI_DisableIT_0_31(x) ((void)(x),++irq_disables)
#define LL_EXTI_ClearFlag_0_31(x) ((void)(x),++irq_clears)
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14);
 claims++;return claim_ok?713U:0U;
}
static bool furi_hal_resource_lease_release(uint32_t owner,uint32_t mask) {
 assert(owner==713U && mask==FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14);
 releases++;return release_ok;
}
static void furi_hal_gpio_write(const GpioPin* pin,bool high) {
 assert(pin==&gpio_ibutton && high);gpio_writes++;
}
static void furi_hal_gpio_init(
 const GpioPin* pin,int mode,int pull,int speed) {
 assert(pin==&gpio_ibutton && (mode==1||mode==2) && pull==0 && speed==0);
 mode_writes++;
}
typedef enum { OneWireSlaveErrorNone=0 } OneWireSlaveError;
typedef struct {int marker;} OneWireSlaveTimings;
static const OneWireSlaveTimings onewire_slave_timings_normal={1};
typedef struct OneWireSlave {
 const GpioPin* gpio_pin;
 const OneWireSlaveTimings* timings;
 OneWireSlaveError error;
 uint32_t e11_owner;
 bool e11_fault;
} OneWireSlave;
static void onewire_slave_exti_callback(void* context) {(void)context;}
void onewire_slave_stop(OneWireSlave* bus);
bool onewire_slave_try_start(OneWireSlave* bus);
"""
RUN=r"""
static void foreign(void* ctx) {(void)ctx;}
static void reset(void) {
 irq_enables=irq_disables=irq_clears=gpio_writes=mode_writes=0;
 claims=releases=freed=0;claim_ok=false;release_ok=true;
 for(int i=0;i<16;i++) {
   gpio_interrupt[i].callback=NULL;gpio_interrupt[i].context=NULL;
 }
}
int main(void) {
 reset();
 OneWireSlave* bus=onewire_slave_alloc(&gpio_ibutton);
 assert(bus && !bus->e11_owner && !bus->e11_fault);
 onewire_slave_start(bus);
 onewire_slave_stop(bus);
 assert(claims==1 && !irq_enables && !gpio_writes && !mode_writes);
 /* True native occupied callback: preserve it without writes or crash. */
 reset();claim_ok=true;
 gpio_interrupt[14].callback=foreign;gpio_interrupt[14].context=(void*)3;
 assert(!onewire_slave_try_start(bus));
 assert(gpio_interrupt[14].callback==foreign && gpio_interrupt[14].context==(void*)3);
 assert(!irq_enables && !irq_disables && !irq_clears &&
        !gpio_writes && !mode_writes && releases==1);
 onewire_slave_stop(bus);assert(!irq_disables && !gpio_writes);
 /* Reject non-PB14 internal/external pins before allocation. */
 reset();claim_ok=true;
 OneWireSlave* invalid=onewire_slave_alloc(&other_gpio);
 assert(!onewire_slave_try_start(invalid) && claims==0 && !gpio_writes);
 onewire_slave_free(invalid);
 /* Valid native START, callback ownership and exact STOP. */
 reset();claim_ok=true;
 assert(onewire_slave_try_start(bus));
 assert(bus->e11_owner==713U && gpio_interrupt[14].callback==onewire_slave_exti_callback);
 assert(irq_enables==1 && gpio_writes==1 && mode_writes==1);
 assert(!onewire_slave_try_start(bus) && claims==1);
 onewire_slave_stop(bus);
 assert(!bus->e11_owner && releases==1 && irq_disables==1 && irq_clears==1);
 assert(!gpio_interrupt[14].callback && gpio_writes==2 && mode_writes==2);
 int old_writes=gpio_writes;
 onewire_slave_stop(bus);assert(gpio_writes==old_writes && releases==1);
 /* A replaced callback is never disabled/removed (sticky failure). */
 reset();claim_ok=true;
 assert(onewire_slave_try_start(bus));
 gpio_interrupt[14].callback=foreign;
 old_writes=gpio_writes;
 onewire_slave_stop(bus);
 assert(bus->e11_fault && bus->e11_owner==713U && releases==0);
 assert(gpio_interrupt[14].callback==foreign && gpio_writes==old_writes);
 assert(irq_disables==0);
 onewire_slave_free(bus); /* deliberate fail-closed retention, no UAF */
 assert(bus->e11_owner==713U && bus->e11_fault);
 /* New clean bus for failed-release path. */
 reset();claim_ok=true;release_ok=false;
 bus=onewire_slave_alloc(&gpio_ibutton);
 assert(onewire_slave_try_start(bus));
 onewire_slave_stop(bus);
 assert(bus->e11_owner==713U && bus->e11_fault &&
        !gpio_interrupt[14].callback && releases==1);
 old_writes=gpio_writes;
 assert(!onewire_slave_try_start(bus));
 onewire_slave_stop(bus);assert(gpio_writes==old_writes);
 onewire_slave_free(bus);
 puts("E11 actual OneWire + native GPIO compare/add/remove C DENY/STOP PASS");
 return 0;
}
"""
MASK=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"OneWire allocator fail line %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14);
 REQUIRE(a);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14));
 REQUIRE(!furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE));
 REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14));
 REQUIRE(!furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14));
 uint32_t b=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_JS_EXTI2);
 REQUIRE(b); /* EXTI2 is PA2/PB2 alias, independent of EXTI14 */
 REQUIRE(furi_hal_resource_lease_release(b,FURI_HAL_LEASE_JS_EXTI2));
 puts("E11 real firmware allocator PB14+EXTI14 exact claim/release PASS");
 return 0;
}
"""

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"lib/one_wire/one_wire_slave.c").read_text()
    gh=(root/"targets/f7/furi_hal/furi_hal_gpio.h").read_text()
    gc=(root/"targets/f7/furi_hal/furi_hal_gpio.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    d=(root/"lib/ibutton/protocols/dallas/protocol_group_dallas.c").read_text()
    assert "/* E11 native OneWire PB14+EXTI14 owner. */" in s
    assert "FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14" in h
    assert "mask == FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14" in r
    assert "Function,+,onewire_slave_try_start,_Bool,OneWireSlave*" in api
    assert "Function,+,furi_hal_gpio_try_add_int_callback,_Bool," in api
    assert "Function,+,furi_hal_gpio_try_remove_int_callback,_Bool," in api
    assert "onewire_slave_try_start(bus)" in d
    assert "void onewire_slave_start(OneWireSlave* bus)" in s
    assert "bool furi_hal_gpio_try_add_int_callback(" in gh
    assert "bool furi_hal_gpio_try_remove_int_callback(" in gh
    assert "if(!bus->e11_owner || bus->e11_fault) return;" in s
    gpio=gc[gc.index("/* Atomically refuse a full EXTI line"):gc.index("void furi_hal_gpio_add_int_callback(")]
    start=s[s.index("OneWireSlave* onewire_slave_alloc("):s.index("void onewire_slave_set_reset_callback(")]
    assert start.index("furi_hal_resource_lease_try_acquire(") < start.index("furi_hal_gpio_try_add_int_callback(")
    assert start.index("furi_hal_gpio_try_add_int_callback(") < start.index("furi_hal_gpio_write(bus->gpio_pin, true);")
    assert "if(!furi_hal_gpio_try_remove_int_callback(" in start
    with tempfile.TemporaryDirectory(prefix="e11_onewire_pb14_") as t:
        td=Path(t);exe=td/"test";driver=td/"driver.c"
        driver.write_text(STUB+"\n"+gpio+"\n"+start+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic",str(driver),"-o",str(exe)],check=True)
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
        (td/"alloc.c").write_text(pre+masks+allocator+MASK)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(td/"alloc.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("OneWire native GPIO/EXTI callback CAS + production START/STOP C HOST PASS")
    print("Native iButton hardware emulation, alternative pins and all firmware EXTI OPEN.")

if __name__=="__main__":
    main()
