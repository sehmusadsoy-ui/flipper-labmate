#pragma once
#include "labmate_internal.h"
#include <stddef.h>
/* Called under UI mutex; never performs storage I/O. */
bool logger_prepare_row(LabMateApp* app, char* row, size_t capacity);
