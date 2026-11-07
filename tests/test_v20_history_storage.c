/* Exact production History source with read-only storage fakes. No USB/SD. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define LOGGER_HISTORY_LIMIT 32U
#define RECORD_STORAGE "storage"
#define FuriWaitForever 0U
#define FSAM_READ 1U
#define FSOM_OPEN_EXISTING 1U
typedef enum {FSE_OK, FSE_NOT_EXIST, FSE_DENIED, FSE_INTERNAL} FS_Error;
typedef struct {bool directory;} FileInfo;
typedef struct {int unused;} Storage;
typedef struct {bool open; size_t offset; FS_Error error;} File;
typedef struct {
    void* mutex;
    uint16_t history_ids[LOGGER_HISTORY_LIMIT];
    uint8_t history_count, history_selected;
    uint32_t history_total, history_rows, history_last_ms, history_line_ms;
    bool history_error, history_busy, history_loading, history_past_header;
    bool history_line_has_comma, history_in_timestamp, history_timestamp_digits;
    uint8_t history_mode, history_first_row_len;
    char history_first_row[80];
    Storage* history_storage;
    File* history_file;
} LabMateApp;

static Storage storage;
static File handle;
static FS_Error sd_error, stat_error, scan_error;
static bool path_is_dir, alloc_fails, dir_open_fails, dir_close_fails, file_read_fails;
static unsigned allocations, frees, closes, records_opened, records_closed;
static const char* contents;
static size_t read_chunk;
static const char* entries[4];
static size_t entry_count, entry_index;

static void fixture(void) {
    memset(&handle, 0, sizeof(handle));
    sd_error = stat_error = FSE_OK;
    scan_error = FSE_NOT_EXIST;
    path_is_dir = true;
    alloc_fails = dir_open_fails = dir_close_fails = file_read_fails = false;
    allocations = frees = closes = records_opened = records_closed = 0U;
    entry_count = entry_index = 0U;
    contents = "elapsed_ms,source,pin,valid\n";
    read_chunk = 256U;
}
static Storage* furi_record_open(const char* record) {
    assert(!strcmp(record, RECORD_STORAGE)); ++records_opened; return &storage;
}
static void furi_record_close(const char* record) {
    assert(!strcmp(record, RECORD_STORAGE)); ++records_closed;
}
static FS_Error storage_sd_status(Storage* s) {assert(s == &storage); return sd_error;}
static FS_Error storage_common_stat(Storage* s, const char* path, FileInfo* info) {
    assert(s == &storage && !strcmp(path, "/ext/apps_data/labmate"));
    if(stat_error == FSE_OK) info->directory = path_is_dir;
    return stat_error;
}
static bool file_info_is_dir(const FileInfo* info) {return info->directory;}
static File* storage_file_alloc(Storage* s) {
    assert(s == &storage);
    if(alloc_fails) return NULL;
    ++allocations; return &handle;
}
static void storage_file_free(File* file) {
    assert(file == &handle && !file->open); ++frees;
}
static bool storage_dir_open(File* file, const char* path) {
    assert(file == &handle && !strcmp(path, "/ext/apps_data/labmate"));
    file->open = !dir_open_fails; return file->open;
}
static bool storage_dir_read(File* file, FileInfo* info, char* name, size_t cap) {
    assert(file == &handle && file->open);
    if(entry_index == entry_count) {file->error = scan_error; return false;}
    snprintf(name, cap, "%s", entries[entry_index++]);
    info->directory = false; return true;
}
static bool storage_dir_close(File* file) {
    assert(file == &handle); file->open = false; ++closes; return !dir_close_fails;
}
static FS_Error storage_file_get_error(File* file) {assert(file == &handle);return file->error;}
static bool storage_file_exists(Storage* s, const char* path) {(void)s;(void)path;return false;}
static FS_Error storage_common_remove(Storage* s, const char* path) {
    (void)s;(void)path; assert(!"read-only tests must not delete"); return FSE_INTERNAL;
}
static bool storage_file_open(File* file, const char* path, unsigned access, unsigned mode) {
    assert(file == &handle && access == FSAM_READ && mode == FSOM_OPEN_EXISTING);
    assert(!strcmp(path, "/ext/apps_data/labmate/log_0001.csv"));
    file->open = true; return true;
}
static bool storage_file_is_open(File* file) {assert(file == &handle);return file->open;}
static bool storage_file_close(File* file) {
    assert(file == &handle); file->open = false; ++closes; return true;
}
static size_t storage_file_read(File* file, void* bytes, size_t cap) {
    assert(file == &handle && file->open);
    if(file_read_fails) return 0U;
    size_t count = strlen(contents) - file->offset;
    if(count > cap) count = cap;
    if(count > read_chunk) count = read_chunk;
    memcpy(bytes, contents + file->offset, count);file->offset += count;return count;
}
static bool storage_file_eof(File* file) {
    assert(file == &handle); return !file_read_fails && file->offset == strlen(contents);
}
static void furi_mutex_acquire(void* mutex, unsigned wait) {(void)mutex;(void)wait;}
static void furi_mutex_release(void* mutex) {(void)mutex;}

/* Runner retains every production function body and changes only its
 * firmware-heavy app-state include to the typed fixture above. */
