#!/usr/bin/env python3
"""E11 additive V2 resource mask for native TIM16/DMAMUX/DMA2 CH3-5.

Keep every existing uint32_t V1 ABI and owner handle intact. V2 is a
separate exact-mask uint64_t API that atomically shares low 32 resource
bits with V1, so existing NFC/RFID/JS clients remain collision-safe.
Dormant: no new driver is migrated until genuine source-C tests pass.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_ext_cc1101_rx_lease import EXPECTED as EXT_PRE,H,R,EXT,EXT_H
from patch_momentum_native_serial_expansion_exti_lease import API

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
EXPECTED=EXT_PRE | {H,R,EXT,EXT_H}
MARK="/* E11 additive 64-bit lease V2: no V1 ABI migration. */"

def one(s,old,new):
    if s.count(old)!=1: raise ValueError("Pinned V2 lease source mismatch "+repr(old[:110]))
    return s.replace(old,new,1)

def patch(h,r,api):
    if MARK in r or "FURI_HAL_RESOURCE_LEASE_API_V2" in h:
        raise ValueError("Extended lease V2 already present")
    h=one(h,
        "#define FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX (FuriHalLeaseTim17|FuriHalLeasePb2|FuriHalLeaseExti2)\n",
        """#define FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX (FuriHalLeaseTim17|FuriHalLeasePb2|FuriHalLeaseExti2)
/* Additive E11 V2 mask. No old 32-bit lease API type changes. */
#define FURI_HAL_RESOURCE_LEASE_API_V2 1
#define FuriHalLeaseTim16 (UINT64_C(1)<<32)
#define FuriHalLeaseDma2Ch3 (UINT64_C(1)<<33)
#define FuriHalLeaseDma2Ch4 (UINT64_C(1)<<34)
#define FuriHalLeaseDma2Ch5 (UINT64_C(1)<<35)
#define FuriHalLeaseDmamuxRg0 (UINT64_C(1)<<36)
/* SignalReader NFC ISO15693 listener: internal PA2/EXTI2 handoff. */
#define FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC \\
 ((uint64_t)FuriHalLeasePa2|(uint64_t)FuriHalLeaseExti2|FuriHalLeaseTim16| \\
 (uint64_t)FuriHalLeaseDma2Ch2|FuriHalLeaseDma2Ch3|FuriHalLeaseDma2Ch5|FuriHalLeaseDmamuxRg0)
/* External CC1101 TX: TIM17, external G0 PB2, DMA2 channels 3/4/5. */
#define FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX \\
 ((uint64_t)FuriHalLeaseTim17|(uint64_t)FuriHalLeasePb2| \\
 FuriHalLeaseDma2Ch3|FuriHalLeaseDma2Ch4|FuriHalLeaseDma2Ch5)
/* V2 opaque handle in same monotonically increasing ID namespace as V1. */
uint32_t furi_hal_resource_lease_v2_try_acquire(uint64_t resources);
bool furi_hal_resource_lease_v2_release(uint32_t owner,uint64_t resources);
""")
    r=one(r,"const GpioPinRecord* furi_hal_resources_pin_by_number(uint8_t number) {",
        """/* E11 additive 64-bit lease V2: no V1 ABI migration.
 * Low bits are shared with every existing V1 lease. High bits are
 * exclusively reserved for TIM16/DMA2 CH3/4/5/DMAMUX generator zero.
 * Exact enum composite masks prohibit partial/stolen resource releases.
 */
#define FURI_HAL_LEASE_V2_MAX_CLAIMS 8U
typedef struct {
    uint32_t handle;
    uint64_t mask;
} FuriHalLeaseV2Claim;
static FuriHalLeaseV2Claim furi_hal_lease_v2_claims[FURI_HAL_LEASE_V2_MAX_CLAIMS];
static uint32_t furi_hal_lease_used_hi;

static bool furi_hal_lease_v2_mask_allowed(uint64_t mask) {
    return mask==FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC ||
           mask==FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX;
}

uint32_t furi_hal_resource_lease_v2_try_acquire(uint64_t resources) {
    if(!furi_hal_lease_v2_mask_allowed(resources)) return 0U;
    const uint32_t low=(uint32_t)resources;
    const uint32_t high=(uint32_t)(resources>>32);
    uint32_t handle=0U;
    FURI_CRITICAL_ENTER();
    if(!(furi_hal_lease_used & low) &&
       !(furi_hal_lease_used_hi & high) &&
       furi_hal_lease_last_handle!=UINT32_MAX) {
        for(size_t i=0U;i<FURI_HAL_LEASE_V2_MAX_CLAIMS;i++) {
            if(furi_hal_lease_v2_claims[i].handle==0U) {
                handle=++furi_hal_lease_last_handle;
                furi_hal_lease_v2_claims[i].handle=handle;
                furi_hal_lease_v2_claims[i].mask=resources;
                furi_hal_lease_used |= low;
                furi_hal_lease_used_hi |= high;
                break;
            }
        }
    }
    FURI_CRITICAL_EXIT();
    return handle;
}

bool furi_hal_resource_lease_v2_release(uint32_t owner,uint64_t resources) {
    if(!owner || !furi_hal_lease_v2_mask_allowed(resources)) return false;
    bool released=false;
    FURI_CRITICAL_ENTER();
    for(size_t i=0U;i<FURI_HAL_LEASE_V2_MAX_CLAIMS;i++) {
        if(furi_hal_lease_v2_claims[i].handle==owner &&
           furi_hal_lease_v2_claims[i].mask==resources) {
            furi_hal_lease_used &= ~((uint32_t)resources);
            furi_hal_lease_used_hi &= ~((uint32_t)(resources>>32));
            furi_hal_lease_v2_claims[i].handle=0U;
            furi_hal_lease_v2_claims[i].mask=0U;
            released=true;
            break;
        }
    }
    FURI_CRITICAL_EXIT();
    return released;
}

const GpioPinRecord* furi_hal_resources_pin_by_number(uint8_t number) {""")
    api=one(api,
        "Function,+,furi_hal_resource_lease_try_acquire,uint32_t,uint32_t\n",
        "Function,+,furi_hal_resource_lease_try_acquire,uint32_t,uint32_t\n"
        'Function,+,furi_hal_resource_lease_v2_release,_Bool,"uint32_t, uint64_t"\n'
        "Function,+,furi_hal_resource_lease_v2_try_acquire,uint32_t,uint64_t\n")
    return h,r,api

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("firmware_root",type=Path)
    parser.add_argument("--apply",action="store_true")
    a=parser.parse_args();root=a.firmware_root.resolve()
    try:
        sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if sha!=PIN: raise ValueError("Wrong Momentum source revision")
        dirty=set()
        for line in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Unreviewed/renamed source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unexpected source delta "+repr(sorted(dirty^EXPECTED)))
        paths=(H,R,API)
        old=[(root/p).read_text(encoding="utf-8") for p in paths]
        new=patch(*old)
        print("E11 V2 64-BIT ADDITIVE LEASE SOURCE PREFLIGHT PASS")
        if a.apply:
            for p,v in zip(paths,new): (root/p).write_text(v,encoding="utf-8")
            print("DORMANT EXTENDED RESOURCE ALLOCATOR SOURCE ONLY; NO FLASH")
        else:
            print("READ-ONLY; unchanged")
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print("E11 LEASE V2 SOURCE REFUSED: "+str(exc),file=sys.stderr)
        raise SystemExit(1)

if __name__=="__main__":
    main()
