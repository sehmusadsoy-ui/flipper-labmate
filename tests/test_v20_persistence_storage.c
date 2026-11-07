/* Production-linked profiles/preferences/logger/deferred I/O over memory VFS.
 * Every persisted byte belongs to this process. No host files, USB or real SD. */
#include "persistence_app.h"
#include "labmate_logger_codec.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DIR "/ext/apps_data/labmate"
#define MAX_FILES 24U
#define MAX_BYTES 4096U
typedef struct {char path[120];uint8_t bytes[MAX_BYTES],durable[MAX_BYTES];size_t size,durable_size;bool exists;} Node;
struct Storage {int unused;};
struct File {Node* node;size_t offset,dir_index;bool open,attempted,directory;FS_Error error;FS_AccessMode access;};
static struct Storage storage;
static Node nodes[MAX_FILES];
static bool directory_exists, directory_is_file;
static unsigned refs,handles,writes,syncs,closes;
static FS_Error sd_error,stat_fault;
static const char* stat_fault_path;
static bool fail_mkdir,fail_alloc,fail_open_write,fail_open_read,fail_sync,fail_close,corrupt_read,create_race;
static unsigned fail_close_on;
static size_t short_write,short_read;
static uint32_t tick=100U;

static Node* find(const char* path) {
    for(size_t i=0;i<MAX_FILES;++i)if(nodes[i].exists&&!strcmp(nodes[i].path,path))return &nodes[i];
    return NULL;
}
static Node* create(const char* path) {
    Node* n=find(path);if(n)return n;
    for(size_t i=0;i<MAX_FILES;++i)if(!nodes[i].exists){n=&nodes[i];memset(n,0,sizeof(*n));snprintf(n->path,sizeof(n->path),"%s",path);n->exists=true;return n;}
    assert(!"VFS full");return NULL;
}
static void clear_faults(void) {
    sd_error=stat_fault=FSE_OK;stat_fault_path=NULL;
    fail_mkdir=fail_alloc=fail_open_write=fail_open_read=fail_sync=fail_close=corrupt_read=false;
    create_race=false;fail_close_on=0U;
    short_write=short_read=SIZE_MAX;
}
static void reset(void) {
    assert(!refs&&!handles);memset(nodes,0,sizeof(nodes));directory_exists=directory_is_file=false;
    writes=syncs=closes=0;clear_faults();
}
static void balanced(void){assert(!refs&&!handles);}
static void power_cycle(void) {
    balanced();for(size_t i=0;i<MAX_FILES;++i)if(nodes[i].exists){nodes[i].size=nodes[i].durable_size;memcpy(nodes[i].bytes,nodes[i].durable,nodes[i].size);}
}
void* furi_record_open(const char* name){assert(!strcmp(name,RECORD_STORAGE));++refs;return &storage;}
void furi_record_close(const char* name){assert(!strcmp(name,RECORD_STORAGE)&&refs);--refs;}
void furi_mutex_acquire(void* m,uint32_t timeout){(void)m;(void)timeout;}
void furi_mutex_release(void* m){(void)m;}
uint32_t furi_get_tick(void){return tick;}
uint32_t furi_kernel_get_tick_frequency(void){return 1000U;}
FS_Error storage_sd_status(Storage* s){assert(s==&storage);return sd_error;}
FS_Error storage_common_stat(Storage* s,const char* path,FileInfo* info){
    assert(s==&storage);
    if(stat_fault!=FSE_OK&&(!stat_fault_path||!strcmp(path,stat_fault_path)))return stat_fault;
    if(!strcmp(path,DIR)){
        if(!directory_exists)return FSE_NOT_EXIST;
        if(info){info->directory=!directory_is_file;info->size=0U;}return FSE_OK;
    }
    Node* n=find(path);if(!n)return FSE_NOT_EXIST;
    if(info){info->directory=false;info->size=(uint32_t)n->size;}return FSE_OK;
}
bool file_info_is_dir(const FileInfo* info){return info->directory;}
bool storage_file_exists(Storage* s,const char* path){FileInfo i;return storage_common_stat(s,path,&i)==FSE_OK&&!i.directory;}
bool storage_dir_exists(Storage* s,const char* path){FileInfo i;return storage_common_stat(s,path,&i)==FSE_OK&&i.directory;}
bool storage_simply_mkdir(Storage* s,const char* path){assert(s==&storage&&!strcmp(path,DIR));if(fail_mkdir||directory_is_file)return false;directory_exists=true;return true;}
File* storage_file_alloc(Storage* s){assert(s==&storage);if(fail_alloc)return NULL;File* f=calloc(1,sizeof(*f));assert(f);++handles;return f;}
void storage_file_free(File* f){assert(f&&!f->open&&!f->attempted&&handles);--handles;free(f);}
bool storage_file_open(File* f,const char* path,FS_AccessMode access,FS_OpenMode mode){
    assert(!f->open&&!f->attempted);f->attempted=true;f->error=FSE_OK;f->access=access;f->offset=0;
    if((access==FSAM_WRITE&&fail_open_write)||(access==FSAM_READ&&fail_open_read)){f->error=FSE_DENIED;return false;}
    Node* n=find(path);
    if(mode==FSOM_CREATE_NEW&&!n&&create_race){
        create_race=false;n=create(path);memcpy(n->bytes,"FOREIGN",7U);n->size=7U;
        memcpy(n->durable,n->bytes,7U);n->durable_size=7U;
        f->error=FSE_EXIST;return false;
    }
    if(mode==FSOM_CREATE_NEW&&n){f->error=FSE_EXIST;return false;}
    if(mode==FSOM_OPEN_EXISTING&&!n){f->error=FSE_NOT_EXIST;return false;}
    if(!n)n=create(path);
    if(mode==FSOM_CREATE_ALWAYS)n->size=0U;
    f->node=n;f->open=true;return true;
}
static void flush(Node* n){memcpy(n->durable,n->bytes,n->size);n->durable_size=n->size;}
bool storage_file_close(File* f){
    assert(f);++closes;if(!f->attempted)return false;
    bool ok=!fail_close&&closes!=fail_close_on;if(fail_close)fail_close=false;
    if(ok&&f->open&&f->access==FSAM_WRITE)flush(f->node);
    f->open=f->attempted=false;return ok;
}
bool storage_file_is_open(File* f){return f->open;}
size_t storage_file_size(File* f){assert(f->open);return f->node->size;}
size_t storage_file_read(File* f,void* bytes,size_t size){
    assert(f->open&&f->access==FSAM_READ);size_t n=f->node->size-f->offset;if(n>size)n=size;
    if(n>short_read){n=short_read;short_read=SIZE_MAX;}
    memcpy(bytes,f->node->bytes+f->offset,n);f->offset+=n;
    if(corrupt_read&&n){((uint8_t*)bytes)[0]^=1U;corrupt_read=false;}return n;
}
size_t storage_file_write(File* f,const void* bytes,size_t size){
    assert(f->open&&f->access==FSAM_WRITE);++writes;size_t n=size;
    if(n>short_write){n=short_write;short_write=SIZE_MAX;}
    assert(f->offset+n<=MAX_BYTES);memcpy(f->node->bytes+f->offset,bytes,n);f->offset+=n;if(f->node->size<f->offset)f->node->size=f->offset;return n;
}
bool storage_file_sync(File* f){assert(f->open);++syncs;if(fail_sync){fail_sync=false;return false;}flush(f->node);return true;}
FS_Error storage_file_get_error(File* f){return f->error;}
bool storage_dir_open(File* f,const char* path){assert(!f->attempted&&!strcmp(path,DIR));f->attempted=true;f->open=directory_exists&&!directory_is_file;f->directory=true;f->dir_index=0;return f->open;}
bool storage_dir_read(File* f,FileInfo* info,char* name,size_t capacity){
    assert(f->open&&f->directory);while(f->dir_index<MAX_FILES){Node* n=&nodes[f->dir_index++];if(n->exists){const char* base=strrchr(n->path,'/');snprintf(name,capacity,"%s",base?base+1:n->path);info->directory=false;return true;}}
    f->error=FSE_NOT_EXIST;return false;
}
bool storage_dir_close(File* f){return storage_file_close(f);}
void view_port_update(ViewPort* viewport){(void)viewport;}
bool labmate_frequency_low_lease_pending(void){return false;}
bool labmate_frequency_tim2_lease_pending(void){return false;}
bool labmate_pulse_lease_pending(void){return false;}
bool logger_prepare_row(LabMateApp* app,char* row,size_t capacity){(void)app;(void)row;(void)capacity;return false;}
bool labmate_uart_send(LabMateUart* uart,const uint8_t* bytes,size_t size){(void)uart;(void)bytes;(void)size;assert(!"unrelated UART path");return false;}
void labmate_history_close(LabMateApp* app){(void)app;assert(!"unrelated History path");}
void labmate_history_scan(LabMateApp* app){(void)app;assert(!"unrelated History path");}
void labmate_history_open(LabMateApp* app){(void)app;assert(!"unrelated History path");}
void labmate_history_read_step(LabMateApp* app){(void)app;assert(!"unrelated History path");}
bool labmate_history_delete_file(uint16_t id){(void)id;assert(!"unrelated delete path");return false;}

