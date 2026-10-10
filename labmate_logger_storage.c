#include "labmate_logger_storage.h"
#include "labmate_logger_codec.h"
#include "labmate_storage_paths.h"

#include <stdio.h>
#include <string.h>

/* Backward compatible microSD directory and file names. */
#define LOGGER_DIR LABMATE_LOGGER_DIR

void labmate_logger_storage_stop(LabMateApp* app) {
    app->logger_recording = false;
    if(app->logger_file) {
        const bool was_open = storage_file_is_open(app->logger_file);
        if(was_open && !storage_file_sync(app->logger_file)) {
            app->logger_error = true;
        }
        /* Storage requires close even if an earlier open failed. A handle
         * that was never opened need not turn an existing error into a
         * second close error. Keep all SD work outside the GUI mutex. */
        if(!storage_file_close(app->logger_file) && was_open) {
            app->logger_error = true;
        }
        storage_file_free(app->logger_file);
        app->logger_file = NULL;
    }
    if(app->logger_storage) {
        furi_record_close(RECORD_STORAGE);
        app->logger_storage = NULL;
    }
}

/* Read the highest existing CSV ID once per application session.
 * Keep naming monotonic even if older files were deleted. All filesystem
 * work occurs from the app loop, after releasing the UI mutex. */
static bool logger_init_next_file_index(LabMateApp* app) {
    if(app->logger_next_file_index != 0U) return true;
    File* dir = storage_file_alloc(app->logger_storage);
    if(!dir) return false;

    bool ok = storage_dir_open(dir, LOGGER_DIR);
    uint16_t max_id = 0U;
    if(ok) {
        FileInfo info;
        char name[64];
        while(storage_dir_read(dir, &info, name, sizeof(name))) {
            uint16_t id;
            if(!file_info_is_dir(&info) &&
               labmate_logger_filename_id(name, &id) && id > max_id) {
                max_id = id;
            }
        }
        FS_Error error = storage_file_get_error(dir);
        if(error != FSE_NOT_EXIST && error != FSE_OK) ok = false;
    }
    /* Storage API requires close even after a failed open. */
    if(!storage_dir_close(dir)) ok = false;
    storage_file_free(dir);
    if(ok) app->logger_next_file_index = (uint32_t)max_id + 1U;
    return ok;
}

bool labmate_logger_storage_start(LabMateApp* app) {
    if(app->logger_recording) return true;
    /* A lost signal is NOT an acquisition failure and still records valid=0.
     * Reject only a software owner / selected pin / active flags mismatch.
     */
    const LabMateCaptureOwner expected =
        (app->logger_source == LoggerPulse) ? LabMateCapturePulse :
        (app->logger_source == LoggerFrequencyHigh) ? LabMateCaptureFrequencyHigh :
                                                       LabMateCaptureFrequencyLow;
    if(!labmate_capture_matches(
           app->capture_owner, expected,
           app->gpio_index, app->capture_pin_index,
           app->frequency_irq_active, app->frequency_hw_active,
           app->pulse_irq_active)) {
        app->capture_blocked = true;
        return false;
    }
    app->capture_blocked = false;
    app->logger_error = false;
    app->logger_rows = 0U;
    app->logger_path[0] = '\0';

    app->logger_storage = furi_record_open(RECORD_STORAGE);
    if(!app->logger_storage ||
       storage_sd_status(app->logger_storage) != FSE_OK ||
       !storage_simply_mkdir(app->logger_storage, LOGGER_DIR)) {
        app->logger_error = true;
        labmate_logger_storage_stop(app);
        return false;
    }

    if(!logger_init_next_file_index(app)) {
        app->logger_error = true;
        labmate_logger_storage_stop(app);
        return false;
    }

    app->logger_file = storage_file_alloc(app->logger_storage);
    if(!app->logger_file) {
        app->logger_error = true;
        labmate_logger_storage_stop(app);
        return false;
    }

    bool opened = false;
    /* Skip old IDs, including when files have been deleted; if the app is
     * restarted, a one-time scan chooses highest existing ID + 1.
     * This also avoids blocking opens on paths known to exist. */
    uint32_t first_index = app->logger_next_file_index;
    for(uint32_t i = first_index; i <= 9999U; ++i) {
        snprintf(
            app->logger_path, sizeof(app->logger_path),
            LOGGER_DIR "/log_%04lu.csv", (unsigned long)i);
        if(storage_file_exists(app->logger_storage, app->logger_path)) continue;
        /* CREATE_NEW is still essential for no-overwrite safety. */
        if(storage_file_open(
               app->logger_file, app->logger_path, FSAM_WRITE, FSOM_CREATE_NEW)) {
            opened = true;
            app->logger_next_file_index = i + 1U;
            break;
        }
        /* Handle the rare case another app created the file after our
         * existence check; all other errors should stop the search. */
        if(storage_file_get_error(app->logger_file) != FSE_EXIST) break;
    }

    if(!opened) {
        app->logger_error = true;
        labmate_logger_storage_stop(app);
        return false;
    }

    const char* header =
        "elapsed_ms,source,pin,valid,frequency_hz,high_us,low_us,period_us,duty_pct\n";
    const size_t header_size = strlen(header);
    if(storage_file_write(app->logger_file, header, header_size) != header_size) {
        app->logger_error = true;
        labmate_logger_storage_stop(app);
        return false;
    }

    app->logger_start_tick = furi_get_tick();
    app->logger_last_tick = app->logger_start_tick;
    app->logger_recording = true;
    return true;
}
