#!/usr/bin/env python3
"""Original native ICM42688P FIFO PB2/EXTI2 C + shared firmware lease fault gate.

Tests source driver body itself, not a handwritten replacement.
IMU worker asynchronous semaphore/NO FALSE PRESENT logic is audited
in the real pinned source; RF/IMU device functional testing is deferred.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import subprocess
import tempfile

STUB=r"""
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#define UNUSED(x) ((void)(x))
#define TAG "IMU"
#define FURI_LOG_W(...) ((void)0)
#define FURI_HAL_LEASE_IRQ_PB2 ((1U<<9)|(1U<<8))
enum { GpioModeInterruptRise=1,GpioModeAnalog=2,
 GpioPullDown=2,GpioPullNo=0,GpioSpeedVeryHigh=4,GpioSpeedLow=0 };
enum { ICM42688_FIFO_CONFIG=1,ICM42688_INTF_CONFIG0,
 ICM42688_FIFO_CONFIG1,ICM42688_FIFO_CONFIG2,
 ICM42688_FIFO_CONFIG3,ICM42688_INT_CONFIG,
 ICM42688_INT_CONFIG0,ICM42688_INT_CONFIG1,
 ICM42688_INT_STATUS,ICM42688_INT_SOURCE0 };
typedef struct {int id;} FuriHalSpiBusHandle;
typedef struct {int port,pin;} GpioPin;
static const GpioPin gpio_ext_pb2={2,2},alien={1,7};
typedef void (*GpioExtiCallback)(void*);
typedef void (*ICM42688PIrqCallback)(void*);
typedef struct ICM42688P ICM42688P;
static int claim_count,release_count,spi_writes,gpio_modes,add_calls,remove_calls,client_irq;
static bool claim_ok,release_ok=true,add_ok=true,remove_ok=true;
static GpioExtiCallback slot;
static void* slot_context;
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask){
 assert(mask==FURI_HAL_LEASE_IRQ_PB2);claim_count++;return claim_ok?333U:0U;
}
static bool furi_hal_resource_lease_release(uint32_t owner,uint32_t mask){
 assert(owner==333U && mask==FURI_HAL_LEASE_IRQ_PB2);
 release_count++;return release_ok;
}
static bool furi_hal_gpio_try_add_int_callback(
 const GpioPin* pin,GpioExtiCallback cb,void* context){
 assert(pin==&gpio_ext_pb2 && cb);add_calls++;
 if(!add_ok||slot)return false;
 slot=cb;slot_context=context;return true;
}
static bool furi_hal_gpio_try_remove_int_callback(
 const GpioPin* pin,GpioExtiCallback cb,void* context){
 assert(pin==&gpio_ext_pb2 && cb);remove_calls++;
 if(!remove_ok||slot!=cb||slot_context!=context)return false;
 slot=NULL;slot_context=NULL;return true;
}
static void furi_hal_gpio_init(const GpioPin* pin,int mode,int pull,int speed){
 assert(pin==&gpio_ext_pb2);
 assert((mode==1&&pull==2&&speed==4)||(mode==2&&pull==0&&speed==0));
 gpio_modes++;
}
static bool icm42688p_write_reg(FuriHalSpiBusHandle* spi,uint8_t reg,uint8_t val){
 assert(spi && reg && val<255U);spi_writes++;return true;
}
static bool icm42688p_read_reg(FuriHalSpiBusHandle* spi,uint8_t reg,uint8_t* val){
 assert(spi&&reg==ICM42688_INT_STATUS&&val);*val=0;spi_writes++;return true;
}
"""
RUN=r"""
static FuriHalSpiBusHandle spi={1};
static void cb(void* ctx){assert(ctx==(void*)&spi);client_irq++;}
static void foreign(void* ctx){(void)ctx;}
static void reset(void){
 claim_count=release_count=spi_writes=gpio_modes=add_calls=remove_calls=client_irq=0;
 claim_ok=false;release_ok=add_ok=remove_ok=true;
 slot=NULL;slot_context=NULL;
}
int main(void){
 reset();
 ICM42688P* d=icm42688p_alloc(&spi,&gpio_ext_pb2);
 assert(d);
 assert(!icm42688_fifo_try_enable(d,cb,&spi));
 icm42688_fifo_disable(d);
 assert(claim_count==1 && !add_calls && !spi_writes && !gpio_modes && !slot);
 reset();claim_ok=true;slot=foreign;slot_context=(void*)7;
 assert(!icm42688_fifo_try_enable(d,cb,&spi));
 assert(slot==foreign && slot_context==(void*)7 && release_count==1 &&
        !spi_writes && !gpio_modes && !remove_calls);
 icm42688_fifo_disable(d);assert(!spi_writes && !gpio_modes);
 reset();claim_ok=true;add_ok=false;release_ok=false;
 assert(!icm42688_fifo_try_enable(d,cb,&spi));
 assert(d->e11_irq_fault && d->e11_irq_owner && !spi_writes);
 icm42688_fifo_disable(d);assert(!spi_writes && !gpio_modes);
 /* Sticky owner deliberately keeps ISR object alive; use a fresh
  * fixture and never free the failed-release instance. */
 reset();
 ICM42688P* live=icm42688p_alloc(&spi,&gpio_ext_pb2);
 claim_ok=true;
 assert(icm42688_fifo_try_enable(live,cb,&spi));
 assert(slot_context==live && slot && spi_writes>0 && gpio_modes==1);
 int n=claim_count;
 assert(!icm42688_fifo_try_enable(live,cb,&spi) && claim_count==n);
 slot(slot_context);assert(client_irq==1);
 icm42688_fifo_disable(live);
 assert(!slot && !live->e11_irq_owner && release_count==1 &&
        gpio_modes==2);
 int old=spi_writes;
 icm42688_fifo_disable(live);
 assert(spi_writes==old && remove_calls==1);
 assert(icm42688_fifo_try_enable(live,cb,&spi));
 icm42688_fifo_disable(live);
 icm42688p_free(live);
 reset();claim_ok=true;
 ICM42688P* wrong=icm42688p_alloc(&spi,&alien);
 assert(!icm42688_fifo_try_enable(wrong,cb,&spi) && !claim_count);
 icm42688p_free(wrong);
 reset();claim_ok=true;
 ICM42688P* changed=icm42688p_alloc(&spi,&gpio_ext_pb2);
 assert(icm42688_fifo_try_enable(changed,cb,&spi));
 slot=foreign;old=spi_writes;
 icm42688_fifo_disable(changed);
 assert(changed->e11_irq_fault && changed->e11_irq_owner &&
        spi_writes==old && slot==foreign && release_count==0);
 assert(!icm42688_fifo_try_enable(changed,cb,&spi) &&
        claim_count==1 && spi_writes==old);
 reset();claim_ok=true;release_ok=false;
 ICM42688P* bad=icm42688p_alloc(&spi,&gpio_ext_pb2);
 assert(icm42688_fifo_try_enable(bad,cb,&spi));
 icm42688_fifo_disable(bad);
 assert(bad->e11_irq_fault && bad->e11_irq_owner && release_count==1);
 old=spi_writes;
 icm42688_fifo_disable(bad);assert(spi_writes==old);
 puts("E11 actual native IMU FIFO PB2/EXTI2 original C denied/STOP/ISR PASS");
 return 0;
}
"""
MASK=r"""
#define CHECK(x) do{if(!(x)){fprintf(stderr,"IMU mask error %d\n",__LINE__);exit(1);}}while(0)
int main(void){
 uint32_t owner=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PB2);
 CHECK(owner);
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX));
 CHECK(!furi_hal_resource_lease_v2_try_acquire(FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_JS_EXTI2));
 CHECK(!furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_JS_EXTI2));
 CHECK(furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_IRQ_PB2));
 CHECK(!furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_IRQ_PB2));
 puts("E11 real native allocator IMU PB2/EXTI2 vs NFC and CC1101 PASS");
 return 0;
}
"""

def main():
    ap=argparse.ArgumentParser();ap.add_argument("root",type=Path)
    root=ap.parse_args().root.resolve()
    src=(root/"applications/system/js_app/modules/js_vgm/ICM42688P/ICM42688P.c").read_text()
    header=(root/"applications/system/js_app/modules/js_vgm/ICM42688P/ICM42688P.h").read_text()
    imu=(root/"applications/system/js_app/modules/js_vgm/imu.c").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    assert "/* E11 native IMU FIFO PB2+EXTI2 exact callback owner. */" in src
    assert "bool icm42688_fifo_try_enable(" in header
    assert "if(!furi_hal_gpio_try_remove_int_callback(" in src
    assert "furi_hal_gpio_remove_int_callback(" not in src
    assert "furi_hal_gpio_add_int_callback(" not in src
    assert "imu->e11_started=icm42688_fifo_try_enable(" in imu
    assert "if(!imu->e11_started)" in imu
    assert "if(!imu->thread) imu->present=false;" in imu
    assert "furi_semaphore_acquire(imu->e11_ready,2000)" in imu
    assert "FURI_HAL_LEASE_IRQ_PB2" in h
    st=src[src.index("struct ICM42688P {"):src.index("static const struct AccelFullScale")]
    driver=src[src.index("static void e11_imu_fifo_irq("):
               src.index("uint16_t icm42688_fifo_get_count(")]
    mem=src[src.index("ICM42688P* icm42688p_alloc("):
            src.index("bool icm42688p_init(")]
    assert driver.index("furi_hal_resource_lease_try_acquire(") < driver.index("icm42688p_write_reg(")
    assert driver.index("furi_hal_gpio_try_add_int_callback(")<driver.index("icm42688p_write_reg(")
    assert driver.index("furi_hal_gpio_try_remove_int_callback(")<driver.index("GpioModeAnalog")
    with tempfile.TemporaryDirectory(prefix="e11_imu_fifo_") as temp:
        d=Path(temp);exe=d/"test"
        (d/"fifo.c").write_text(STUB+"\n"+st+"\n"+driver+"\n"+mem+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        str(d/"fifo.c"),"-o",str(exe)],check=True)
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
        alloc=r[r.index("/* Firmware-owned E11 lease primitive"):r.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
        (d/"allocator.c").write_text(pre+masks+alloc+MASK)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(d/"allocator.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 original IMU FIFO C and actual lease C HOST PASS")
    print("IMU worker exact source BUSY route audited; physical IMU and JS UI OPEN")

if __name__=="__main__":
    main()
