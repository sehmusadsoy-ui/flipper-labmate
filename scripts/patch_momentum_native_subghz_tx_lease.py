#!/usr/bin/env python3
"""E11 pinned SubGHz TX TIM2 + DMA2 CH1(+CH2 for mirror) atomic owner.

Preserve original bool TX API and region rules. Unknown mirror pins or
special GPIO build configurations fail closed rather than run unleased.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_subghz_rx_busy_callers import EXPECTED as RX_CALLER_PRE, I,IH,D,DH,APP

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
H="targets/f7/furi_hal/furi_hal_resources.h"
R="targets/f7/furi_hal/furi_hal_resources.c"
S="targets/f7/furi_hal/furi_hal_subghz.c"
PUB="targets/f7/furi_hal/furi_hal_subghz.h"
EXPECTED=RX_CALLER_PRE | {I,IH,D,DH,APP}
MARK="/* E11 native SubGHz TX TIM2/DMA2 lease owner. */"

def once(s,old,new):
    if s.count(old)!=1:
        raise ValueError("Pinned SubGHz TX source anchor missing/ambiguous "+repr(old[:125]))
    return s.replace(old,new,1)

def patch(h,r,src):
    if MARK in src or "FURI_HAL_LEASE_NATIVE_SUBGHZ_TX" in h:
        raise ValueError("SubGHz TX owner already present")
    if "/* E11 native SubGHz RX TIM2 cooperative owner. */" not in src:
        raise ValueError("Missing SubGHz RX predecessor")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3 (FuriHalLeaseTim2|FuriHalLeasePb3)\n",
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3 (FuriHalLeaseTim2|FuriHalLeasePb3)\n"
        "/* TX: DMA2 CH1 always, CH2 only for a validated debug mirror. */\n"
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE (FuriHalLeaseTim2|FuriHalLeaseDma2Ch1)\n"
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PA7 (FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2|FuriHalLeasePa7)\n"
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3 (FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2|FuriHalLeasePb3)\n")
    r=once(r,
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PA7 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3 ||\n")
    src=once(src,
        '''    if(e11_subghz_rx_handle || e11_subghz_rx_fault) return;
    furi_hal_subghz.async_mirror_pin = pin;''',
        '''    if(e11_subghz_rx_handle || e11_subghz_rx_fault ||
       e11_subghz_tx_handle || e11_subghz_tx_fault) return;
    furi_hal_subghz.async_mirror_pin = pin;''')
    src=once(src,
        '''static void furi_hal_subghz_async_tx_dma_isr(void* context) {
    UNUSED(context);
    furi_check(furi_hal_subghz.state == SubGhzStateAsyncTx);''',
        '''/* E11 native SubGHz TX TIM2/DMA2 lease owner. */
static uint32_t e11_subghz_tx_handle;
static uint32_t e11_subghz_tx_mask;
static bool e11_subghz_tx_fault;

static uint32_t e11_subghz_tx_mask_for_mirror(const GpioPin* mirror) {
    if(!mirror) return FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE;
    if(mirror==&gpio_ext_pa7) return FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PA7;
    if(mirror==&gpio_ext_pb3) return FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3;
    return 0U;
}

static bool e11_subghz_tx_ready(void) {
    if(!e11_subghz_tx_handle || e11_subghz_tx_fault) return false;
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM2) ||
       !LL_DMA_IsEnabledChannel(SUBGHZ_DMA_CH1_DEF) ||
       (furi_hal_subghz.async_mirror_pin &&
        !LL_DMA_IsEnabledChannel(SUBGHZ_DMA_CH2_DEF))) {
        e11_subghz_tx_fault=true;
        return false;
    }
    return true;
}

static bool e11_subghz_tx_release(void) {
    if(!e11_subghz_tx_handle || e11_subghz_tx_fault) return false;
    if(furi_hal_resource_lease_release(e11_subghz_tx_handle,e11_subghz_tx_mask)) {
        e11_subghz_tx_handle=0U;
        e11_subghz_tx_mask=0U;
        return true;
    }
    e11_subghz_tx_fault=true;
    return false;
}

static void furi_hal_subghz_async_tx_dma_isr(void* context) {
    UNUSED(context);
    if(!e11_subghz_tx_ready()) return;
    if(furi_hal_subghz.state != SubGhzStateAsyncTx) {
        e11_subghz_tx_fault=true;
        return;
    }''')
    # Source order: mirror setter occurs before TX helper definitions.
    # Add forward global declarations above setter, but avoid duplicate definitions.
    marker='static uint32_t e11_subghz_rx_handle;\n'
    src=once(src,marker,
        'static uint32_t e11_subghz_rx_handle;\n'
        'static uint32_t e11_subghz_tx_handle;\n'
        'static uint32_t e11_subghz_tx_mask;\n'
        'static bool e11_subghz_tx_fault;\n')
    src=once(src,
        '''/* E11 native SubGHz TX TIM2/DMA2 lease owner. */
static uint32_t e11_subghz_tx_handle;
static uint32_t e11_subghz_tx_mask;
static bool e11_subghz_tx_fault;''',
        '''/* E11 native SubGHz TX TIM2/DMA2 lease owner. */''')
    src=once(src,
        '''bool furi_hal_subghz_start_async_tx(FuriHalSubGhzAsyncTxCallback callback, void* context) {
    furi_check(furi_hal_subghz.state == SubGhzStateIdle);
    furi_check(callback);

    //If transmission is prohibited by regional settings
    if(furi_hal_subghz.regulation != SubGhzRegulationTxRx) return false;

    furi_hal_subghz_async_tx.callback = callback;''',
        '''bool furi_hal_subghz_start_async_tx(FuriHalSubGhzAsyncTxCallback callback, void* context) {
    if(furi_hal_subghz.state != SubGhzStateIdle || !callback ||
       e11_subghz_tx_handle || e11_subghz_tx_fault) return false;

    // Keep the native regulatory prohibition before touching any hardware.
    if(furi_hal_subghz.regulation != SubGhzRegulationTxRx) return false;

#ifdef FURI_HAL_SUBGHZ_TX_GPIO
#error E11: optional TX GPIO requires a separately reviewed atomic pin owner
#endif
    const uint32_t mask=e11_subghz_tx_mask_for_mirror(furi_hal_subghz.async_mirror_pin);
    if(!mask) {
        FURI_LOG_W(TAG, "SubGHz TX mirror GPIO is not lease-managed");
        return false;
    }
    const uint32_t lease=furi_hal_resource_lease_try_acquire(mask);
    if(!lease) return false;
    /* Legacy TIM2 or DMA2 CH1/CH2 bypasses can still be live. */
    if(furi_hal_bus_is_enabled(FuriHalBusTIM2) ||
       LL_DMA_IsEnabledChannel(SUBGHZ_DMA_CH1_DEF) ||
       (furi_hal_subghz.async_mirror_pin &&
        LL_DMA_IsEnabledChannel(SUBGHZ_DMA_CH2_DEF))) {
        if(!furi_hal_resource_lease_release(lease,mask)) {
            e11_subghz_tx_handle=lease;
            e11_subghz_tx_mask=mask;
            e11_subghz_tx_fault=true;
        }
        return false;
    }
    e11_subghz_tx_handle=lease;
    e11_subghz_tx_mask=mask;

    furi_hal_subghz_async_tx.callback = callback;''')
    src=once(src,
        '''    furi_hal_subghz_async_tx.buffer =
        malloc(FURI_HAL_SUBGHZ_ASYNC_TX_BUFFER_FULL * sizeof(uint32_t));

    // Here we use TIM2_CH2''',
        '''    furi_hal_subghz_async_tx.buffer =
        malloc(FURI_HAL_SUBGHZ_ASYNC_TX_BUFFER_FULL * sizeof(uint32_t));
    if(!furi_hal_subghz_async_tx.buffer) {
        /* No pin/DMA/IRQ/timer write occurred; undo owned claim. */
        furi_hal_subghz.state=SubGhzStateIdle;
        furi_hal_subghz_async_tx.callback=NULL;
        furi_hal_subghz_async_tx.callback_context=NULL;
        (void)e11_subghz_tx_release();
        return false;
    }

    // Here we use TIM2_CH2''')
    src=once(src,
        '''bool furi_hal_subghz_is_async_tx_complete(void) {
    return (furi_hal_subghz.state == SubGhzStateAsyncTx) && (LL_TIM_GetAutoReload(TIM2) == 0);
}''',
        '''bool furi_hal_subghz_is_async_tx_complete(void) {
    if(!e11_subghz_tx_ready()) return false;
    return (furi_hal_subghz.state == SubGhzStateAsyncTx) && (LL_TIM_GetAutoReload(TIM2) == 0);
}''')
    src=once(src,
        '''void furi_hal_subghz_stop_async_tx(void) {
    furi_check(furi_hal_subghz.state == SubGhzStateAsyncTx);

    // Shutdown radio''',
        '''void furi_hal_subghz_stop_async_tx(void) {
    if(!e11_subghz_tx_ready()) return;
    if(furi_hal_subghz.state != SubGhzStateAsyncTx) {
        e11_subghz_tx_fault=true;
        return;
    }

    // Shutdown radio''')
    src=once(src,
        '''    furi_hal_subghz.state = SubGhzStateIdle;
}

''',
        '''    furi_hal_subghz.state = SubGhzStateIdle;
    furi_hal_subghz_async_tx.buffer=NULL;
    furi_hal_subghz_async_tx.callback=NULL;
    furi_hal_subghz_async_tx.callback_context=NULL;
    (void)e11_subghz_tx_release();
}

''') if False else src
    # Scope exact final TX stop tail (never touch a separate Idle transition).
    txstart=src.index("void furi_hal_subghz_stop_async_tx(void) {")
    txend=src.index("\n}",txstart)+2
    stop=src[txstart:txend]
    if stop.count("    furi_hal_subghz.state = SubGhzStateIdle;")!=1:
        raise ValueError("Native TX STOP tail changed")
    stop=stop.replace(
        "    furi_hal_subghz.state = SubGhzStateIdle;",
        "    furi_hal_subghz.state = SubGhzStateIdle;\n"
        "    furi_hal_subghz_async_tx.buffer=NULL;\n"
        "    furi_hal_subghz_async_tx.callback=NULL;\n"
        "    furi_hal_subghz_async_tx.callback_context=NULL;\n"
        "    (void)e11_subghz_tx_release();")
    src=src[:txstart]+stop+src[txend:]
    return h,r,src

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PIN: raise ValueError("Unpinned Momentum SHA")
        dirty=set()
        for line in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked/renamed source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed native stage "+repr(sorted(dirty^EXPECTED)))
        paths=(H,R,S)
        old=[(root/p).read_text(encoding="utf-8") for p in paths]
        new=patch(*old)
        print("E11 SUBGHZ TX ATOMIC TIM2/DMA2 SOURCE PREFLIGHT PASS")
        if a.apply:
            for name,contents in zip(paths,new):
                (root/name).write_text(contents,encoding="utf-8")
            print("TX SOURCE PATCHED; NO FLASH, NO DEVICE, NO EXTERNAL PLUGIN ABI CHANGE")
        else:
            print("READ ONLY; NONE WRITTEN")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 SUBGHZ TX REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