static LabMateProfileStore profile(uint32_t generation,uint8_t preset){
    LabMateProfileStore p;labmate_profile_store_init(&p);p.generation=generation;
    p.slots[0]=(LabMateProfile){true,4U,1U,preset,0U};return p;
}
static LabMateUiPreferences prefs(uint32_t generation,bool motion){LabMateUiPreferences p;labmate_ui_prefs_defaults(&p);p.generation=generation;p.animations=motion;return p;}
static void test_metadata(void){
    reset();LabMateProfileStore p;LabMateUiPreferences u;uint8_t a=99;
    assert(labmate_profile_sd_load(&p,&a)==LabMateProfileIoEmpty&&a==255U);
    assert(labmate_ui_prefs_sd_load(&u,&a)==LabMateUiPrefsIoEmpty&&a==255U);
    stat_fault=FSE_DENIED;
    assert(labmate_profile_sd_load(&p,&a)==LabMateProfileIoError);
    assert(labmate_ui_prefs_sd_load(&u,&a)==LabMateUiPrefsIoError);
    clear_faults();directory_exists=directory_is_file=true;
    assert(labmate_profile_sd_load(&p,&a)==LabMateProfileIoError);
    assert(labmate_ui_prefs_sd_load(&u,&a)==LabMateUiPrefsIoError);balanced();
    clear_faults();directory_is_file=false;
    stat_fault=FSE_DENIED;stat_fault_path=DIR "/profiles_a.bin";
    assert(labmate_profile_sd_load(&p,&a)==LabMateProfileIoError&&a==255U);
    stat_fault_path=DIR "/ui_prefs_a.bin";
    assert(labmate_ui_prefs_sd_load(&u,&a)==LabMateUiPrefsIoError&&a==255U);balanced();
}
static void test_records(void){
    reset();uint8_t active=255U,out=77U;LabMateProfileStore p=profile(1U,0U),loaded;
    assert(labmate_profile_sd_save(&p,active,&out)&&out==0U);active=out;balanced();
    uint8_t first[32];memcpy(first,find(DIR "/profiles_a.bin")->bytes,32U);
    p=profile(2U,4U);assert(labmate_profile_sd_save(&p,active,&out)&&out==1U);
    assert(!memcmp(first,find(DIR "/profiles_a.bin")->bytes,32U));power_cycle();
    assert(labmate_profile_sd_load(&loaded,&active)==LabMateProfileIoOk&&active==1U&&loaded.generation==2U&&loaded.slots[0].generator_index==4U);
    stat_fault=FSE_DENIED;stat_fault_path=DIR "/profiles_b.bin";
    assert(labmate_profile_sd_load(&loaded,&active)==LabMateProfileIoOk&&active==0U&&loaded.generation==1U);clear_faults();
    find(DIR "/profiles_b.bin")->size=7U;
    assert(labmate_profile_sd_load(&loaded,&active)==LabMateProfileIoOk&&active==0U&&loaded.generation==1U);
    find(DIR "/profiles_a.bin")->bytes[3]^=1U;
    assert(labmate_profile_sd_load(&loaded,&active)==LabMateProfileIoCorrupt&&active==255U);
    balanced();reset();LabMateUiPreferences u=prefs(1U,true),ul;
    assert(labmate_ui_prefs_sd_save(&u,255U,&out)&&out==0U);uint8_t old[16];memcpy(old,find(DIR "/ui_prefs_a.bin")->bytes,16U);
    u=prefs(2U,false);assert(labmate_ui_prefs_sd_save(&u,0U,&out)&&out==1U);
    assert(!memcmp(old,find(DIR "/ui_prefs_a.bin")->bytes,16U));power_cycle();
    assert(labmate_ui_prefs_sd_load(&ul,&active)==LabMateUiPrefsIoOk&&active==1U&&!ul.animations&&ul.generation==2U);
    find(DIR "/ui_prefs_b.bin")->bytes[0]^=1U;
    assert(labmate_ui_prefs_sd_load(&ul,&active)==LabMateUiPrefsIoOk&&active==0U&&ul.animations);
    find(DIR "/ui_prefs_a.bin")->size=3U;
    assert(labmate_ui_prefs_sd_load(&ul,&active)==LabMateUiPrefsIoCorrupt&&active==255U);balanced();
}
static void fault(unsigned which){
    switch(which){case 0:fail_alloc=true;break;case 1:fail_open_write=true;break;case 2:short_write=5U;break;case 3:fail_sync=true;break;case 4:fail_close=true;break;case 5:fail_open_read=true;break;case 6:short_read=3U;break;case 7:corrupt_read=true;break;case 8:fail_mkdir=true;break;case 9:fail_close_on=closes+2U;break;default:assert(false);}
}
static void test_record_failures(void){
    for(unsigned kind=0;kind<2;++kind)for(unsigned f=0;f<10;++f){
        reset();uint8_t out=55U;LabMateProfileStore p=profile(1U,0U);LabMateUiPreferences u=prefs(1U,true);
        if(!kind)assert(labmate_profile_sd_save(&p,255U,&out));else assert(labmate_ui_prefs_sd_save(&u,255U,&out));
        const char* path=kind?DIR "/ui_prefs_a.bin":DIR "/profiles_a.bin";Node snapshot=*find(path);
        p=profile(2U,4U);u=prefs(2U,false);out=55U;fault(f);
        if(!kind)assert(!labmate_profile_sd_save(&p,0U,&out));else assert(!labmate_ui_prefs_sd_save(&u,0U,&out));
        assert(out==55U&&!memcmp(snapshot.bytes,find(path)->bytes,snapshot.size));balanced();clear_faults();
        /* Failed saves never destroy the previous active copy. A retry can recover. */
        if(!kind)assert(labmate_profile_sd_save(&p,0U,&out)&&out==1U);else assert(labmate_ui_prefs_sd_save(&u,0U,&out)&&out==1U);
        power_cycle();uint8_t active;LabMateProfileStore pl;LabMateUiPreferences ul;
        if(!kind)assert(labmate_profile_sd_load(&pl,&active)==LabMateProfileIoOk&&active==1U&&pl.generation==2U);
        else assert(labmate_ui_prefs_sd_load(&ul,&active)==LabMateUiPrefsIoOk&&active==1U&&ul.generation==2U);
        balanced();
    }
}
static LabMateApp app(void){LabMateApp a={0};a.screen=LabMateScreenLogger;a.capture_owner=LabMateCaptureFrequencyLow;a.gpio_index=a.capture_pin_index=1U;a.frequency_irq_active=true;return a;}
static void row(LabMateApp* a){LabMateDeferredWork w={0};w.pending_log=true;snprintf(w.pending_log_row,sizeof(w.pending_log_row),"1000,FREQ,PC1,0,0.000,,,,\n");labmate_deferred_execute(a,&w,NULL);}
static void test_csv(void){
    reset();LabMateApp a=app();assert(labmate_logger_storage_start(&a));assert(!strcmp(a.logger_path,DIR "/log_0001.csv"));
    for(unsigned i=0;i<9;++i)row(&a);
    assert(a.logger_rows==9U&&!syncs);
    row(&a);assert(a.logger_rows==10U&&syncs==1U);labmate_logger_storage_stop(&a);assert(!a.logger_error&&!a.logger_file&&!a.logger_storage);balanced();
    Node saved=*find(DIR "/log_0001.csv");power_cycle();assert(saved.size==find(saved.path)->size&&!memcmp(saved.bytes,find(saved.path)->bytes,saved.size));
    LabMateApp reopened=app();assert(labmate_logger_storage_start(&reopened));assert(!strcmp(reopened.logger_path,DIR "/log_0002.csv"));
    assert(!memcmp(saved.bytes,find(saved.path)->bytes,saved.size));row(&reopened);labmate_logger_storage_stop(&reopened);balanced();
    for(unsigned f=0;f<5;++f){
        reset();a=app();assert(labmate_logger_storage_start(&a));
        if(f==0)short_write=2U;else if(f==1){a.logger_rows=9U;fail_sync=true;}else if(f==2)fail_close=true;else if(f==3)fail_sync=true;
        if(f<2)row(&a);else if(f<4)labmate_logger_storage_stop(&a);else{row(&a);labmate_logger_storage_stop(&a);}
        assert(!a.logger_recording&&!a.logger_file&&!a.logger_storage);
        assert(a.logger_error==(f<4));balanced();clear_faults();
        assert(labmate_logger_storage_start(&a));assert(!a.logger_error);labmate_logger_storage_stop(&a);balanced();
    }
    reset();a=app();short_write=4U;assert(!labmate_logger_storage_start(&a)&&a.logger_error);balanced();
    reset();a=app();a.capture_owner=LabMateCaptureNone;assert(!labmate_logger_storage_start(&a)&&!writes);balanced();
    reset();a=app();create_race=true;
    assert(labmate_logger_storage_start(&a)&&!strcmp(a.logger_path,DIR "/log_0002.csv"));
    assert(find(DIR "/log_0001.csv")->size==7U&&!memcmp(find(DIR "/log_0001.csv")->bytes,"FOREIGN",7U));
    labmate_logger_storage_stop(&a);balanced();
    reset();a=app();create_race=true;fail_close_on=2U;
    assert(!labmate_logger_storage_start(&a)&&a.logger_error);balanced();
    assert(find(DIR "/log_0001.csv")->size==7U);clear_faults();
    assert(labmate_logger_storage_start(&a));labmate_logger_storage_stop(&a);balanced();
    reset();directory_exists=true;Node* final=create(DIR "/log_9999.csv");memcpy(final->bytes,"old",3U);final->size=3U;
    a=app();assert(!labmate_logger_storage_start(&a)&&a.logger_error&&final->size==3U&&!memcmp(final->bytes,"old",3U));balanced();
}
static void test_generation_wrap(void){
    reset();uint8_t out,active;LabMateProfileStore p=profile(UINT32_MAX,0U),pl;
    assert(labmate_profile_sd_save(&p,255U,&out));p.generation=0U;assert(labmate_profile_sd_save(&p,0U,&out));
    assert(labmate_profile_sd_load(&pl,&active)==LabMateProfileIoOk&&active==1U&&pl.generation==0U);
    LabMateUiPreferences u=prefs(UINT32_MAX,true),ul;assert(labmate_ui_prefs_sd_save(&u,255U,&out));u.generation=0U;assert(labmate_ui_prefs_sd_save(&u,0U,&out));
    assert(labmate_ui_prefs_sd_load(&ul,&active)==LabMateUiPrefsIoOk&&active==1U&&ul.generation==0U);balanced();
}
static void test_deferred_records(void){
    reset();LabMateApp first={0},reopened={0};LabMateDeferredWork work={0};
    work.profiles_save_requested=true;work.proposed_profiles=profile(10U,0U);work.proposed_copy=255U;
    labmate_deferred_execute(&first,&work,NULL);
    assert(first.profile_io==LabMateProfileIoOk&&first.profile_active_copy==0U&&first.profile_notice==1U&&!first.profile_busy);balanced();power_cycle();
    memset(&work,0,sizeof(work));work.profiles_read_requested=true;
    labmate_deferred_execute(&reopened,&work,NULL);
    assert(reopened.profiles.generation==10U&&reopened.profile_active_copy==0U&&reopened.profile_io==LabMateProfileIoOk);
    memset(&work,0,sizeof(work));work.profiles_save_requested=true;work.proposed_profiles=profile(11U,4U);work.proposed_copy=0U;short_write=5U;
    labmate_deferred_execute(&reopened,&work,NULL);
    assert(reopened.profiles.generation==10U&&reopened.profile_active_copy==0U&&reopened.profile_notice==5U&&!reopened.profile_busy);balanced();clear_faults();
    memset(&work,0,sizeof(work));work.ui_prefs_save_requested=true;work.proposed_ui_prefs=prefs(7U,true);work.proposed_ui_prefs_copy=255U;
    labmate_deferred_execute(&first,&work,NULL);
    assert(first.ui_prefs_io==LabMateUiPrefsIoOk&&first.ui_prefs_active_copy==0U&&first.ui_prefs_notice==1U&&first.settings_toast_active);balanced();power_cycle();
    assert(labmate_ui_prefs_sd_load(&reopened.ui_prefs,&reopened.ui_prefs_active_copy)==LabMateUiPrefsIoOk&&reopened.ui_prefs.generation==7U);
    reopened.ui_prefs.animations=false;work.proposed_ui_prefs=prefs(8U,false);work.proposed_ui_prefs_copy=0U;fail_open_write=true;
    labmate_deferred_execute(&reopened,&work,NULL);
    assert(reopened.ui_prefs_io==LabMateUiPrefsIoError&&reopened.ui_prefs_active_copy==0U&&reopened.ui_prefs_notice==2U&&!reopened.ui_prefs.animations&&!reopened.settings_toast_active&&!reopened.ui_prefs_busy);balanced();
}
int main(void){test_metadata();test_records();test_record_failures();test_generation_wrap();test_deferred_records();test_csv();balanced();puts("Production profiles/UI prefs A/B persistence, fallback, wrap, deferred app/reopen and fault recovery PASS (memory VFS)");puts("Production CSV create/no-overwrite/deferred rows/10-row sync/close/reopen/fault recovery PASS (memory VFS)");return 0;}
