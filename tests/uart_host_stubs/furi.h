#pragma once
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>

#define RECORD_EXPANSION "expansion"
typedef struct FuriStreamBuffer FuriStreamBuffer;

FuriStreamBuffer* furi_stream_buffer_alloc(size_t capacity, size_t trigger_level);
void furi_stream_buffer_free(FuriStreamBuffer* stream);
size_t furi_stream_buffer_send(
    FuriStreamBuffer* stream, const void* data, size_t size, uint32_t timeout);
size_t furi_stream_buffer_receive(
    FuriStreamBuffer* stream, void* output, size_t size, uint32_t timeout);

void* furi_record_open(const char* name);
void furi_record_close(const char* name);
