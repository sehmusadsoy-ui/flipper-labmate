#!/usr/bin/env python3
"""Compile original pinned external CC1101 RX ISR, START, STOP and real lease C.

Explicitly asserts no GPIO/TIM17/foreign EXTI mutation after denied
lease/callback, wrong owner, clock loss or failed release.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#define UNUSED(x) ((void)(x))
#define FURI_LOG_W(...) ((void)0)
#define TAG "ExtRadio"
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
enum { FuriHalBusTIM17=17,SubGhzDeviceCC1101ExtStateIdle=1,
 SubGhzDeviceCC1101ExtStateAsyncRx=2,
 GpioModeInterruptRiseFall=1,GpioModeAnalog=2,GpioPullUp=1,
 GpioPullNo=0,GpioSpeedVeryHigh=4,GpioSpeedLow=0,
 LL_TIM_COUNTERMODE_UP=0,LL_TIM_CLOCKDIVISION_DIV1=0,
 LL_TIM_CLOCKSOURCE_INTERNAL=0 };
#define FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX ((1U<<24)|(1U<<9)|(1U<<8))
typedef struct {int port;int pin;} GpioPin;
typedef void(*GpioExtiCallback)(void*);
typedef void(*SubGhzDeviceCC1101ExtCaptureCallback)(bool,uint32_t,void*);
static const GpioPin gpio_ext_pb2={2,2},gpio_ext_pa7={1,7},gpio_ext_pb3={2,3};
typedef struct {
 uint32_t Prescaler,CounterMode,Autoreload,ClockDivision;
} LL_TIM_InitTypeDef;
typedef struct {
 int state;
 const GpioPin *g0_pin,*async_mirror_pin;
 struct {
  SubGhzDeviceCC1101ExtCaptureCallback capture_callback;
  void* capture_callback_context;
  uint32_t capture_delta_duration;
 } async_rx;
} SubGhzDeviceCC1101Ext;
static SubGhzDeviceCC1101Ext instance;
static SubGhzDeviceCC1101Ext* subghz_device_cc1101_ext=&instance;
static bool lease_allowed,release_allowed=true,bus_on,slot_allowed=true,remove_allowed=true;
static int writes,claims,releases,add_calls,remove_calls,rx_switches,radio_stops,callbacks;
static GpioExtiCallback active_cb;
static void* active_ctx;
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX);
 claims++;return lease_allowed?247U:0U;
}
static bool furi_hal_resource_lease_release(uint32_t owner,uint32_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX && owner==247U);
 releases++;return release_allowed;
}
static bool furi_hal_bus_is_enabled(int bus) {
 assert(bus==FuriHalBusTIM17);return bus_on;
}
static void furi_hal_bus_enable(int bus) {
 assert(bus==FuriHalBusTIM17 && !bus_on);bus_on=true;writes++;
}
static void furi_hal_bus_disable(int bus) {
 assert(bus==FuriHalBusTIM17 && bus_on);bus_on=false;writes++;
}
static bool furi_hal_gpio_try_add_int_callback(
 const GpioPin* gpio,GpioExtiCallback cb,void* ctx) {
 assert(gpio==&gpio_ext_pb2 && cb && ctx==subghz_device_cc1101_ext);
 add_calls++;
 if(!slot_allowed || active_cb)return false;
 active_cb=cb;active_ctx=ctx;writes++;
 return true;
}
static bool furi_hal_gpio_try_remove_int_callback(
 const GpioPin* gpio,GpioExtiCallback cb,void* ctx) {
 assert(gpio==&gpio_ext_pb2 && cb && ctx==subghz_device_cc1101_ext);
 remove_calls++;
 if(!remove_allowed || active_cb!=cb || active_ctx!=ctx)return false;
 active_cb=NULL;active_ctx=NULL;writes++;
 return true;
}
static void furi_hal_gpio_init(const GpioPin* pin,int mode,int pull,int speed) {
 assert(pin==&gpio_ext_pb2 && (mode==1||mode==2));
 (void)pull;(void)speed;writes++;
}
static bool furi_hal_gpio_read(const GpioPin* pin) {
 assert(pin==&gpio_ext_pb2);return false;
}
static void furi_hal_gpio_write(const GpioPin* pin,bool state) {
 assert(pin==&gpio_ext_pb2);(void)state;writes++;
}
static void subghz_device_cc1101_ext_rx(void) {rx_switches++;writes++;}
static void subghz_device_cc1101_ext_idle(void) {radio_stops++;writes++;}
static bool subghz_device_cc1101_ext_start_debug(void) {return false;}
static bool subghz_device_cc1101_ext_stop_debug(void) {return false;}
#define TIM17 17
#define LL_TIM_Init(t,s) ((void)(t),(void)(s),++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_DisableDMAReq_TRIG(...) (++writes)
#define LL_TIM_DisableIT_TRIG(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_GetCounter(...) 11U
#define LL_TIM_EnableCounter(...) (++writes)
"""
RUN=r"""
static void foreign(void* ptr) {(void)ptr;}
static void capture(bool level,uint32_t duration,void* ctx) {
 assert(level && duration==22U && ctx==&instance);callbacks++;
}
static void reset(void) {
 writes=claims=releases=add_calls=remove_calls=0;
 rx_switches=radio_stops=callbacks=0;
 lease_allowed=false;release_allowed=slot_allowed=remove_allowed=true;
 bus_on=false;active_cb=NULL;active_ctx=NULL;
 instance.state=SubGhzDeviceCC1101ExtStateIdle;
 instance.g0_pin=&gpio_ext_pb2;
 instance.async_mirror_pin=NULL;
 instance.async_rx.capture_callback=NULL;
 instance.async_rx.capture_callback_context=NULL;
 e11_ext_rx_owner=0U;e11_ext_rx_fault=false;
}
int main(void) {
 reset();
 subghz_device_cc1101_ext=NULL;
 subghz_device_cc1101_ext_set_async_mirror_pin(&gpio_ext_pa7);
 subghz_device_cc1101_ext=&instance;
 assert(instance.async_mirror_pin==NULL && !writes && !claims);
 reset();
 assert(!subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 subghz_device_cc1101_ext_stop_async_rx();
 subghz_device_cc1101_ext_capture_ISR(NULL);
 assert(!writes && !add_calls && !remove_calls && !callbacks);
 assert(claims==1);
 reset();lease_allowed=true;bus_on=true;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 assert(!writes && releases==1 && !add_calls);
 reset();lease_allowed=true;slot_allowed=false;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 assert(!writes && add_calls==1 && releases==1 && !bus_on);
 reset();lease_allowed=true;
 active_cb=foreign;active_ctx=(void*)3;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 assert(active_cb==foreign && active_ctx==(void*)3 && !writes);
 assert(!remove_calls && !radio_stops);
 reset();lease_allowed=true;
 instance.g0_pin=&gpio_ext_pb3;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 assert(!claims && !writes);
 reset();lease_allowed=true;
 /* Exercise the actual patched public setter, not direct struct mutation. */
 subghz_device_cc1101_ext_set_async_mirror_pin(&gpio_ext_pa7);
 assert(instance.async_mirror_pin==&gpio_ext_pa7);
 assert(!subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 assert(!claims && !writes);
 subghz_device_cc1101_ext_set_async_mirror_pin(NULL);
 assert(instance.async_mirror_pin==NULL);
 reset();lease_allowed=true;
 assert(subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 assert(e11_ext_rx_owner==247U && bus_on && rx_switches==1);
 assert(instance.state==SubGhzDeviceCC1101ExtStateAsyncRx);
 assert(active_cb==subghz_device_cc1101_ext_capture_ISR);
 /* An in-flight RX lease must freeze the mirror pin until owned STOP. */
 subghz_device_cc1101_ext_set_async_mirror_pin(&gpio_ext_pa7);
 assert(instance.async_mirror_pin==NULL);
 int c=claims;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(capture,&instance) &&
        claims==c);
 subghz_device_cc1101_ext_capture_ISR(NULL);assert(callbacks==1);
 subghz_device_cc1101_ext_stop_async_rx();
 assert(!bus_on && !e11_ext_rx_owner && !active_cb && releases==1);
 int before=writes;
 subghz_device_cc1101_ext_stop_async_rx();
 subghz_device_cc1101_ext_capture_ISR(NULL);
 assert(writes==before && releases==1);
 assert(subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 subghz_device_cc1101_ext_stop_async_rx();
 reset();lease_allowed=true;
 assert(subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 active_cb=foreign;before=writes;
 subghz_device_cc1101_ext_stop_async_rx();
 assert(e11_ext_rx_owner==247U && e11_ext_rx_fault &&
        bus_on && writes==before && !radio_stops && !releases);
 assert(active_cb==foreign);
 reset();lease_allowed=true;release_allowed=false;bus_on=true;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 assert(e11_ext_rx_fault && e11_ext_rx_owner && !writes);
 reset();lease_allowed=true;release_allowed=false;
 assert(subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 subghz_device_cc1101_ext_stop_async_rx();
 assert(e11_ext_rx_fault && e11_ext_rx_owner==247U && !bus_on);
 before=writes;
 subghz_device_cc1101_ext_stop_async_rx();assert(writes==before);
 reset();lease_allowed=true;
 assert(subghz_device_cc1101_ext_try_start_async_rx(capture,&instance));
 bus_on=false;before=writes;
 subghz_device_cc1101_ext_capture_ISR(NULL);
 subghz_device_cc1101_ext_stop_async_rx();
 assert(e11_ext_rx_fault && e11_ext_rx_owner && writes==before);
 subghz_device_cc1101_ext_set_async_mirror_pin(&gpio_ext_pa7);
 assert(instance.async_mirror_pin==NULL); /* Sticky fault forbids retarget. */
 puts("E11 ext CC1101 original RX TIM17 PB2 EXTI2 C deny/ISR/STOP PASS");
 return 0;
}
"""
MASK=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"ext CC1101 allocator fail line %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t lease=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX);
 REQUIRE(lease);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PB2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_JS_EXTI2));
 REQUIRE(!furi_hal_resource_lease_release(lease,FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
 REQUIRE(furi_hal_resource_lease_release(lease,FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX));
 REQUIRE(!furi_hal_resource_lease_release(lease,FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX));
 puts("E11 real firmware ext CC1101 TIM17/PB2/EXTI2 collisions PASS");
 return 0;
}
"""
def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"applications/drivers/subghz/cc1101_ext/cc1101_ext.c").read_text()
    header=(root/"applications/drivers/subghz/cc1101_ext/cc1101_ext.h").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    assert "/* E11 external CC1101 RX TIM17+PB2+EXTI2 owner. */" in s
    assert "bool subghz_device_cc1101_ext_try_start_async_rx(" in header
    assert "mask == FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX" in r
    start=s[s.index("bool subghz_device_cc1101_ext_try_start_async_rx("):
            s.index("void subghz_device_cc1101_ext_async_tx_middleware_idle(")]
    assert start.index("furi_hal_resource_lease_try_acquire(") < start.index(
        "furi_hal_bus_enable(FuriHalBusTIM17);")
    assert start.index("furi_hal_gpio_try_add_int_callback(") < start.index(
        "furi_hal_bus_enable(FuriHalBusTIM17);")
    assert "furi_hal_gpio_remove_int_callback(" not in start
    assert "if(!e11_ext_rx_ready()) return;" in start
    helper=s[s.index("/* E11 external CC1101 RX TIM17+PB2+EXTI2 owner. */"):
             s.index("#define SUBGHZ_DEVICE_CC1101_EXT_TX_GPIO")]
    # Separate subsequent TX stage adds globals beside the original RX owner.
    # Compile the unchanged genuine RX helper without unrelated TX-only data.
    if "/* E11 native external CC1101 TX TIM17/DMA2 V2 owner. */" in s:
        for definition in (
            "static uint32_t e11_ext_tx_owner;\n",
            "static bool e11_ext_tx_fault;\n",
        ):
            assert definition in helper
            helper=helper.replace(definition,"")
    setter=s[s.index("void subghz_device_cc1101_ext_set_async_mirror_pin("):
             s.index("const GpioPin* subghz_device_cc1101_ext_get_data_gpio(")]
    # On later TX-integrated source the setter also checks TX state;
    # this RX-only native extraction provides those otherwise unrelated tokens.
    if "e11_ext_tx_owner" in setter:
        helper+="\nstatic uint32_t e11_ext_tx_owner;\nstatic bool e11_ext_tx_fault;\n"
        setter=setter.replace("e11_ext_tx_owner || e11_ext_tx_fault", "e11_ext_tx_owner || e11_ext_tx_fault")
    isr=s[s.index("static void subghz_device_cc1101_ext_capture_ISR("):
          s.index("bool subghz_device_cc1101_ext_try_start_async_rx(")]
    with tempfile.TemporaryDirectory(prefix="e11_ext_cc1101_") as temp:
        d=Path(temp);exe=d/"test"
        (d/"native.c").write_text(STUB+"\n"+helper+"\n"+setter+"\n"+isr+"\n"+start+"\n"+RUN)
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
        (d/"lease.c").write_text(pre+masks+allocator+MASK)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(d/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 EXT CC1101 PB2+EXTI2+TIM17 original driver and allocator C PASS")
    print("TX DMA2 CH3/4/5, plugin void-client BUSY and physical RF still OPEN.")

if __name__=="__main__":
    main()
