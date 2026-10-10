#include "labmate_history.h"
#include "labmate_logger_codec.h"
#include "labmate_storage_paths.h"

#include <stdio.h>
#include <string.h>

#define LOGGER_DIR LABMATE_LOGGER_DIR
/* Preserve v1.5 bounded incremental SD reads. */
#define LOGGER_HISTORY_READ_BYTES 256U

/* ---------- READ-ONLY LOG HISTORY v1.5 ---------- */
/* No delete/rename/truncate calls are made from the history browser. */

/* Called without the UI mutex; copies the result under the mutex. */
void labmate_history_scan(LabMateApp* app) {
    uint16_t latest[LOGGER_HISTORY_LIMIT] = {0};
    uint8_t count = 0U;
    uint32_t total = 0U;
    bool ok = false;

    Storage* storage = furi_record_open(RECORD_STORAGE);
    File* dir = NULL;
    if(storage && storage_sd_status(storage) == FSE_OK &&
       storage_dir_exists(storage, LOGGER_DIR)) {
        dir = storage_file_alloc(storage);
        if(dir) {
            if(storage_dir_open(dir, LOGGER_DIR)) {
                ok = true;
                FileInfo info;
                char name[64];
                while(storage_dir_read(dir, &info, name, sizeof(name))) {
                    uint16_t id;
                    if(file_info_is_dir(&info) || !labmate_logger_filename_id(name, &id)) continue;
                    ++total;
                    uint8_t insert = 0U;
                    while(insert < count && latest[insert] > id) ++insert;
                    if(insert >= LOGGER_HISTORY_LIMIT) continue;
                    if(count < LOGGER_HISTORY_LIMIT) ++count;
                    for(uint8_t j = count - 1U; j > insert; --j) {
                        latest[j] = latest[j - 1U];
                    }
                    latest[insert] = id;
                }
                if(storage_file_get_error(dir) != FSE_NOT_EXIST &&
                   storage_file_get_error(dir) != FSE_OK) ok = false;
            }
            /* Directory handles must be closed even if open fails. */
            storage_dir_close(dir);
            storage_file_free(dir);
        }
    }
    if(storage) furi_record_close(RECORD_STORAGE);

    furi_mutex_acquire(app->mutex, FuriWaitForever);
    app->history_count = ok ? count : 0U;
    app->history_total = ok ? total : 0U;
    app->history_selected = 0U;
    if(ok) memcpy(app->history_ids, latest, sizeof(latest));
    app->history_error = !ok;
    app->history_busy = false;
    furi_mutex_release(app->mutex);
}

void labmate_history_close(LabMateApp* app) {
    if(app->history_file) {
        if(storage_file_is_open(app->history_file)) {
            storage_file_close(app->history_file);
        }
        storage_file_free(app->history_file);
        app->history_file = NULL;
    }
    if(app->history_storage) {
        furi_record_close(RECORD_STORAGE);
        app->history_storage = NULL;
    }
}

/* Called outside the UI mutex; does not interfere with active log files. */
void labmate_history_open(LabMateApp* app) {
    labmate_history_close(app);
    bool ok = false;
    Storage* storage = NULL;
    File* file = NULL;
    if(app->history_selected < app->history_count) {
        char path[96];
        snprintf(
            path, sizeof(path), LOGGER_DIR "/log_%04u.csv",
            (unsigned int)app->history_ids[app->history_selected]);
        storage = furi_record_open(RECORD_STORAGE);
        if(storage && storage_sd_status(storage) == FSE_OK) {
            file = storage_file_alloc(storage);
            if(file && storage_file_open(file, path, FSAM_READ, FSOM_OPEN_EXISTING)) {
                ok = true;
            } else if(file) {
                /* Required even on failed open. */
                storage_file_close(file);
            }
        }
    }
    if(!ok) {
        if(file) storage_file_free(file);
        if(storage) furi_record_close(RECORD_STORAGE);
    }
    furi_mutex_acquire(app->mutex, FuriWaitForever);
    app->history_storage = ok ? storage : NULL;
    app->history_file = ok ? file : NULL;
    app->history_rows = 0U;
    app->history_last_ms = 0U;
    app->history_line_ms = 0U;
    app->history_past_header = false;
    app->history_line_has_comma = false;
    app->history_in_timestamp = true;
    app->history_mode = 0U; /* unknown until first data row */
    app->history_first_row_len = 0U;
    app->history_first_row[0] = '\0';
    app->history_error = !ok;
    app->history_loading = ok;
    app->history_busy = false;
    furi_mutex_release(app->mutex);
}

/* Parse at most one small SD chunk per main-loop iteration. */
void labmate_history_read_step(LabMateApp* app) {
    if(!app->history_file || !app->history_loading) return;
    uint8_t bytes[LOGGER_HISTORY_READ_BYTES];
    size_t size = storage_file_read(app->history_file, bytes, sizeof(bytes));
    bool finished = size == 0U;
    bool ok = true;
    if(finished && !storage_file_eof(app->history_file)) ok = false;

    furi_mutex_acquire(app->mutex, FuriWaitForever);
    for(size_t i = 0; i < size; ++i) {
        const char ch = (char)bytes[i];
        if(ch == '\n') {
            if(app->history_past_header && app->history_line_has_comma) {
                if(app->history_rows == 0U) {
                    app->history_first_row[app->history_first_row_len] = '\0';
                    if(strstr(app->history_first_row, ",PULSE,PC1,")) {
                        app->history_mode = 3U;
                    } else if(strstr(app->history_first_row, ",FREQ,PB3,")) {
                        app->history_mode = 2U;
                    } else if(strstr(app->history_first_row, ",FREQ,PC1,")) {
                        app->history_mode = 1U;
                    }
                }
                ++app->history_rows;
                app->history_last_ms = app->history_line_ms;
            }
            app->history_past_header = true;
            app->history_line_has_comma = false;
            app->history_line_ms = 0U;
            app->history_in_timestamp = true;
            continue;
        }
        if(!app->history_past_header) continue;
        if(app->history_rows == 0U &&
           app->history_first_row_len < sizeof(app->history_first_row) - 1U) {
            app->history_first_row[app->history_first_row_len++] = ch;
        }
        if(ch == ',') {
            app->history_line_has_comma = true;
            app->history_in_timestamp = false;
        } else if(app->history_in_timestamp) {
            if(ch >= '0' && ch <= '9' && app->history_line_ms <= 429496729U) {
                app->history_line_ms =
                    app->history_line_ms * 10U + (uint32_t)(ch - '0');
            } else {
                app->history_in_timestamp = false;
            }
        }
    }
    if(finished) {
        app->history_loading = false;
        if(!ok) app->history_error = true;
    }
    furi_mutex_release(app->mutex);
    if(finished) labmate_history_close(app);
}
