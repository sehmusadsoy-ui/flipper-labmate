#include "labmate_profile_storage.h"

#include <furi.h>
#include <storage/storage.h>
#include <string.h>

#define PROFILE_DIR "/ext/apps_data/labmate"
static const char* const profile_paths[2] = {
    PROFILE_DIR "/profiles_a.bin",
    PROFILE_DIR "/profiles_b.bin",
};

/* Required even for a failed open: the Storage API documents that an
 * attempted open must be followed by a close. Never skip close on error.
 */
static bool profile_read_file(Storage* storage, uint8_t which, uint8_t* bytes) {
    File* file = storage_file_alloc(storage);
    if(!file) return false;

    const bool opened = storage_file_open(
        file, profile_paths[which], FSAM_READ, FSOM_OPEN_EXISTING);
    bool ok = opened;
    if(ok) {
        ok = storage_file_size(file) == LABMATE_PROFILE_BYTES &&
             storage_file_read(file, bytes, LABMATE_PROFILE_BYTES) ==
                 LABMATE_PROFILE_BYTES;
    }

    const bool closed = storage_file_close(file);
    storage_file_free(file);
    return ok && closed;
}

LabMateProfileIoResult labmate_profile_sd_load(
    LabMateProfileStore* profiles,
    uint8_t* active_copy) {
    if(!profiles || !active_copy) return LabMateProfileIoError;

    *active_copy = LABMATE_PROFILE_COPY_NONE;
    labmate_profile_store_init(profiles);

    Storage* storage = furi_record_open(RECORD_STORAGE);
    if(!storage) return LabMateProfileIoError;

    if(storage_sd_status(storage) != FSE_OK) {
        furi_record_close(RECORD_STORAGE);
        return LabMateProfileIoError;
    }
    if(!storage_dir_exists(storage, PROFILE_DIR)) {
        furi_record_close(RECORD_STORAGE);
        return LabMateProfileIoEmpty;
    }

    bool any_exists = false;
    bool valid = false;
    uint8_t candidate[LABMATE_PROFILE_BYTES];
    for(uint8_t i = 0U; i < 2U; ++i) {
        if(!storage_file_exists(storage, profile_paths[i])) continue;
        any_exists = true;

        if(!profile_read_file(storage, i, candidate)) {
            /* A short/torn file is invalid rather than a usable backup.
             * Read/open failures are also rejected as corrupted records.
             */
            continue;
        }

        LabMateProfileStore decoded;
        if(!labmate_profiles_decode(&decoded, candidate, sizeof(candidate))) {
            continue;
        }
        if(!valid || labmate_profiles_is_newer(
                         decoded.generation, profiles->generation)) {
            *profiles = decoded;
            *active_copy = i;
            valid = true;
        }
    }
    furi_record_close(RECORD_STORAGE);

    if(valid) return LabMateProfileIoOk;
    return any_exists ? LabMateProfileIoCorrupt : LabMateProfileIoEmpty;
}

bool labmate_profile_sd_save(
    const LabMateProfileStore* profiles,
    uint8_t current_copy,
    uint8_t* new_copy) {
    if(!profiles || !new_copy ||
       (current_copy != 0U && current_copy != 1U &&
        current_copy != LABMATE_PROFILE_COPY_NONE)) return false;

    uint8_t bytes[LABMATE_PROFILE_BYTES];
    if(!labmate_profiles_encode(profiles, bytes)) return false;

    const uint8_t inactive = current_copy == 0U ? 1U : 0U;

    Storage* storage = furi_record_open(RECORD_STORAGE);
    if(!storage) return false;

    bool ok = storage_sd_status(storage) == FSE_OK &&
              storage_simply_mkdir(storage, PROFILE_DIR);
    if(ok) {
        File* file = storage_file_alloc(storage);
        if(!file) {
            ok = false;
        } else {
            const bool opened = storage_file_open(
                file, profile_paths[inactive], FSAM_WRITE, FSOM_CREATE_ALWAYS);
            ok = opened &&
                 storage_file_write(file, bytes, sizeof(bytes)) == sizeof(bytes);
            if(ok) ok = storage_file_sync(file);
            const bool closed = storage_file_close(file);
            if(!closed) ok = false;
            storage_file_free(file);
        }
    }

    /* An explicit read-back guards against a seemingly successful but
     * incomplete SD write. Keep older known-good copy untouched.
     */
    if(ok) {
        uint8_t verify[LABMATE_PROFILE_BYTES];
        LabMateProfileStore decoded;
        ok = profile_read_file(storage, inactive, verify) &&
             memcmp(bytes, verify, sizeof(bytes)) == 0 &&
             labmate_profiles_decode(&decoded, verify, sizeof(verify));
    }
    furi_record_close(RECORD_STORAGE);

    if(ok) *new_copy = inactive;
    return ok;
}
