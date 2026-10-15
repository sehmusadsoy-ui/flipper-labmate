#!/usr/bin/env python3
"""Compile/execute the ACTUAL patched Momentum pulse_reader.c on fake HAL.

Checks denial before any HAL write, successful capture, STOP, no double free,
and fail-sticky release. No physical timing or analog signal evidence.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile

HARNESS=r'''
#include "mock.h"
#include <stdio.h>
#include <string.h>

GpioPort port_a = {0},port_b = {0},port_c = {0};
const GpioPin gpio_ext_pc0={&port_c,1U<<0},gpio_ext_pc1={&port_c,1U<<1};
const GpioPin gpio_ext_pc3={&port_c,1U<<3},gpio_ext_pb2={&port_b,1U<<2};
const GpioPin gpio_ext_pb3={&port_b,1U<<3},gpio_ext_pa4={&port_a,1U<<4};
const GpioPin gpio_ext_pa6={&port_a,1U<<6},gpio_ext_pa7={&port_a,1U<<7};
Timer fake_tim2 = {0};
Counter fake_dwt = {0};
unsigned mock_register_writes, gpio_writes, bus_writes, claims, releases;
static uint32_t used, next_handle;
static uint32_t handles[100],masks[100];
static bool bus_on,dma4_busy,dma5_busy,deny_release;

uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    claims++;
    if(used & mask) return 0U;
    uint32_t h=++next_handle;
    assert(h<100);
    handles[h]=h; masks[h]=mask; used|=mask;
    return h;
}
bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask) {
    releases++;
    if(deny_release) return false;
    if(!h || h>=100 || handles[h]!=h || masks[h]!=mask) return false;
    used&=~mask;handles[h]=masks[h]=0;
    return true;
}
bool furi_hal_bus_is_enabled(FuriHalBus bus) {
    assert(bus==FuriHalBusTIM2);
    return bus_on;
}
void furi_hal_bus_enable(FuriHalBus bus) {
    assert(bus==FuriHalBusTIM2 && !bus_on);
    bus_writes++;bus_on=true;
}
void furi_hal_bus_disable(FuriHalBus bus) {
    assert(bus==FuriHalBusTIM2 && bus_on);
    bus_writes++;bus_on=false;
}
void furi_hal_gpio_init_ex(const GpioPin* p,int mode,int pull,int speed,int alt) {
    (void)mode;(void)pull;(void)speed;(void)alt;
    assert(p && used);
    gpio_writes++;
}
void furi_hal_gpio_init_simple(const GpioPin* p,int mode) {
    furi_hal_gpio_init_ex(p,mode,0,0,0);
}
bool mock_dma_is_enabled(int chan) {
    if(chan==4)return dma4_busy;
    if(chan==5)return dma5_busy;
    abort();
}
uint32_t mock_dma_length(void) {return 0U;}
#define CHECK(x) do{if(!(x)){fprintf(stderr,"E11 PULSE FAIL line %d: %s\n",__LINE__,#x);abort();}}while(0)
static unsigned write_total(void){return mock_register_writes+gpio_writes+bus_writes;}
static void reset_metrics(void){mock_register_writes=gpio_writes=bus_writes=0U;}
int main(void) {
    const GpioPin* pins[] = {
        &gpio_ext_pc0,&gpio_ext_pc1,&gpio_ext_pc3,&gpio_ext_pb2,
        &gpio_ext_pb3,&gpio_ext_pa4,&gpio_ext_pa6,&gpio_ext_pa7,
    };
    uint32_t masks[]={
        FURI_HAL_LEASE_PULSE_PC0,FURI_HAL_LEASE_PULSE_PC1,
        FURI_HAL_LEASE_PULSE_PC3,FURI_HAL_LEASE_PULSE_PB2,
        FURI_HAL_LEASE_PULSE_PB3,FURI_HAL_LEASE_PULSE_PA4,
        FURI_HAL_LEASE_PULSE_PA6,FURI_HAL_LEASE_PULSE_PA7,
    };
    for(unsigned i=0U;i<8U;++i) {
        PulseReader* s=pulse_reader_alloc(pins[i],8U);
        CHECK(s);
        uint32_t foreign=furi_hal_resource_lease_try_acquire(masks[i]);
        CHECK(foreign);
        reset_metrics();
        pulse_reader_start(s);
        CHECK(write_total()==0U && pulse_reader_samples(s)==0U);
        CHECK(pulse_reader_receive(s,0)==PULSE_READER_NO_EDGE);
        pulse_reader_stop(s);
        CHECK(write_total()==0U);
        CHECK(furi_hal_resource_lease_release(foreign,masks[i]));
        reset_metrics();
        pulse_reader_start(s);
        CHECK(bus_on && write_total()>0U && (used & masks[i])==masks[i]);
        CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PB3));
        unsigned writes=write_total();
        pulse_reader_start(s);
        CHECK(write_total()==writes);
        pulse_reader_stop(s);
        CHECK(!bus_on && used==0U);
        writes=write_total();
        pulse_reader_stop(s);
        CHECK(write_total()==writes);
        pulse_reader_free(s);
        CHECK(used==0U);
    }
    /* A legacy TIM2/DMA user must not be modified on denied starts. */
    PulseReader* s=pulse_reader_alloc(&gpio_ext_pb3,8U);
    reset_metrics();
    bus_on=true;
    pulse_reader_start(s);
    CHECK(!write_total() && !pulse_reader_samples(s) && used==0U);
    bus_on=false;
    dma4_busy=true;
    pulse_reader_start(s);
    CHECK(!write_total() && used==0U);
    dma4_busy=false;
    dma5_busy=true;
    pulse_reader_start(s);
    CHECK(!write_total() && used==0U);
    dma5_busy=false;
    /* Preserve historical arbitrary GPIO support: nonconnector pins
     * still reserve TIM2/DMA/DMAMUX core, though their GPIO/EXTI are not
     * protected by the eight connector-specific E11 masks.
     */
    const GpioPin internal={&port_a,1U<<8};
    PulseReader* other=pulse_reader_alloc(&internal,8U);
    reset_metrics();
    pulse_reader_start(other);
    CHECK(bus_on && used==FURI_HAL_LEASE_PULSE_NONCONNECTOR &&
          write_total()>0U);
    pulse_reader_stop(other);
    CHECK(!bus_on && used==0U);
    pulse_reader_free(other);
    /* An external client may construct an equivalent GPIO descriptor
     * instead of using the canonical &gpio_ext_pb3 pointer.
     */
    const GpioPin clone_pb3={&port_b,1U<<3};
    PulseReader* alias=pulse_reader_alloc(&clone_pb3,8U);
    uint32_t monitor=furi_hal_resource_lease_try_acquire(FuriHalLeasePb3);
    CHECK(monitor);
    reset_metrics();
    pulse_reader_start(alias);
    CHECK(write_total()==0U && used==FuriHalLeasePb3);
    CHECK(furi_hal_resource_lease_release(monitor,FuriHalLeasePb3));
    pulse_reader_start(alias);
    CHECK(bus_on && (used & FURI_HAL_LEASE_PULSE_PB3)==FURI_HAL_LEASE_PULSE_PB3);
    pulse_reader_stop(alias);pulse_reader_free(alias);
    CHECK(!bus_on && used==0U);

    /* Repeated starts and close must not tear down a foreign owner. */
    pulse_reader_start(s);
    CHECK(bus_on);
    reset_metrics();
    pulse_reader_free(s); /* frees active DMA, timer, GPIO and own claim */
    CHECK(!bus_on && used==0U && write_total()>0U);

    /* Firmware release failure must retain the contested reservation. */
    s=pulse_reader_alloc(&gpio_ext_pb3,8U);
    unsigned writes=0U;
    pulse_reader_start(s);
    deny_release=true;
    pulse_reader_stop(s);
    CHECK(!bus_on && (used & FURI_HAL_LEASE_PULSE_PB3));
    writes=write_total();
    pulse_reader_start(s);pulse_reader_stop(s);
    CHECK(write_total()==writes);
    CHECK(pulse_reader_receive(s,0)==PULSE_READER_NO_EDGE);
    pulse_reader_free(s);
    CHECK(used & FURI_HAL_LEASE_PULSE_PB3);

    /* Another service disabled TIM2 unexpectedly: STOP cannot
     * assert or reconfigure GPIO; hold old handle sticky instead.
     */
    /* Isolate the next fault case as if firmware rebooted. A real
     * sticky fault remains unsafe until a complete device reset.
     */
    deny_release=false;
    used=0U;next_handle=0U;
    memset(handles,0,sizeof handles);memset(masks,0,sizeof masks);
    PulseReader* s2=pulse_reader_alloc(&gpio_ext_pc0,8U);
    pulse_reader_start(s2);
    CHECK(bus_on);
    bus_on=false;reset_metrics();
    pulse_reader_stop(s2);
    CHECK(!write_total());
    CHECK(pulse_reader_receive(s2,0)==PULSE_READER_NO_EDGE);
    pulse_reader_free(s2);
    CHECK(used & FURI_HAL_LEASE_PULSE_PC0);
    puts("E11 native PulseReader actual C HOST PASS: 8 pins, TIM2/DMA denial, STOP, sticky faults.");
    puts("No physical capture, no global legacy DMA/EXTI interceptor.");
    return 0;
}
'''
def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    args=ap.parse_args()
    root=args.momentum_root.resolve()
    pulse=(root/"lib/pulse_reader/pulse_reader.c").read_text()
    hdr=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    lease=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    marker="/* LabMate E11 native PulseReader single composite-resource claim. */"
    assert pulse.count(marker)==1
    assert "FURI_HAL_LEASE_PULSE_CORE" in hdr
    assert "mask == FURI_HAL_LEASE_PULSE_PB3" in lease
    assert "if(!signal || !signal->capture_active" in pulse
    assert "if(signal->firmware_lease_fault) return;" in pulse
    assert "FURI_HAL_LEASE_PULSE_NONCONNECTOR" in hdr
    assert "if(!furi_hal_bus_is_enabled(FuriHalBusTIM2))" in pulse
    # Compile the real original+patched source, not a reimplemented model.
    macros=set(re.findall(r"\bLL_[A-Z][A-Z0-9_]+\b",pulse))
    funcs=set(re.findall(r"\bLL_[A-Za-z0-9_]+\s*(?=\()",pulse))
    # Only the explicitly read-only HAL calls get functional mocks.
    reads={"LL_DMA_IsEnabledChannel","LL_DMA_GetDataLength"}
    write_funcs=funcs-reads
    mock_def="\n".join(
        f"#define {f}(...) do {{mock_register_writes++;}} while(0)" for f in sorted(write_funcs)
    )
    consts=macros-funcs
    d={"LL_DMA_CHANNEL_4":4, "LL_DMA_CHANNEL_5":5}
    for i in range(16):
        d[f"LL_GPIO_PIN_{i}"]=1<<i
    mock_def+="\n"+"\n".join(f"#define {k} {d.get(k,1)}" for k in sorted(consts))
    mock_def+="\n#define LL_DMA_IsEnabledChannel(d,c) mock_dma_is_enabled(c)\n"
    mock_def+="#define LL_DMA_GetDataLength(d,c) mock_dma_length()\n"
    mock_def+="\n" + "\n".join(
        f"#define LL_DMAMUX_REQ_GEN_EXTI_LINE{i} {i}U" for i in range(16))
    mock_def+="\n"
    # Include exact primitive mask definitions by extracting the source
    # header's E11 declarations, preserving bit alias and conflict semantics.
    lease_start=hdr.index("enum {\n    FuriHalLeaseTim1")
    lease_end=hdr.index("/* Passive GPIO Monitor pin-only claims.")
    lease_defs=hdr[lease_start:lease_end]
    # Current source uses identifier macros in the enum declarations.
    header=r'''
#pragma once
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stddef.h>
typedef struct {uint32_t IDR;} GpioPort;
typedef struct {GpioPort* port;uint32_t pin;} GpioPin;
typedef struct {uint32_t CNT;} Timer;
typedef struct {uint32_t CYCCNT;} Counter;
extern GpioPort port_a,port_b,port_c;
extern const GpioPin gpio_ext_pc0,gpio_ext_pc1,gpio_ext_pc3,gpio_ext_pb2,
    gpio_ext_pb3,gpio_ext_pa4,gpio_ext_pa6,gpio_ext_pa7;
extern Timer fake_tim2;
extern Counter fake_dwt;
#define TIM2 (&fake_tim2)
#define DWT (&fake_dwt)
#define F_TIM2 64000000UL
#define PULSE_READER_NO_EDGE 0xFFFFFFFFUL
#define PULSE_READER_LOST_EDGE 0xFFFFFFFEUL
typedef struct PulseReader PulseReader;
typedef enum {PulseReaderUnit64MHz,PulseReaderUnitPicosecond,
    PulseReaderUnitNanosecond,PulseReaderUnitMicrosecond} PulseReaderUnit;
typedef struct {
 uint32_t Direction,PeriphOrM2MSrcAddress,PeriphOrM2MSrcIncMode;
 uint32_t PeriphOrM2MSrcDataSize,MemoryOrM2MDstAddress;
 uint32_t MemoryOrM2MDstIncMode,MemoryOrM2MDstDataSize;
 uint32_t Mode,PeriphRequest,Priority,NbData;
} LL_DMA_InitTypeDef;
typedef enum { FuriHalBusTIM2 } FuriHalBus;
#define GPIO_NUMBER 16
#define GpioPullNo 0
typedef int GpioPull;
#define GpioModeAnalog 1
#define GpioModeInterruptRiseFall 2
#define GpioSpeedVeryHigh 3
#define GpioAltFnUnused 4
#define DMA1 1
#define furi_assert(x) assert(x)
extern unsigned mock_register_writes;
void furi_hal_gpio_init_ex(const GpioPin*,int,int,int,int);
void furi_hal_gpio_init_simple(const GpioPin*,int);
bool furi_hal_bus_is_enabled(FuriHalBus);
void furi_hal_bus_enable(FuriHalBus);
void furi_hal_bus_disable(FuriHalBus);
uint32_t furi_hal_resource_lease_try_acquire(uint32_t);
bool furi_hal_resource_lease_release(uint32_t,uint32_t);
bool mock_dma_is_enabled(int);
uint32_t mock_dma_length(void);
PulseReader* pulse_reader_alloc(const GpioPin*,uint32_t);
void pulse_reader_free(PulseReader*);
void pulse_reader_start(PulseReader*);
void pulse_reader_stop(PulseReader*);
uint32_t pulse_reader_receive(PulseReader*,int);
uint32_t pulse_reader_samples(PulseReader*);
void pulse_reader_set_timebase(PulseReader*,PulseReaderUnit);
void pulse_reader_set_bittime(PulseReader*,uint32_t);
void pulse_reader_set_pull(PulseReader*,GpioPull);
'''
    with tempfile.TemporaryDirectory(prefix="labmate_native_pulse_") as td:
        d=Path(td)
        (d/"mock.h").write_text(header+"\n"+lease_defs+"\n"+mock_def)
        for name in ("pulse_reader.h","furi.h","furi_hal.h","furi_hal_gpio.h",
                     "furi_hal_resources.h","stm32wbxx_ll_dma.h",
                     "stm32wbxx_ll_dmamux.h","stm32wbxx_ll_tim.h",
                     "stm32wbxx_ll_exti.h"):
            (d/name).write_text('#include "mock.h"\n')
        (d/"host.c").write_text(HARNESS)
        # Compile the unchanged complete C text, copied so local quoted
        # includes resolve to the fake headers rather than pinned originals.
        (d/"pulse_reader.c").write_text(pulse)
        exe=d/"test"
        subprocess.run(
            ["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
             "-Wno-pointer-to-int-cast","-Wno-unused-variable",
             "-I",str(d),str(d/"pulse_reader.c"),
             str(d/"host.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

if __name__=="__main__": main()
