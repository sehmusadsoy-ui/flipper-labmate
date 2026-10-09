#pragma once
#include "labmate_profiles.h"
#include <stdint.h>

/* Redundant SD copies: only the inactive 32-byte record is overwritten.
 * Neither function touches CSV files, GPIO, PWM, or an active capture.
 * Calling code MUST call these functions outside the GUI mutex.
 */
#define LABMATE_PROFILE_COPY_NONE 255U

typedef enum {
    LabMateProfileIoOk,
    LabMateProfileIoEmpty,
    LabMateProfileIoCorrupt,
    LabMateProfileIoError,
} LabMateProfileIoResult;

/* If at least one intact copy is found, returns Ok and its index (0/1).
 * Empty is a clean first run; Corrupt means file(s) exist but none valid.
 * Storage errors refuse writes rather than risking a good copy.
 */
LabMateProfileIoResult labmate_profile_sd_load(
    LabMateProfileStore* profiles,
    uint8_t* active_copy);

/* Writes to the inactive copy, syncs/closes, reads and verifies all 32 bytes.
 * current_copy must be a value returned by sd_load or COPY_NONE.
 * On failure the previously active copy is not modified by this function.
 */
bool labmate_profile_sd_save(
    const LabMateProfileStore* profiles,
    uint8_t current_copy,
    uint8_t* new_copy);
