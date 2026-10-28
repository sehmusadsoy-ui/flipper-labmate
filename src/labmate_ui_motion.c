#include "labmate_ui_motion.h"
#include "labmate_info_ui.h"
#include "ui_kit.h"

void labmate_ui_motion_init(LabMateApp* app) {
    if(!app) return;
    app->ui_splash = app->ui_prefs.startup_animation;
    app->ui_splash_tick = furi_get_tick();
    app->ui_frame_tick = app->ui_splash_tick;
    app->ui_trace_tick = app->ui_splash_tick;
    app->ui_frame = UI_KIT_TWEEN_FRAMES;
}

static void start(LabMateApp* app) {
    app->ui_frame = 0U;
    app->ui_frame_tick = furi_get_tick();
}

void labmate_ui_motion_carousel(LabMateApp* app, uint8_t old_index, int8_t direction) {
    if(!app) return;
    if(!app->ui_prefs.animations) {
        app->ui_carousel_motion = false;
        app->ui_list_motion = false;
        return;
    }
    app->ui_from = old_index;
    app->ui_direction = direction;
    app->ui_carousel_motion = true;
    app->ui_list_motion = false;
    start(app);
}

void labmate_ui_motion_list(LabMateApp* app, uint8_t old_index) {
    if(!app) return;
    if(!app->ui_prefs.animations) {
        app->ui_carousel_motion = false;
        app->ui_list_motion = false;
        return;
    }
    app->ui_list_previous = old_index;
    app->ui_list_motion = true;
    app->ui_carousel_motion = false;
    start(app);
}

void labmate_ui_motion_info_cancel(LabMateApp* app) {
    if(!app) return;
    app->info_page_motion = false;
    app->info_scroll_motion = false;
    app->info_section_motion = false;
    app->info_motion_frame = UI_KIT_TWEEN_FRAMES;
    app->info_scroll_render_px = (int16_t)app->info_guide_scroll_steps * 12;
}

void labmate_ui_motion_info_page(LabMateApp* app, uint8_t old_guide, int8_t direction) {
    if(!app) return;
    if(!app->ui_prefs.animations) {
        labmate_ui_motion_info_cancel(app);
        return;
    }
    app->info_previous_guide = old_guide;
    app->info_previous_scroll_px = app->info_scroll_render_px;
    app->info_page_direction = direction < 0 ? -1 : 1;
    app->info_page_motion = true;
    app->info_scroll_motion = false;
    app->info_section_motion = false;
    app->info_scroll_render_px = 0;
    app->info_motion_frame = 0U;
    app->ui_frame_tick = furi_get_tick();
}

void labmate_ui_motion_info_scroll(LabMateApp* app) {
    if(!app) return;
    if(!app->ui_prefs.animations) {
        labmate_ui_motion_info_cancel(app);
        return;
    }
    app->info_scroll_from_px = app->info_scroll_render_px;
    app->info_scroll_motion = true;
    app->info_page_motion = false;
    app->info_section_motion = false;
    app->info_motion_frame = 0U;
    app->ui_frame_tick = furi_get_tick();
}

void labmate_ui_motion_info_section(LabMateApp* app, uint8_t old_section, int8_t direction) {
    if(!app) return;
    if(!app->ui_prefs.animations) {
        labmate_ui_motion_info_cancel(app);
        return;
    }
    app->info_previous_section = old_section;
    app->info_previous_home_selected = app->info_selected;
    app->info_previous_guide = app->info_guide_selected;
    app->info_previous_scroll_px = app->info_scroll_render_px;
    /* An immediately-following scroll press on a freshly opened card must
     * begin at its real first row, even if the prior card was scrolled. */
    if(app->info_section == LabMateInfoGuideCard &&
       old_section != LabMateInfoGuideCard)
        app->info_scroll_render_px = 0;
    app->info_page_direction = direction < 0 ? -1 : 1;
    app->info_page_motion = false;
    app->info_scroll_motion = false;
    app->info_section_motion = true;
    app->info_motion_frame = 0U;
    app->ui_frame_tick = furi_get_tick();
}

bool labmate_ui_motion_is_active(const LabMateApp* app) {
    return app && (app->ui_splash || app->ui_carousel_motion || app->ui_list_motion ||
                   (app->screen == LabMateScreenSettings &&
                    (app->settings_selection_motion || app->settings_toggle_motion ||
                     app->settings_toast_active)) ||
                   (app->screen == LabMateScreenAbout &&
                    (app->info_page_motion || app->info_scroll_motion ||
                     app->info_section_motion)));
}

