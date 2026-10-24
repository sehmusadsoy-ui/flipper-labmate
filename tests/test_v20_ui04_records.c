#include "test_v20_ui04_harness.h"
#include "ui_format_key.inc"
#include "ui_footer_info.inc"
#include "records_profiles_body.inc"
#include "records_history_body.inc"
#include "records_history_detail_body.inc"
static bool has(Canvas* c,const char* t){
    for(unsigned i=0;i<c->count;i++)if(!strcmp(c->labels[i],t))return true;
    return false;
}
static unsigned profile_cases(void) {
    unsigned cases=0;
    for(unsigned selected=0;selected<3;selected++)
    for(unsigned action=0;action<3;action++)
    for(unsigned present=0;present<2;present++)
    for(unsigned scenario=0;scenario<12;scenario++){
        LabMateApp a={0};Canvas c={0};
        a.profile_selected=(uint8_t)selected;
        a.profile_action=(uint8_t)action;
        a.profile_io=LabMateProfileIoOk;
        a.profiles.slots[selected].present=present!=0;
        for(unsigned slot=0;slot<3;slot++){
            a.profiles.slots[slot].generator_index=(uint8_t)(14-slot*7);
            a.profiles.slots[slot].frequency_pin=(slot&1)?4:1;
        }
        if(scenario==1)a.profile_busy=true;
        if(scenario==2)a.profile_io=LabMateProfileIoCorrupt;
        if(scenario==3)a.profile_io=LabMateProfileIoError;
        if(scenario==4)a.generator_running=true;
        if(scenario==5)a.capture_owner=LabMateCaptureBusy;
        if(scenario==6)a.logger_recording=true;
        if(scenario==7)a.profile_notice=6;
        if(scenario==8)a.profile_notice=7;
        if(scenario==9)a.profile_notice=2;
        if(scenario==10)a.profile_confirm=true;
        if(scenario==11){a.profile_confirm=true;a.profile_busy=true;}
        const LabMateApp before=a;
        draw_profiles(&c,&a);
        assert(!memcmp(&a,&before,sizeof(a)));
        if(c.faults){
            fprintf(stderr,"PROFILES selected=%u action=%u present=%u scenario=%u faults=%u\n",
                    selected,action,present,scenario,c.faults);
            return cases+1U;
        }
        if(scenario==10){assert(has(&c,"(BACK) NO"));
            if(action==2)assert(has(&c,"CANNOT UNDO"));}
        ++cases;
    }
    return cases;
}
static unsigned history_cases(void){
    unsigned cases=0;
    const uint8_t counts[]={0,1,3,32};
    for(unsigned ci=0;ci<4;ci++)for(unsigned scen=0;scen<11;scen++){
        LabMateApp a={0};Canvas c={0};
        a.history_count=counts[ci];
        a.history_selected=a.history_count?(uint8_t)(a.history_count-1):0;
        for(unsigned i=0;i<32;i++) a.history_ids[i]=(uint16_t)(i==31?65535:50+i);
        if(scen==1)a.history_busy=true;
        if(scen==2)a.history_error=true;
        if(scen==3)a.history_delete_mode=true;
        if(scen==4)a.history_delete_notice=1;
        if(scen==5)a.history_delete_notice=2;
        if(scen==6){a.history_delete_confirm=true;a.history_delete_mode=true;}
        if(scen==7){a.history_busy=true;a.history_delete_mode=true;}
        if(scen==8&&a.history_count)a.history_selected=0;
        if(scen==9&&a.history_count)a.history_selected=a.history_count/2;
        if(scen==10){a.history_delete_confirm=true;a.history_busy=true;}
        const LabMateApp before=a;
        draw_history(&c,&a);
        assert(!memcmp(&a,&before,sizeof(a)));
        if(c.faults){
            fprintf(stderr,"HISTORY count=%u scenario=%u faults=%u\n",counts[ci],scen,c.faults);
            return cases+1U;
        }
        if(scen==6&&a.history_count){assert(has(&c,"CANNOT UNDO"));assert(has(&c,"(BACK) NO"));}
        ++cases;
    }
    return cases;
}
static unsigned detail_cases(void){
    unsigned cases=0;
    for(unsigned selectedValid=0;selectedValid<2;selectedValid++)
    for(unsigned state=0;state<5;state++)
    for(unsigned mode=0;mode<4;mode++){
        LabMateApp a={0};Canvas c={0};
        a.history_count=selectedValid?1:0;
        a.history_ids[0]=65535;
        a.history_mode=(uint8_t)mode;
        a.history_rows=(state&1)?UINT32_MAX:0;
        a.history_last_ms=(state&1)?UINT32_MAX:0;
        if(state==1)a.history_loading=true;
        if(state==2)a.history_busy=true;
        if(state==3)a.history_error=true;
        if(state==4){a.history_busy=true;a.history_error=true;}
        const LabMateApp before=a;
        draw_history_detail(&c,&a);
        assert(!memcmp(&a,&before,sizeof(a)));
        assert(c.boxes==1U && c.color==ColorBlack);
        if(c.faults){
            fprintf(stderr,"DETAIL file=%u state=%u mode=%u faults=%u\n",selectedValid,state,mode,c.faults);
            return cases+1;
        }
        assert(has(&c,"(BACK)LIST") && has(&c,"READ ONLY"));
        ++cases;
    }
    return cases;
}
int main(void){
    const unsigned profiles=profile_cases();
    const unsigned history=history_cases();
    const unsigned detail=detail_cases();
    printf("UI-04 HOST PASS: profiles=%u history=%u detail=%u\n",profiles,history,detail);
    return 0;
}
