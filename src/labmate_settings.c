#include "labmate_settings.h"
#include "labmate_settings_view.h"
#include "labmate_info_ui.h"
#include "labmate_ui_motion.h"
#include "ui_kit.h"

static void prefs_save_request(LabMateApp* app, LabMateDeferredWork* work) {
    if(app->ui_prefs_busy) return;
    app->ui_prefs_busy = true;
    app->ui_prefs_notice = 0U;
    app->settings_toast_active = false;
    ++app->ui_prefs.generation;
    work->ui_prefs_save_requested = true;
    work->proposed_ui_prefs = app->ui_prefs;
    work->proposed_ui_prefs_copy = app->ui_prefs_active_copy;
}

void labmate_settings_draw(Canvas* canvas, const LabMateApp* app) {
    if(!canvas || !app) return;
    const uint32_t elapsed = (uint32_t)(furi_get_tick() - app->settings_toast_tick);
    const uint32_t tps = furi_kernel_get_tick_frequency();
    const uint32_t total = (tps * 12U + 9U) / 10U;
    const uint32_t transition = (tps * UI_KIT_FRAME_MS * 4U + 999U) / 1000U;
    uint8_t toast_progress = 0U;
    if(app->settings_toast_active && total > transition * 2U && elapsed < total) {
        if(!app->ui_prefs.animations ||
           (elapsed >= transition && elapsed < total-transition))
            toast_progress = 255U;
        else if(elapsed < transition) {
            uint8_t frame = (uint8_t)((elapsed * 4U) / transition + 1U);
            if(frame > 4U) frame = 4U;
            toast_progress = (uint8_t)(255U * ui_kit_ease(frame, 4U) / 256U);
        } else {
            uint8_t frame = (uint8_t)(((elapsed - (total-transition))*4U) / transition + 1U);
            if(frame > 4U) frame = 4U;
            toast_progress = (uint8_t)(255U - 255U * ui_kit_ease(frame, 4U) / 256U);
        }
    }
    LabMateSettingsVisual visual = {
        .previous_selected = app->settings_anim_previous,
        .selection_frame = app->settings_anim_frame,
        .selection_motion = app->settings_selection_motion,
        .toggle_index = app->settings_toggle_index,
        .toggle_frame = app->settings_toggle_frame,
        .toggle_motion = app->settings_toggle_motion,
        .toast_progress = toast_progress,
        .toast_reset = app->settings_toast_reset,
    };
    labmate_settings_draw_animated(
        canvas, &app->ui_prefs, app->settings_selected,
        (LabMateSettingsPage)app->settings_page,
        app->ui_prefs_notice, app->ui_prefs_busy,
        app->settings_reset_confirm_selected, &visual);
}

static void settings_select(LabMateApp* app, uint8_t next) {
    const uint8_t previous = app->settings_selected;
    if(previous == next) return;
    app->settings_selected = next;
    app->settings_selection_motion = app->ui_prefs.animations;
    app->settings_anim_previous = previous;
    app->settings_anim_frame = app->ui_prefs.animations ? 0U : UI_KIT_TWEEN_FRAMES;
    app->ui_frame_tick = furi_get_tick();
}

static void settings_toggle_start(LabMateApp* app, uint8_t index) {
    app->settings_toggle_index = index;
    app->settings_toggle_motion = app->ui_prefs.animations;
    app->settings_toggle_frame = app->ui_prefs.animations ? 0U : 4U;
    app->ui_frame_tick = furi_get_tick();
}

void labmate_settings_input(
    LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    if(!app || !work || app->ui_prefs_busy) return;
    if(app->settings_page == LabMateSettingsLanguage) {
        if(event.key == InputKeyBack || event.key == InputKeyOk)
            app->settings_page = LabMateSettingsList;
        return;
    }
    if(app->settings_page == LabMateSettingsReset) {
        if(event.key == InputKeyBack) app->settings_page = LabMateSettingsList;
        else if(event.key == InputKeyLeft)
            app->settings_reset_confirm_selected = false;
        else if(event.key == InputKeyRight)
            app->settings_reset_confirm_selected = true;
        else if(event.key == InputKeyOk) {
            if(!app->settings_reset_confirm_selected) {
                app->settings_page = LabMateSettingsList;
                return;
            }
            const uint32_t generation = app->ui_prefs.generation;
            labmate_ui_prefs_defaults(&app->ui_prefs);
            app->ui_prefs.generation = generation;
            /* Disable transient transitions immediately on reset. */
            app->ui_carousel_motion = false;
            app->ui_list_motion = false;
            labmate_ui_motion_info_cancel(app);
            app->settings_selection_motion = false;
            app->settings_toggle_motion = false;
            app->settings_page = LabMateSettingsList;
            app->settings_toast_reset = true;
            prefs_save_request(app, work);
        }
        return;
    }
    if(event.key == InputKeyUp) {
        if(app->settings_selected > 0U)
            settings_select(app, (uint8_t)(app->settings_selected - 1U));
    } else if(event.key == InputKeyDown) {
        if(app->settings_selected < 4U)
            settings_select(app, (uint8_t)(app->settings_selected + 1U));
    } else if(event.key == InputKeyBack) {
        app->screen = LabMateScreenMenu;
        app->menu_in_group = false;
        app->selected = LabMateGroupInfo;
    } else if(event.key == InputKeyOk) {
        switch(app->settings_selected) {
        case 0U:
            app->settings_page = LabMateSettingsLanguage;
            break;
        case 1U:
            app->ui_prefs.animations = !app->ui_prefs.animations;
            if(!app->ui_prefs.animations) {
                app->ui_carousel_motion = false;
                app->ui_list_motion = false;
                labmate_ui_motion_info_cancel(app);
            } else {
                app->ui_frame_tick = furi_get_tick();
            }
            app->settings_toast_reset = false;
            settings_toggle_start(app, 1U);
            prefs_save_request(app, work);
            break;
        case 2U:
            app->ui_prefs.startup_animation = !app->ui_prefs.startup_animation;
            app->settings_toast_reset = false;
            settings_toggle_start(app, 2U);
            prefs_save_request(app, work);
            break;
        case 3U:
            app->screen = LabMateScreenAbout;
            app->about_page = 0U;
            app->info_section = LabMateInfoHome;
            app->info_selected = 0U;
            app->info_safety_page = 0U;
            app->info_guide_selected = 0U;
            app->info_guide_scroll_steps = 0U;
            labmate_ui_motion_info_cancel(app);
            break;
        case 4U:
            app->settings_reset_confirm_selected = false; /* Safe default: Cancel */
            app->settings_page = LabMateSettingsReset;
            break;
        default: break;
        }
    }
}
