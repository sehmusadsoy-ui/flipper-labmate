#!/usr/bin/env python3
"""Execute genuine native external CC1101 RX ISR/START/STOP C and real lease.

Narrow safe baseline: fixed PB2 G0, no debug mirror. Unsupported configurations
must fail before callback, bus or GPIO changes. Device/RF tests remain deferred.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

STUB=r"""
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#define UNUSED(x) ((void)(x))
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
#define FURI_LOG_W(...) ((void)0)
#define FuriHalBusTIM17 17
#define FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX ((1U<<24)|(1U<<9)|(1U<<8))
#define TIM17 17
#define LL_TIM_COUNTERMODE_UP 0
#define LL_TIM_CLOCKDIVISION_DIV1 0
#define LL_TIM_CLOCKSOURCE_INTERNAL 0
#define GpioModeInterruptRiseFall 1
#define GpioModeAnalog 2
#define GpioPullUp 1
#define GpioPullNo 0
#define GpioSpeedVeryHigh 4
#define GpioSpeedLow 0
typedef struct {int port,pin;} GpioPin;
static const GpioPin gpio_ext_pb2={2,2}, foreign_pin={1,7};
typedef void (*SubGhzDeviceCC1101ExtCaptureCallback)(bool,uint32_t,void*);
typedef void (*GpioExtiCallback)(void*);
typedef struct {uint32_t Prescaler,CounterMode,Autoreload,ClockDivision;} LL_TIM_InitTypeDef;
typedef enum {SubGhzDeviceCC1101ExtStateIdle,SubGhzDeviceCC1101ExtStateAsyncRx} State;
typedef struct {
 State state;
 const GpioPin* g0_pin;
 const GpioPin* async_mirror_pin;
 struct {SubGhzDeviceCC1101ExtCaptureCallback capture_callback;
         void* capture_callback_context;
         uint32_t capture_delta_duration;} async_rx;
} SubGhzDeviceCC1101Ext;
static SubGhzDeviceCC1101Ext obj;
static SubGhzDeviceCC1101Ext* subghz_device_cc1101_ext=&obj;
static uint32_t e11_cc1101_rx_handle;
static bool e11_cc1101_rx_fault;
static int claims,releases,writes,callback_add,callback_remove,radio_changes,callback_count;
static bool allow_lease,allow_release=true,legacy_tim,allow_add=true,allow_remove=true;
static GpioExtiCallback existing;
static void* existing_ctx;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask){
 assert(mask==FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX);claims++;return allow_lease?329U:0U;
}
bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask){
 assert(h==329U&&mask==FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX);releases++;return allow_release;
}
bool furi_hal_bus_is_enabled(int bus){assert(bus==17);return legacy_tim;}
void furi_hal_bus_enable(int bus){assert(bus==17&&!legacy_tim);legacy_tim=true;writes++;}
void furi_hal_bus_disable(int bus){assert(bus==17&&legacy_tim);legacy_tim=false;writes++;}
bool furi_hal_gpio_try_add_int_callback(const GpioPin* p,GpioExtiCallback cb,void* ctx){
 assert(p==&gpio_ext_pb2 && cb);callback_add++;
 if(!allow_add||existing)return false;
 existing=cb;existing_ctx=ctx;return true;
}
bool furi_hal_gpio_try_remove_int_callback(const GpioPin* p,GpioExtiCallback cb,void* ctx){
 assert(p==&gpio_ext_pb2 && cb);callback_remove++;
 if(!allow_remove||existing!=cb||existing_ctx!=ctx)return false;
 existing=NULL;existing_ctx=NULL;return true;
}
bool furi_hal_gpio_read(const GpioPin* pin){assert(pin==&gpio_ext_pb2);return false;}
void furi_hal_gpio_init(const GpioPin* pin,int mode,int pull,int speed){
 assert(pin==&gpio_ext_pb2);(void)mode;(void)pull;(void)speed;writes++;
}
void furi_hal_gpio_write(const GpioPin* p,bool b){assert(p);(void)b;writes++;}
void subghz_device_cc1101_ext_rx(void){radio_changes++;writes++;}
void subghz_device_cc1101_ext_idle(void){radio_changes++;writes++;}
bool subghz_device_cc1101_ext_start_debug(void){writes++;return true;}
bool subghz_device_cc1101_ext_stop_debug(void){writes++;return true;}
#define LL_TIM_Init(...) (++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_DisableDMAReq_TRIG(...) (++writes)
#define LL_TIM_DisableIT_TRIG(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_EnableCounter(...) (++writes)
#define LL_TIM_GetCounter(...) (23U)
"""
RUN=r"""
static void cb(bool level,uint32_t duration,void* ctx){
 (void)level;assert(duration==46U);assert(ctx==(void*)27);callback_count++;
}
static void foreign(void* p){(void)p;}
static void reset_case(void){
 claims=releases=writes=callback_add=callback_remove=radio_changes=callback_count=0;
 allow_lease=false;allow_release=allow_add=allow_remove=true;
 legacy_tim=false;existing=NULL;existing_ctx=NULL;
 e11_cc1101_rx_handle=0;e11_cc1101_rx_fault=false;
 obj.state=SubGhzDeviceCC1101ExtStateIdle;
 obj.g0_pin=&gpio_ext_pb2;obj.async_mirror_pin=NULL;
 obj.async_rx.capture_callback=NULL;obj.async_rx.capture_callback_context=NULL;
}
int main(void){
 reset_case();
 assert(!subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 subghz_device_cc1101_ext_stop_async_rx();
 subghz_device_cc1101_ext_capture_ISR(NULL);
 assert(claims==1 && !writes && !radio_changes && !existing);
 reset_case();allow_lease=true;legacy_tim=true;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 assert(!writes && releases==1 && !callback_add);
 subghz_device_cc1101_ext_stop_async_rx();assert(!writes);
 reset_case();allow_lease=true;existing=foreign;existing_ctx=(void*)3;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 assert(!writes && !radio_changes && releases==1 && existing==foreign);
 assert(existing_ctx==(void*)3 && callback_remove==0);
 reset_case();allow_lease=true;obj.g0_pin=&foreign_pin;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 assert(!claims&&!writes);
 reset_case();allow_lease=true;obj.async_mirror_pin=&foreign_pin;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 assert(!claims&&!writes);
 reset_case();allow_lease=true;allow_add=false;allow_release=false;
 assert(!subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 assert(e11_cc1101_rx_fault && e11_cc1101_rx_handle && !writes);
 assert(!subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 reset_case();allow_lease=true;
 assert(subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 assert(e11_cc1101_rx_handle==329U && existing==subghz_device_cc1101_ext_capture_ISR);
 assert(legacy_tim && writes>0 && radio_changes==1);
 assert(!subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 existing(existing_ctx);assert(callback_count==1);
 subghz_device_cc1101_ext_stop_async_rx();
 assert(!e11_cc1101_rx_handle && !legacy_tim && !existing && releases==1);
 int w=writes;
 subghz_device_cc1101_ext_stop_async_rx();assert(writes==w&&releases==1);
 reset_case();allow_lease=true;
 assert(subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 existing=foreign;w=writes;
 subghz_device_cc1101_ext_stop_async_rx();
 assert(e11_cc1101_rx_fault && e11_cc1101_rx_handle && releases==0);
 assert(writes==w && existing==foreign && !callback_count);
 reset_case();allow_lease=true;
 assert(subghz_device_cc1101_ext_try_start_async_rx(cb,(void*)27));
 legacy_tim=false;w=writes;
 subghz_device_cc1101_ext_capture_ISR(NULL);
 subghz_device_cc1101_ext_stop_async_rx();
 assert(e11_cc1101_rx_fault && writes==w && releases==0);
 puts("E11 genuine CC1101 external RX C TIM17/EXTI2 deny/STOP/ISR PASS");
 return 0;
}
"""
MASK=r"""
#define CHECK(x) do{if(!(x)){fprintf(stderr,"EXT CC1101 allocator error %d\n",__LINE__);exit(1);}}while(0)
int main(void){
 uint32_t a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX);
 CHECK(a);
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PB2));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_JS_EXTI2));
 CHECK(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX));
 CHECK(!furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX));
 puts("E11 external CC1101 firmware allocator TIM17/PB2/EXTI2 conflicts PASS");
 return 0;
}
"""
def main():
 p=argparse.ArgumentParser();p.add_argument("root",type=Path);root=p.parse_args().root
 s=(root/"applications/drivers/subghz/cc1101_ext/cc1101_ext.c").read_text()
 h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
 r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
 pub=(root/"applications/drivers/subghz/cc1101_ext/cc1101_ext.h").read_text()
 assert "/* E11 external CC1101 TIM17/PB2/EXTI2 exact RX owner. */" in s
 assert "FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX" in h and "mask == FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX" in r
 assert "bool subghz_device_cc1101_ext_try_start_async_rx(" in pub
 start=s[s.index("bool subghz_device_cc1101_ext_try_start_async_rx("):
         s.index("void subghz_device_cc1101_ext_async_tx_middleware_idle(")]
 assert start.index("furi_hal_resource_lease_try_acquire(")<start.index("furi_hal_bus_enable(FuriHalBusTIM17)")
 assert start.index("furi_hal_gpio_try_add_int_callback(")<start.index("furi_hal_bus_enable(FuriHalBusTIM17)")
 assert "furi_hal_gpio_remove_int_callback(" not in start
 assert "if(!e11_cc1101_rx_handle || e11_cc1101_rx_fault)" in s
 isr=s[s.index("static void subghz_device_cc1101_ext_capture_ISR("):
       s.index("bool subghz_device_cc1101_ext_try_start_async_rx(")]
 with tempfile.TemporaryDirectory(prefix="e11_cc1101_ext_") as t:
  d=Path(t);exe=d/"test"
  # Real ISR, bool start, legacy void and STOP from upstream patched C.
  (d/"driver.c").write_text(STUB+"\n"+isr+"\n"+start+"\n"+RUN)
  subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-Wno-pointer-to-int-cast",
                  str(d/"driver.c"),"-o",str(exe)],check=True)
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
  lease=r[r.index("/* Firmware-owned E11 lease primitive"):r.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
  (d/"allocator.c").write_text(pre+masks+lease+MASK)
  subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic","-pthread",
                  str(d/"allocator.c"),"-o",str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
 print("E11 original external CC1101 RX TIM17/PB2/EXTI2 native C+allocator HOST PASS")
 print("Other dynamic G0 and debug mirrors plus physical RF remain OPEN")

if __name__=="__main__": main()