void labmate_ui_motion_step(LabMateApp* app) {
    if(!app) return;
    const uint32_t now = furi_get_tick();
    const uint32_t tps = furi_kernel_get_tick_frequency();
    const uint32_t frame_ticks = (tps * UI_KIT_FRAME_MS + 999U) / 1000U;
    const uint32_t interval = frame_ticks ? frame_ticks : 1U;

    if(app->ui_splash && (uint32_t)(now - app->ui_splash_tick) >= (tps * 12U / 10U)) {
        app->ui_splash = false;
    }
    if(app->settings_toast_active &&
       (uint32_t)(now - app->settings_toast_tick) >= (tps * 12U + 9U) / 10U) {
        app->settings_toast_active = false;
        if(app->ui_prefs_notice == 1U) app->ui_prefs_notice = 0U;
    }
    if((uint32_t)(now - app->ui_frame_tick) >= interval) {
        app->ui_frame_tick = now;
        if(app->screen == LabMateScreenSettings) {
            if(app->settings_selection_motion) {
                if(app->settings_anim_frame < UI_KIT_TWEEN_FRAMES)
                    ++app->settings_anim_frame;
                if(app->settings_anim_frame == UI_KIT_TWEEN_FRAMES)
                    app->settings_selection_motion = false;
            }
            if(app->settings_toggle_motion) {
                if(app->settings_toggle_frame < 4U) ++app->settings_toggle_frame;
                if(app->settings_toggle_frame == 4U)
                    app->settings_toggle_motion = false;
            }
        }
        if(app->ui_carousel_motion || app->ui_list_motion) {
            if(app->ui_frame < UI_KIT_TWEEN_FRAMES) ++app->ui_frame;
            if(app->ui_frame == UI_KIT_TWEEN_FRAMES) {
                app->ui_carousel_motion = false;
                app->ui_list_motion = false;
            }
        }
        if(app->screen == LabMateScreenAbout &&
           (app->info_page_motion || app->info_scroll_motion ||
            app->info_section_motion)) {
            if(app->info_motion_frame < UI_KIT_TWEEN_FRAMES) ++app->info_motion_frame;
            if(app->info_scroll_motion) {
                app->info_scroll_render_px = labmate_info_scroll_pixel(
                    app->info_scroll_from_px,
                    (int16_t)app->info_guide_scroll_steps * 12,
                    app->info_motion_frame);
            }
            if(app->info_motion_frame == UI_KIT_TWEEN_FRAMES) {
                app->info_page_motion = false;
                app->info_scroll_motion = false;
                app->info_section_motion = false;
                app->info_scroll_render_px = (int16_t)app->info_guide_scroll_steps * 12;
            }
        }
        /* Decorative pulse is presentation-only; measurement trace sampling
         * below still runs when animations are disabled. */
        if(app->ui_prefs.animations) ++app->ui_pulse_phase;
    }

    /* Small UI-only history; never alters capture, logger or statistics.
     * Each sample is a normalized *relative trend* around recorded extrema,
     * not invented edge timing or an electrical waveform. */
    if(app->screen == LabMateScreenFrequency && app->frequency_valid &&
       !app->hold && (uint32_t)(now - app->ui_trace_tick) >= tps / 10U) {
        app->ui_trace_tick = now;
        uint8_t display = 128U;
        if(app->frequency_stats_valid &&
           app->frequency_max_millihz > app->frequency_min_millihz) {
            uint32_t mhz = app->frequency_millihz;
            if(mhz < app->frequency_min_millihz) mhz = app->frequency_min_millihz;
            if(mhz > app->frequency_max_millihz) mhz = app->frequency_max_millihz;
            display = (uint8_t)((uint64_t)(mhz - app->frequency_min_millihz) * 255U /
                                (app->frequency_max_millihz - app->frequency_min_millihz));
        }
        app->ui_frequency_trace[app->ui_frequency_trace_head] = display;
        app->ui_frequency_trace_head = (app->ui_frequency_trace_head + 1U) % 100U;
        if(app->ui_frequency_trace_count < 100U) ++app->ui_frequency_trace_count;
    }
}
