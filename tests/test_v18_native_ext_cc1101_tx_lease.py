#!/usr/bin/env python3
"""Execute original external CC1101 TX DMA2 CH3/4/5 C and V2 allocator.

Production ISR/START/STOP original functions, real firmware V1+V2
allocator collision gate via test_v18_extended_dma_lease.py in workflow.
Physical transmitted RF is never simulated as PASS.
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
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#define UNUSED(x) ((void)(x))
#define FURI_LOG_W(...) ((void)0)
#define TAG "ExternalTx"
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
#define GPIO_NUMBER 16
#define SUBGHZ_DEVICE_CC1101_EXT_ASYNC_TX_BUFFER_FULL 256U
#define SUBGHZ_DEVICE_CC1101_EXT_ASYNC_TX_BUFFER_HALF 128U
#define SUBGHZ_DEVICE_CC1101_EXT_DMA 2
#define LL_DMA_CHANNEL_3 3
#define SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_CHANNEL 3
#define SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_DEF 2,3
#define SUBGHZ_DEVICE_CC1101_EXT_DMA_CH4_DEF 2,4
#define SUBGHZ_DEVICE_CC1101_EXT_DMA_CH5_DEF 2,5
#define SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_IRQ 3
#define FuriHalBusTIM17 17
#define FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX UINT64_C(0x1FFF00000000)
#define LL_DMA_DIRECTION_MEMORY_TO_PERIPH 0
#define LL_DMA_MODE_CIRCULAR 0
#define LL_DMA_PERIPH_NOINCREMENT 0
#define LL_DMA_MEMORY_INCREMENT 0
#define LL_DMA_PDATAALIGN_WORD 0
#define LL_DMA_MDATAALIGN_WORD 0
#define LL_DMA_PRIORITY_VERYHIGH 0
#define LL_DMA_PRIORITY_HIGH 0
#define LL_DMA_PRIORITY_LOW 0
#define LL_DMAMUX_REQ_TIM17_UP 0
#define LL_TIM_COUNTERMODE_UP 0
#define LL_TIM_CLOCKDIVISION_DIV1 0
#define LL_TIM_CLOCKSOURCE_INTERNAL 0
#define GpioModeOutputPushPull 1
#define GpioModeAnalog 2
#define GpioPullNo 0
#define GpioSpeedLow 0
#define GpioSpeedVeryHigh 4
typedef struct {uint32_t BSRR;} SimGpioPort;
typedef struct {SimGpioPort* port;uint32_t pin;} GpioPin;
static SimGpioPort port;
static const GpioPin gpio_ext_pb2={&port,4U}, gpio_ext_pa7={&port,128U},
                     gpio_ext_pb3={&port,8U};
typedef struct {uint32_t ARR;} SimTimer;
static SimTimer timer;
#define TIM17 (&timer)
typedef int LevelDuration;
typedef LevelDuration (*SubGhzDeviceCC1101ExtCallback)(void*);
typedef struct {int state;} SubGhzDeviceCC1101ExtAsyncTxMiddleware;
typedef struct {
 uint32_t* buffer;
 SubGhzDeviceCC1101ExtCallback callback;
 void* callback_context;
 uint32_t gpio_tx_buff[2];
 uint32_t debug_gpio_buff[2];
 SubGhzDeviceCC1101ExtAsyncTxMiddleware middleware;
} SubGhzDeviceCC1101ExtAsyncTx;
enum {
 SubGhzDeviceCC1101ExtStateIdle=1,SubGhzDeviceCC1101ExtStateAsyncTx=2,
 SubGhzDeviceCC1101ExtRegulationOnlyRx=0,SubGhzDeviceCC1101ExtRegulationTxRx=1
};
typedef struct {
 int state,regulation;
 const GpioPin *g0_pin,*async_mirror_pin;
 SubGhzDeviceCC1101ExtAsyncTx async_tx;
} SubGhzDeviceCC1101Ext;
static SubGhzDeviceCC1101Ext instance;
static SubGhzDeviceCC1101Ext* subghz_device_cc1101_ext=&instance;
static uint32_t e11_ext_tx_owner;
static bool e11_ext_tx_fault;
static int claims,releases,writes,pin_writes,radio_idle,radio_tx,irq_attaches,irq_detaches,refills;
static bool allow_claim,allow_release=true,tim17,ch3,ch4,ch5,fail_alloc,half_flag,full_flag;
static void* tx_alloc(size_t count) {return fail_alloc?NULL:calloc(1,count);}
#define malloc tx_alloc
static uint32_t furi_hal_resource_lease_v2_try_acquire(uint64_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX);
 claims++;return allow_claim?812U:0U;
}
static bool furi_hal_resource_lease_v2_release(uint32_t owner,uint64_t mask) {
 assert(owner==812U && mask==FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX);
 releases++;return allow_release;
}
static bool furi_hal_bus_is_enabled(int bus) {assert(bus==17);return tim17;}
static void furi_hal_bus_enable(int bus) {assert(bus==17&&!tim17);tim17=true;writes++;}
static void furi_hal_bus_disable(int bus) {assert(bus==17&&tim17);tim17=false;writes++;}
static bool dma_is_enabled(int ctrl,int channel) {
 assert(ctrl==2 && channel>=3 && channel<=5);
 return channel==3?ch3:channel==4?ch4:ch5;
}
static void dma_enable(int ctrl,int channel) {
 assert(ctrl==2);
 if(channel==3)ch3=true;else if(channel==4)ch4=true;else ch5=true;
 writes++;
}
static void dma_deinit(int ctrl,int channel) {
 assert(ctrl==2);
 if(channel==3)ch3=false;else if(channel==4)ch4=false;else ch5=false;
 writes++;
}
#define LL_DMA_IsEnabledChannel dma_is_enabled
#define LL_DMA_EnableChannel dma_enable
#define LL_DMA_DeInit dma_deinit
#define LL_DMA_SetMemoryAddress(...) (++writes)
#define LL_DMA_SetPeriphAddress(...) (++writes)
#define LL_DMA_ConfigTransfer(...) (++writes)
#define LL_DMA_SetDataLength(...) (++writes)
#define LL_DMA_SetPeriphRequest(...) (++writes)
#define LL_DMA_EnableIT_TC(...) (++writes)
#define LL_DMA_EnableIT_HT(...) (++writes)
#define LL_DMA_IsActiveFlag_HT3(...) (half_flag)
#define LL_DMA_IsActiveFlag_TC3(...) (full_flag)
#define LL_DMA_ClearFlag_HT3(...) (half_flag=false,++writes)
#define LL_DMA_ClearFlag_TC3(...) (full_flag=false,++writes)
#define LL_DMA_DisableChannel dma_deinit
#define LL_TIM_SetCounterMode(...) (++writes)
#define LL_TIM_SetClockDivision(...) (++writes)
#define LL_TIM_SetAutoReload(t,reload) ((t)->ARR=(reload),++writes)
#define LL_TIM_SetPrescaler(...) (++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_EnableDMAReq_UPDATE(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_EnableCounter(...) (++writes)
#define LL_TIM_GetAutoReload(t) ((t)->ARR)
static void furi_hal_gpio_write(const GpioPin* pin,bool state) {
 assert(pin==&gpio_ext_pb2);(void)state;pin_writes++;writes++;
}
static void furi_hal_gpio_init(const GpioPin* pin,int mode,int pull,int speed) {
 assert(pin==&gpio_ext_pb2 && (mode==1||mode==2));
 (void)pull;(void)speed;pin_writes++;writes++;
}
static void subghz_device_cc1101_ext_async_tx_middleware_idle(
 SubGhzDeviceCC1101ExtAsyncTxMiddleware* middleware){assert(middleware);}
static void subghz_device_cc1101_ext_async_tx_refill(uint32_t* buffer,size_t count) {
 assert(buffer && count>0);refills++;
}
static bool subghz_device_cc1101_ext_start_debug(void) {return false;}
static bool subghz_device_cc1101_ext_stop_debug(void) {return false;}
static void subghz_device_cc1101_ext_tx(void) {radio_tx++;writes++;}
static void subghz_device_cc1101_ext_idle(void) {radio_idle++;writes++;}
typedef void(*FuriHalInterruptCallback)(void*);
static void furi_hal_interrupt_set_isr(int id,FuriHalInterruptCallback cb,void*ctx) {
 assert(id==SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_IRQ && ctx==NULL);
 if(cb)irq_attaches++;else irq_detaches++;
 writes++;
}
"""
RUN=r"""
static LevelDuration tx_cb(void* ptr){(void)ptr;return 1;}
static void reset_case(void){
 claims=releases=writes=pin_writes=radio_idle=radio_tx=irq_attaches=irq_detaches=refills=0;
 allow_claim=false;allow_release=true;
 tim17=ch3=ch4=ch5=fail_alloc=half_flag=full_flag=false;
 e11_ext_tx_owner=0U;e11_ext_tx_fault=false;
 instance.state=SubGhzDeviceCC1101ExtStateIdle;
 instance.regulation=SubGhzDeviceCC1101ExtRegulationTxRx;
 instance.g0_pin=&gpio_ext_pb2;
 instance.async_mirror_pin=NULL;
 instance.async_tx.buffer=NULL;
 instance.async_tx.callback=NULL;
 instance.async_tx.callback_context=NULL;
 timer.ARR=0;
}
static bool start(void){return subghz_device_cc1101_ext_start_async_tx(tx_cb,&instance);}
int main(void){
 reset_case();
 assert(!start());
 subghz_device_cc1101_ext_stop_async_tx();
 subghz_device_cc1101_ext_async_tx_dma_isr(NULL);
 assert(claims==1 && !writes && !pin_writes && !irq_attaches);
 reset_case();allow_claim=true;
 instance.regulation=SubGhzDeviceCC1101ExtRegulationOnlyRx;
 assert(!start() && !claims && !writes);
 reset_case();allow_claim=true;instance.g0_pin=&gpio_ext_pb3;
 assert(!start() && !claims && !writes);
 reset_case();allow_claim=true;instance.async_mirror_pin=&gpio_ext_pa7;
 assert(!start() && !claims && !writes);
 for(int n=0;n<4;n++){
  reset_case();allow_claim=true;
  if(n==0)tim17=true;
  if(n==1)ch3=true;
  if(n==2)ch4=true;
  if(n==3)ch5=true;
  assert(!start() && !writes && releases==1 && !e11_ext_tx_owner);
  subghz_device_cc1101_ext_stop_async_tx();
  assert(!writes);
 }
 reset_case();allow_claim=true;fail_alloc=true;
 assert(!start() && !pin_writes && !radio_tx && releases==1);
 assert(instance.state==SubGhzDeviceCC1101ExtStateIdle);
 reset_case();allow_claim=true;allow_release=false;tim17=true;
 assert(!start() && e11_ext_tx_owner==812U && e11_ext_tx_fault && !writes);
 reset_case();allow_claim=true;
 assert(start() && tim17 && ch3 && ch4 && !ch5);
 assert(e11_ext_tx_owner==812U && irq_attaches==1 && radio_tx==1 && pin_writes);
 int prev_claims=claims;
 assert(!start() && claims==prev_claims);
 assert(!subghz_device_cc1101_ext_is_async_tx_complete());
 half_flag=full_flag=true;
 subghz_device_cc1101_ext_async_tx_dma_isr(NULL);
 assert(!half_flag && !full_flag && refills==3);
 subghz_device_cc1101_ext_stop_async_tx();
 assert(!tim17 && !ch3 && !ch4 && !ch5 && !e11_ext_tx_owner &&
        releases==1 && irq_detaches==1 && radio_idle==1 &&
        instance.state==SubGhzDeviceCC1101ExtStateIdle);
 int before=writes;
 subghz_device_cc1101_ext_stop_async_tx();
 subghz_device_cc1101_ext_async_tx_dma_isr(NULL);
 assert(writes==before && releases==1);
 assert(start());subghz_device_cc1101_ext_stop_async_tx();
 reset_case();allow_claim=true;allow_release=false;
 assert(start());subghz_device_cc1101_ext_stop_async_tx();
 assert(e11_ext_tx_fault && e11_ext_tx_owner==812U && !tim17);
 before=writes;
 subghz_device_cc1101_ext_stop_async_tx();
 assert(writes==before && !start());
 reset_case();allow_claim=true;
 assert(start());tim17=false;before=writes;
 subghz_device_cc1101_ext_async_tx_dma_isr(NULL);
 subghz_device_cc1101_ext_stop_async_tx();
 assert(writes==before && e11_ext_tx_fault && e11_ext_tx_owner);
 reset_case();allow_claim=true;
 assert(start());ch4=false;before=writes;
 subghz_device_cc1101_ext_stop_async_tx();
 assert(writes==before && e11_ext_tx_fault && e11_ext_tx_owner);
 reset_case();allow_claim=true;
 assert(start());ch5=true;before=writes;
 subghz_device_cc1101_ext_stop_async_tx();
 assert(writes==before && e11_ext_tx_fault && e11_ext_tx_owner);
 puts("E11 original external CC1101 TX TIM17/DMA2 C owner, BUSY/ISR/STOP PASS");
 return 0;
}
"""
def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"applications/drivers/subghz/cc1101_ext/cc1101_ext.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    assert "/* E11 native external CC1101 TX TIM17/DMA2 V2 owner. */" in s
    assert "FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX" in h
    a=s.index("/* E11 native external CC1101 TX TIM17/DMA2 V2 owner. */")
    src=s[a:]
    assert src.count("furi_hal_resource_lease_v2_try_acquire(")==1
    assert src.index("furi_hal_resource_lease_v2_try_acquire(") < src.index(
        "subghz_device_cc1101_ext->async_tx.callback = callback;")
    assert src.index("furi_hal_resource_lease_v2_try_acquire(") < src.index(
        "furi_hal_gpio_write(subghz_device_cc1101_ext->g0_pin, false);")
    assert "FuriHalInterruptIdTim1TrgComTim17, NULL, NULL" not in src
    assert "if(!e11_ext_tx_ready()) return;" in src
    assert "if(!e11_ext_tx_ready()) return false;" in src
    assert "LL_DMA_DeInit(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH4_DEF);" in src
    with tempfile.TemporaryDirectory(prefix="e11_ext_cc1101_tx_") as tmp:
        d=Path(tmp);exe=d/"test"
        (d/"native.c").write_text(STUB+"\n"+src+"\n"+RUN)
        subprocess.run(["cc","-std=gnu11","-Wall","-Wextra","-Werror",
                        "-Wno-pointer-to-int-cast",str(d/"native.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 genuine external CC1101 TX DMA2 original-C HOST PASS")
    print("External plugin void RX BUSY and physical RF are separate gates.")

if __name__=="__main__":
    main()