#include "history_production.inc"

static void assert_balanced(void) {
    assert(records_opened == records_closed && allocations == frees && !handle.open);
}
static void scan_expect(bool error) {
    LabMateApp app = {0};app.history_busy = true;
    labmate_history_scan(&app);
    assert(app.history_error == error && !app.history_busy);
    assert(app.history_count == 0U && app.history_total == 0U);
    assert_balanced();
}
static void test_scan(void) {
    fixture();stat_error = FSE_NOT_EXIST;scan_expect(false);assert(!allocations);
    fixture();scan_expect(false);
    fixture();sd_error = FSE_INTERNAL;scan_expect(true);assert(!allocations);
    fixture();stat_error = FSE_DENIED;scan_expect(true);assert(!allocations);
    fixture();path_is_dir = false;scan_expect(true);assert(!allocations);
    fixture();alloc_fails = true;scan_expect(true);
    fixture();dir_open_fails = true;scan_expect(true);assert(closes == 1U);
    fixture();scan_error = FSE_INTERNAL;scan_expect(true);
    fixture();dir_close_fails = true;scan_expect(true);
    fixture();entries[0] = "log_0007.csv";entries[1] = "other.txt";
    entries[2] = "log_0042.csv";entry_count = 3U;
    LabMateApp app = {0};labmate_history_scan(&app);
    assert(!app.history_error && app.history_total == 2U && app.history_count == 2U);
    assert(app.history_ids[0] == 42U && app.history_ids[1] == 7U);assert_balanced();
}
static LabMateApp parse(const char* input, size_t chunk, bool read_error) {
    fixture();contents = input;read_chunk = chunk;file_read_fails = read_error;
    LabMateApp app = {0};app.history_count = 1U;app.history_ids[0] = 1U;
    labmate_history_open(&app);
    assert(!app.history_error && app.history_loading && !app.history_timestamp_digits);
    unsigned steps = 0U;
    while(app.history_loading) {labmate_history_read_step(&app);assert(++steps < 2048U);}
    assert(!app.history_file && !app.history_storage);assert_balanced();return app;
}
static void test_timestamps(void) {
    const size_t chunks[] = {1U, 2U, 7U, 256U};
    const char* bad[] = {"4294967296", "4294967299", "99999999999", "", "12x", "+1", "-1", " 1"};
    for(size_t i = 0; i < sizeof(chunks) / sizeof(chunks[0]); ++i) {
        LabMateApp app = parse("elapsed_ms,source,pin,valid\n0,FREQ,PC1,1\n4294967295,FREQ,PC1,1\n", chunks[i], false);
        assert(!app.history_error && app.history_rows == 2U && app.history_last_ms == UINT32_MAX && app.history_mode == 1U);
        for(size_t j = 0; j < sizeof(bad) / sizeof(bad[0]); ++j) {
            char input[160];snprintf(input, sizeof(input), "elapsed_ms,source,pin,valid\n%s,FREQ,PC1,1\n", bad[j]);
            app = parse(input, chunks[i], false);
            assert(app.history_error && app.history_rows == 0U && app.history_last_ms == 0U);
        }
        app = parse("elapsed_ms,source,pin,valid\n1000,FREQ,PC1,1\n4294967299,FREQ,PC1,1\n", chunks[i], false);
        assert(app.history_error && app.history_rows == 1U && app.history_last_ms == 1000U);
        app = parse("elapsed_ms,source,pin,valid\n1000,FREQ,PC1,1", chunks[i], false);
        assert(app.history_error && app.history_rows == 0U);
        app = parse("elapsed_ms,source,pin,valid\n", chunks[i], false);
        assert(!app.history_error && app.history_rows == 0U);
    }
    LabMateApp app = parse("elapsed_ms,source,pin,valid\n", 256U, true);
    assert(app.history_error && !app.history_rows);
}
int main(void) {
    test_scan();test_timestamps();
    puts("History missing-directory/media/stat/open/read/close distinctions PASS (fake storage)");
    puts("History timestamp bounds/malformed/truncated/chunk-split rejection PASS (exact production source)");
    return 0;
}
