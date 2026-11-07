#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef struct Storage Storage;
typedef struct File File;
typedef enum {FSE_OK, FSE_NOT_EXIST, FSE_EXIST, FSE_DENIED, FSE_INTERNAL} FS_Error;
typedef struct {bool directory; uint32_t size;} FileInfo;
typedef enum {FSAM_READ, FSAM_WRITE} FS_AccessMode;
typedef enum {FSOM_OPEN_EXISTING, FSOM_CREATE_ALWAYS, FSOM_CREATE_NEW} FS_OpenMode;
FS_Error storage_sd_status(Storage* storage);
FS_Error storage_common_stat(Storage* storage, const char* path, FileInfo* info);
bool file_info_is_dir(const FileInfo* info);
bool storage_file_exists(Storage* storage, const char* path);
bool storage_dir_exists(Storage* storage, const char* path);
bool storage_simply_mkdir(Storage* storage, const char* path);
File* storage_file_alloc(Storage* storage);
void storage_file_free(File* file);
bool storage_file_open(File* file, const char* path, FS_AccessMode access, FS_OpenMode mode);
bool storage_file_close(File* file);
bool storage_file_is_open(File* file);
size_t storage_file_size(File* file);
size_t storage_file_read(File* file, void* bytes, size_t size);
size_t storage_file_write(File* file, const void* bytes, size_t size);
bool storage_file_sync(File* file);
FS_Error storage_file_get_error(File* file);
bool storage_dir_open(File* file, const char* path);
bool storage_dir_read(File* file, FileInfo* info, char* name, size_t capacity);
bool storage_dir_close(File* file);
