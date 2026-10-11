#pragma once

/* CSV Log History: bounded read-only browser plus explicitly confirmed
 * single-log removal. Keep all SD I/O outside the UI mutex. */
#include "labmate_internal.h"

void labmate_history_scan(LabMateApp* app);
void labmate_history_open(LabMateApp* app);
void labmate_history_read_step(LabMateApp* app);
void labmate_history_close(LabMateApp* app);
/* Delete exactly one numeric log_XXXX.csv from LabMate's log directory.
 * Caller ensures no logger/history file is open. Returns false on SD error. */
bool labmate_history_delete_file(uint16_t log_id);
