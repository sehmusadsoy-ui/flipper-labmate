#include "labmate_dashboard_screen.h"
#include "labmate_ui_primitives.h"
#include "labmate_scope_period_stats.h"
#include <stdio.h>
#include <stdint.h>

static const char* const labels[LabMateSnapshotSourceCount] = {
    "FREQ", "PULSE", "SCOPE", "COUNT", "LOGGER"
};
static void hz_text(uint32_t mhz, char* out, size_t cap) {
    const uint64_t tenhz = ((uint64_t)mhz + 50U) / 100U;
    if(tenhz > 999999U) (void)snprintf(out, cap, ">99kHz");
    else (void)snprintf(out, cap, "%lu.%luHz",
        (unsigned long)(tenhz / 10U), (unsigned long)(tenhz % 10U));
}
static void line(Canvas* c, uint8_t y, bool selected, const char* text) {
    /* x=3 and 6px glyphs: at most 20 visible chars fit 128px. */
    char buffer[21];
    (void)snprintf(buffer,sizeof(buffer),"%c%s",selected ? '>' : ' ',text);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 3, y, buffer);
}
void labmate_dashboard_screen_draw(Canvas* c, const LabMateApp* a) {
    if(!c || !a) return;
    const uint8_t selected=a->dashboard_source < LabMateSnapshotSourceCount ?
         a->dashboard_source : 0U;
    const uint8_t page=selected < 3U ? 0U : 1U;
    char buf[22], hz[16];
    ui_draw_header(c,!a->dashboard_details ? "DASHBOARD" :
                          a->dashboard_evidence ? "EVIDENCE" : "STATS");
    ui_badge(c,95,1,31,page ? "2/2" : "1/2",false);
    if(a->dashboard_details && a->dashboard_evidence) {
        const LabMateDashboardSlot* slot = &a->doctor_store.slots[selected];
        line(c,22,false,labels[selected]);
        if(!slot->has_snapshot) {
            line(c,33,false,"NO SOURCE DATA");
            line(c,50,false,"NOT MEASURED");
        } else {
            const LabMateSnapshotV1* s = &slot->latest;
            const char* quality = labmate_snapshot_v1_quality_text(s->quality);
            (void)snprintf(buf,sizeof(buf),"PIN %u %s",
                (unsigned)s->pin_index,quality);
            line(c,31,false,buf);
            if(labmate_snapshot_v1_can_display_measurement(s))
                (void)snprintf(buf,sizeof(buf),"GEN %lu SAMP %lu",
                    (unsigned long)s->capture_generation,
                    (unsigned long)s->valid_sample_count);
            else
                (void)snprintf(buf,sizeof(buf),"NO VALID SAMPLES");
            line(c,40,false,buf);
            /* No claim of calibrated wall time. The event interval is
             * from the SAME verified capture session.
             */
            const uint32_t duration=s->observation_end_ms-s->observation_start_ms;
            (void)snprintf(buf,sizeof(buf),"WINDOW %lums",(unsigned long)duration);
            line(c,50,false,buf);
        }
        ui_footer_pair(c,"<>","PAGE","OK","LIST");
        return;
    }
    if(a->dashboard_details) {
        LabMateSnapshotV1 snapshot;
        uint32_t mean,min,max; uint8_t count;
        if(labmate_dashboard_store_read_measurement(
                &a->doctor_store,selected,&snapshot) &&
           labmate_signal_stats_read(
                &a->signal_stats,selected,&mean,&min,&max,&count)) {
            hz_text(mean,hz,sizeof(hz));
            (void)snprintf(buf,sizeof(buf),"MEAN %s",hz);
            line(c,22,false,buf);
            hz_text(min,hz,sizeof(hz));
            (void)snprintf(buf,sizeof(buf),"MIN  %s",hz);
            line(c,31,false,buf);
            hz_text(max,hz,sizeof(hz));
            (void)snprintf(buf,sizeof(buf),"MAX  %s",hz);
            line(c,40,false,buf);
            (void)snprintf(buf,sizeof(buf),"%u SEALED SESSIONS",(unsigned)count);
            line(c,50,false,buf);
        } else if(selected==LabMateSnapshotScope &&
           labmate_dashboard_store_read_measurement(
               &a->doctor_store,selected,&snapshot) &&
           a->scope_last_valid &&
           a->scope_last_generation == snapshot.capture_generation &&
           a->scope_last_metrics.status == LabMateScopeMetricsReady &&
           !a->scope_last_metrics.truncated) {
            hz_text(snapshot.frequency_millihz,hz,sizeof(hz));
            (void)snprintf(buf,sizeof(buf),"FREQ %s",hz);
            line(c,22,false,buf);
            (void)snprintf(buf,sizeof(buf),"MIN %lu ticks",
                (unsigned long)a->scope_last_metrics.min_period_ticks);
            line(c,31,false,buf);
            (void)snprintf(buf,sizeof(buf),"MAX %lu ticks",
                (unsigned long)a->scope_last_metrics.max_period_ticks);
            line(c,40,false,buf);
            LabMateScopePeriodStats spread;
            if(labmate_scope_period_stats(&a->scope_last_metrics,&spread)) {
                (void)snprintf(buf,sizeof(buf),"SPREAD %lu.%lu%%",
                    (unsigned long)(spread.spread_permille / 10U),
                    (unsigned long)(spread.spread_permille % 10U));
                line(c,50,false,buf);
            } else line(c,50,false,"SPREAD N/A");
        } else if(labmate_dashboard_store_read_measurement(
                      &a->doctor_store,selected,&snapshot) &&
                  (selected==LabMateSnapshotCounter ||
                   selected==LabMateSnapshotLogger)) {
            (void)snprintf(buf,sizeof(buf),"%lu %s",
                (unsigned long)snapshot.valid_sample_count,
                selected==LabMateSnapshotLogger ? "CSV ROWS" : "TIM2 EDGES");
            line(c,22,false,buf);
            (void)snprintf(buf,sizeof(buf),"PIN %u", (unsigned)snapshot.pin_index);
            line(c,31,false,buf);
            const uint32_t elapsed_ms =
                snapshot.observation_end_ms - snapshot.observation_start_ms;
            (void)snprintf(buf,sizeof(buf),"WINDOW %lums",(unsigned long)elapsed_ms);
            line(c,40,false,buf);
            line(c,50,false,"HISTORICAL ONLY");
        } else {
            line(c,22,false,labels[selected]);
            line(c,34,false,"NO VERIFIED STATS");
            line(c,50,false,"SEALED ONLY");
        }
        ui_footer_pair(c,"<>","PAGE","OK","LIST");
        return;
    }
    const uint8_t first=page?3U:0U;
    const uint8_t end=page?LabMateSnapshotSourceCount:3U;
    for(uint8_t i=first;i<end;++i) {
        const LabMateDashboardSlot* slot=&a->doctor_store.slots[i];
        LabMateSnapshotV1 snap;
        const char* state="NO DATA";
        if(labmate_dashboard_store_read_measurement(&a->doctor_store,i,&snap)) {
            if(i<=LabMateSnapshotScope && snap.frequency_millihz) {
                hz_text(snap.frequency_millihz,hz,sizeof(hz));
                state=hz;
            } else if(i==LabMateSnapshotCounter || i==LabMateSnapshotLogger) {
                (void)snprintf(hz,sizeof(hz),
                              i==LabMateSnapshotLogger ? "%lu ROWS" : "%lu EVENTS",
                              (unsigned long)snap.valid_sample_count);
                state=hz;
            } else state="VALID";
        } else if(slot->has_snapshot) {
            state=labmate_snapshot_v1_quality_text(slot->latest.quality);
        }
        (void)snprintf(buf,sizeof(buf),"%s %s",labels[i],state);
        line(c,(uint8_t)(22U+9U*(i-first)),i==selected,buf);
    }
    line(c,50,false,"SEALED / NOT LIVE");
    ui_footer_pair(c,"^v","SOURCE","OK","STATS");
}
