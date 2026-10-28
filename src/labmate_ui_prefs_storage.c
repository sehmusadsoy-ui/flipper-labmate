#include "labmate_ui_prefs_storage.h"

#include <furi.h>
#include <storage/storage.h>
#include <string.h>

#define UI_PREFS_DIR "/ext/apps_data/labmate"
static const char* const ui_prefs_paths[2] = {
    UI_PREFS_DIR "/ui_prefs_a.bin",
    UI_PREFS_DIR "/ui_prefs_b.bin",
};

/* A failed open still requires file_close (same ownership rule as profiles). */
static bool ui_prefs_read(Storage* storage, uint8_t slot, uint8_t* bytes) {
    File* file = storage_file_alloc(storage);
    if(!file) return false;
    const bool opened = storage_file_open(
        file, ui_prefs_paths[slot], FSAM_READ, FSOM_OPEN_EXISTING);
    bool ok = opened;
    if(ok) ok = storage_file_size(file) == LABMATE_UI_PREFS_BYTES &&
                storage_file_read(file, bytes, LABMATE_UI_PREFS_BYTES) ==
                    LABMATE_UI_PREFS_BYTES;
    const bool closed = storage_file_close(file);
    storage_file_free(file);
    return ok && closed;
}

LabMateUiPrefsIoResult labmate_ui_prefs_sd_load(
    LabMateUiPreferences* prefs, uint8_t* active_copy) {
    if(!prefs || !active_copy) return LabMateUiPrefsIoError;
    labmate_ui_prefs_defaults(prefs);
    *active_copy = LABMATE_UI_PREFS_COPY_NONE;
    Storage* storage = furi_record_open(RECORD_STORAGE);
    if(!storage) return LabMateUiPrefsIoError;
    if(storage_sd_status(storage) != FSE_OK) {
        furi_record_close(RECORD_STORAGE);
        return LabMateUiPrefsIoError;
    }
    if(!storage_dir_exists(storage, UI_PREFS_DIR)) {
        furi_record_close(RECORD_STORAGE);
        return LabMateUiPrefsIoEmpty;
    }
    bool any_exists = false;
    bool valid = false;
    uint8_t bytes[LABMATE_UI_PREFS_BYTES];
    for(uint8_t i = 0U; i < 2U; ++i) {
        if(!storage_file_exists(storage, ui_prefs_paths[i])) continue;
        any_exists = true;
        LabMateUiPreferences candidate;
        if(!ui_prefs_read(storage, i, bytes) ||
           !labmate_ui_prefs_decode(&candidate, bytes, sizeof(bytes))) continue;
        if(!valid || labmate_ui_prefs_is_newer(candidate.generation, prefs->generation)) {
            *prefs = candidate;
            *active_copy = i;
            valid = true;
        }
    }
    furi_record_close(RECORD_STORAGE);
    return valid ? LabMateUiPrefsIoOk :
           (any_exists ? LabMateUiPrefsIoCorrupt : LabMateUiPrefsIoEmpty);
}

bool labmate_ui_prefs_sd_save(
    const LabMateUiPreferences* prefs, uint8_t active_copy, uint8_t* written_copy) {
    if(!prefs || !written_copy ||
       (active_copy != 0U && active_copy != 1U &&
        active_copy != LABMATE_UI_PREFS_COPY_NONE)) return false;
    uint8_t bytes[LABMATE_UI_PREFS_BYTES];
    if(!labmate_ui_prefs_encode(prefs, bytes)) return false;
    const uint8_t target = active_copy == 0U ? 1U : 0U;
    Storage* storage = furi_record_open(RECORD_STORAGE);
    if(!storage) return false;
    bool ok = storage_sd_status(storage) == FSE_OK &&
              storage_simply_mkdir(storage, UI_PREFS_DIR);
    if(ok) {
        File* file = storage_file_alloc(storage);
        if(!file) ok = false;
        else {
            const bool opened = storage_file_open(
                file, ui_prefs_paths[target], FSAM_WRITE, FSOM_CREATE_ALWAYS);
            ok = opened &&
                 storage_file_write(file, bytes, sizeof(bytes)) == sizeof(bytes);
            if(ok) ok = storage_file_sync(file);
            const bool closed = storage_file_close(file);
            if(!closed) ok = false;
            storage_file_free(file);
        }
    }
    if(ok) {
        uint8_t readback[LABMATE_UI_PREFS_BYTES];
        LabMateUiPreferences decoded;
        ok = ui_prefs_read(storage, target, readback) &&
             memcmp(readback, bytes, sizeof(bytes)) == 0 &&
             labmate_ui_prefs_decode(&decoded, readback, sizeof(readback));
    }
    furi_record_close(RECORD_STORAGE);
    if(ok) *written_copy = target;
    return ok;
}
