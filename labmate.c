#include <furi.h>
#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <furi_hal_interrupt.h>
#include <furi_hal_bus.h>
#include <stm32wbxx_ll_tim.h>
#include <gui/gui.h>
#include <input/input.h>

#define MENU_COUNT 5
#define GPIO_COUNT 8

#define LABMATE_GEN_TIMER     TIM2
#define LABMATE_GEN_TIMER_BUS FuriHalBusTIM2
#define LABMATE_GEN_TIMER_IRQ FuriHalInterruptIdTIM2

typedef enum {
    LabMateScreenMenu,
    LabMateScreenGpio,
    LabMateScreenFrequency,
    LabMateScreenPulse,
    LabMateScreenGenerator,
    LabMateScreenAbout,
} LabMateScreen;

typedef struct {
    bool running;
    bool hold;

    uint8_t selected;
    uint8_t gpio_index;

    LabMateScreen screen;

    bool gpio_state;
    bool gpio_previous_state;
    uint32_t edges;

    /* Frequency meter */
    uint32_t frequency_last_edge;
    uint32_t frequency_period_ticks;
    uint32_t frequency_millihz;
    bool frequency_edge_seen;
    bool frequency_valid;

    volatile uint32_t frequency_irq_last_cycle;
    volatile uint32_t frequency_irq_period_cycles;
    volatile uint32_t frequency_irq_last_tick;
    volatile uint32_t frequency_irq_edges;
    volatile bool frequency_irq_new_period;
    bool frequency_irq_active;

    uint32_t frequency_period_samples[4];
    uint8_t frequency_sample_index;
    uint8_t frequency_sample_count;

    /* Pulse analyzer */
    uint32_t pulse_last_edge;
    uint32_t pulse_high_ticks;
    uint32_t pulse_low_ticks;
    uint32_t pulse_period_ticks;
    uint32_t pulse_duty_permille;

    bool pulse_high_valid;
    bool pulse_low_valid;
    bool pulse_period_valid;

    /* Signal generator */
    bool generator_running;
    bool generator_state;
    uint8_t generator_freq_index;
    uint32_t generator_last_toggle;

    FuriMutex* mutex;
} LabMateApp;

static const char* menu_items[MENU_COUNT] = {
    "GPIO Monitor",
    "Frequency Meter",
    "Pulse Analyzer",
    "Signal Generator",
    "About",
};

static const GpioPin* labmate_gpio_pins[GPIO_COUNT] = {
    &gpio_ext_pc0,
    &gpio_ext_pc1,
    &gpio_ext_pc3,
    &gpio_ext_pb2,
    &gpio_ext_pb3,
    &gpio_ext_pa4,
    &gpio_ext_pa6,
    &gpio_ext_pa7,
};

static const char* gpio_names[GPIO_COUNT] = {
    "PC0",
    "PC1",
    "PC3",
    "PB2",
    "PB3",
    "PA4",
    "PA6",
    "PA7",
};

/*
 * Conservative self-test frequencies.
 * Designed for the current polling-based
 * measurement engine.
 */
static const uint32_t generator_frequencies[] = {
    1,
    2,
    5,
};

#define GENERATOR_FREQ_COUNT 3

static void frequency_gpio_callback(void* context) {
    LabMateApp* app = context;

    /*
     * High-resolution timestamp.
     * Unsigned subtraction also handles a single
     * 32-bit CYCCNT wrap correctly.
     */
    uint32_t now_cycle = DWT->CYCCNT;

    if(app->frequency_irq_last_cycle != 0) {
        app->frequency_irq_period_cycles =
            now_cycle -
            app->frequency_irq_last_cycle;

        app->frequency_irq_new_period = true;
    }

    app->frequency_irq_last_cycle = now_cycle;
    app->frequency_irq_last_tick = furi_get_tick();
    app->frequency_irq_edges++;
}

static void frequency_interrupt_stop(LabMateApp* app) {
    if(!app->frequency_irq_active) return;

    const GpioPin* pin =
        labmate_gpio_pins[app->gpio_index];

    furi_hal_gpio_disable_int_callback(pin);
    furi_hal_gpio_remove_int_callback(pin);

    app->frequency_irq_active = false;
}

static void frequency_interrupt_start(LabMateApp* app) {
    const GpioPin* pin =
        labmate_gpio_pins[app->gpio_index];

    app->frequency_irq_last_cycle = 0;
    app->frequency_irq_period_cycles = 0;
    app->frequency_irq_last_tick = 0;
    app->frequency_irq_edges = 0;
    app->frequency_irq_new_period = false;

    furi_hal_gpio_init(
        pin,
        GpioModeInterruptRise,
        GpioPullNo,
        GpioSpeedVeryHigh);

    furi_hal_gpio_add_int_callback(
        pin,
        frequency_gpio_callback,
        app);

    furi_hal_gpio_enable_int_callback(pin);

    app->frequency_irq_active = true;
}

static void gpio_release(uint8_t index) {
    furi_hal_gpio_init_simple(
        labmate_gpio_pins[index],
        GpioModeAnalog);
}

static void measurement_reset(LabMateApp* app) {
    uint32_t now = furi_get_tick();

    app->edges = 0;

    app->frequency_last_edge = now;
    app->frequency_period_ticks = 0;
    app->frequency_millihz = 0;
    app->frequency_edge_seen = false;
    app->frequency_valid = false;

    memset(
        app->frequency_period_samples,
        0,
        sizeof(app->frequency_period_samples));

    app->frequency_sample_index = 0;
    app->frequency_sample_count = 0;

    app->pulse_last_edge = now;
    app->pulse_high_ticks = 0;
    app->pulse_low_ticks = 0;
    app->pulse_period_ticks = 0;
    app->pulse_duty_permille = 0;

    app->pulse_high_valid = false;
    app->pulse_low_valid = false;
    app->pulse_period_valid = false;
}

static void gpio_activate(LabMateApp* app) {
    furi_hal_gpio_init_simple(
        labmate_gpio_pins[app->gpio_index],
        GpioModeInput);

    app->gpio_state =
        furi_hal_gpio_read(
            labmate_gpio_pins[app->gpio_index]);

    app->gpio_previous_state =
        app->gpio_state;

    measurement_reset(app);
}

static void gpio_change(
    LabMateApp* app,
    int8_t direction) {

    /*
     * Frequency Meter owns an active GPIO IRQ.
     * Runtime pin switching is intentionally locked
     * for maximum stability.
     */
    if(app->screen == LabMateScreenFrequency) {
        return;
    }

    gpio_release(app->gpio_index);

    if(direction > 0) {
        app->gpio_index++;

        if(app->gpio_index >= GPIO_COUNT) {
            app->gpio_index = 0;
        }
    } else {
        if(app->gpio_index == 0) {
            app->gpio_index = GPIO_COUNT - 1;
        } else {
            app->gpio_index--;
        }
    }

    gpio_activate(app);
}

static uint32_t ticks_to_ms(uint32_t ticks) {
    uint32_t frequency =
        furi_kernel_get_tick_frequency();

    if(frequency == 0) {
        return 0;
    }

    return (uint32_t)(
        ((uint64_t)ticks * 1000ULL) /
        frequency);
}

static void pulse_recalculate(LabMateApp* app) {
    if(!app->pulse_high_valid ||
       !app->pulse_low_valid) {
        return;
    }

    uint64_t period =
        (uint64_t)app->pulse_high_ticks +
        (uint64_t)app->pulse_low_ticks;

    if(period == 0 ||
       period > UINT32_MAX) {
        app->pulse_period_valid = false;
        return;
    }

    app->pulse_period_ticks =
        (uint32_t)period;

    app->pulse_duty_permille =
        (uint32_t)(
            ((uint64_t)app->pulse_high_ticks *
             1000ULL) /
            period);

    app->pulse_period_valid = true;
}

static void measurement_update(LabMateApp* app) {
    if(app->hold) return;

    uint32_t now = furi_get_tick();
    uint32_t tick_frequency =
        furi_kernel_get_tick_frequency();

    /*
     * FREQUENCY METER
     *
     * Rising edges are captured by the GPIO interrupt.
     * The main loop only consumes the period measured
     * by the ISR and performs filtering/calculation.
     */
    if(app->screen == LabMateScreenFrequency) {

        if(app->frequency_irq_new_period) {

            uint32_t period_cycles;

            /*
             * Copy the volatile ISR value first, then
             * acknowledge it.
             */
            period_cycles =
                app->frequency_irq_period_cycles;

            app->frequency_irq_new_period = false;

            if(period_cycles > 0 &&
               SystemCoreClock > 0) {

                app->frequency_period_samples[
                    app->frequency_sample_index] =
                    period_cycles;

                app->frequency_sample_index =
                    (app->frequency_sample_index + 1U) %
                    4U;

                if(app->frequency_sample_count < 4U) {
                    app->frequency_sample_count++;
                }

                uint64_t period_sum = 0;

                for(uint8_t s = 0;
                    s < app->frequency_sample_count;
                    s++) {

                    period_sum +=
                        app->frequency_period_samples[s];
                }

                uint32_t average_period =
                    (uint32_t)(
                        (period_sum +
                         (app->frequency_sample_count /
                          2U)) /
                        app->frequency_sample_count);

                if(average_period > 0) {

                    app->frequency_period_ticks =
                        average_period;

                    app->frequency_millihz =
                        (uint32_t)(
                            (((uint64_t)SystemCoreClock *
                              1000ULL) +
                             (average_period / 2U)) /
                            average_period);

                    app->frequency_valid = true;
                }
            }
        }

        /*
         * Keep the displayed edge counter connected
         * to the real interrupt counter.
         */
        app->edges =
            app->frequency_irq_edges;

        /*
         * No rising edge for 3 seconds -> signal lost.
         */
        if(app->frequency_irq_last_tick != 0 &&
           tick_frequency > 0) {

            uint32_t no_edge_ticks =
                now -
                app->frequency_irq_last_tick;

            if(no_edge_ticks >
               (tick_frequency * 3U)) {

                app->frequency_millihz = 0;
                app->frequency_valid = false;

                app->frequency_sample_index = 0;
                app->frequency_sample_count = 0;

                memset(
                    app->frequency_period_samples,
                    0,
                    sizeof(
                        app->frequency_period_samples));
            }
        }

        return;
    }

    /*
     * GPIO MONITOR / PULSE ANALYZER
     *
     * Keep the original polling implementation.
     */
    bool current =
        furi_hal_gpio_read(
            labmate_gpio_pins[
                app->gpio_index]);

    if(current != app->gpio_previous_state) {

        uint32_t duration =
            now - app->pulse_last_edge;

        app->edges++;

        if(app->gpio_previous_state) {

            app->pulse_high_ticks =
                duration;

            app->pulse_high_valid = true;

        } else {

            app->pulse_low_ticks =
                duration;

            app->pulse_low_valid = true;
        }

        app->pulse_last_edge = now;

        pulse_recalculate(app);

        app->gpio_previous_state =
            current;
    }

    app->gpio_state = current;
}

/* ---------- SIGNAL GENERATOR ---------- */

static void generator_timer_isr(void* context) {
    LabMateApp* app = context;

    LL_TIM_ClearFlag_UPDATE(LABMATE_GEN_TIMER);

    if(!app || !app->generator_running) {
        return;
    }

    app->generator_state =
        !app->generator_state;

    furi_hal_gpio_write(
        &gpio_ext_pa7,
        app->generator_state);
}

static void generator_stop(LabMateApp* app) {
    if(app->generator_running) {
        LL_TIM_DisableIT_UPDATE(LABMATE_GEN_TIMER);
        LL_TIM_DisableCounter(LABMATE_GEN_TIMER);

        furi_hal_interrupt_set_isr(
            LABMATE_GEN_TIMER_IRQ,
            NULL,
            NULL);

        furi_hal_bus_disable(
            LABMATE_GEN_TIMER_BUS);
    }

    app->generator_running = false;
    app->generator_state = false;

    furi_hal_gpio_write(
        &gpio_ext_pa7,
        false);

    furi_hal_gpio_init_simple(
        &gpio_ext_pa7,
        GpioModeAnalog);
}

static void generator_start(LabMateApp* app) {
    uint32_t freq =
        generator_frequencies[
            app->generator_freq_index];

    if(freq == 0) {
        return;
    }

    app->generator_state = false;

    furi_hal_gpio_init_simple(
        &gpio_ext_pa7,
        GpioModeOutputPushPull);

    furi_hal_gpio_write(
        &gpio_ext_pa7,
        false);

    furi_hal_bus_enable(
        LABMATE_GEN_TIMER_BUS);

    /*
     * 50% duty cycle:
     * GPIO toggles twice per complete output period.
     */
    uint32_t toggle_frequency =
        freq * 2U;

    LL_TIM_InitTypeDef timer_init = {0};

    timer_init.Autoreload =
        (SystemCoreClock / toggle_frequency) - 1U;

    LL_TIM_Init(
        LABMATE_GEN_TIMER,
        &timer_init);

    LL_TIM_SetCounter(
        LABMATE_GEN_TIMER,
        0);

    LL_TIM_ClearFlag_UPDATE(
        LABMATE_GEN_TIMER);

    furi_hal_interrupt_set_isr(
        LABMATE_GEN_TIMER_IRQ,
        generator_timer_isr,
        app);

    app->generator_running = true;

    LL_TIM_EnableIT_UPDATE(
        LABMATE_GEN_TIMER);

    LL_TIM_EnableCounter(
        LABMATE_GEN_TIMER);
}
static void generator_change_frequency(
    LabMateApp* app,
    int8_t direction) {

    if(direction > 0) {
        app->generator_freq_index++;

        if(app->generator_freq_index >=
           GENERATOR_FREQ_COUNT) {

            app->generator_freq_index = 0;
        }
    } else {
        if(app->generator_freq_index == 0) {
            app->generator_freq_index =
                GENERATOR_FREQ_COUNT - 1;
        } else {
            app->generator_freq_index--;
        }
    }

    /*
     * Restart timing cleanly when frequency
     * changes while generator is running.
     */
    if(app->generator_running) {
        generator_stop(app);
        generator_start(app);
    }
}

/* ---------- DRAWING ---------- */

static void draw_menu(
    Canvas* canvas,
    LabMateApp* app) {

    canvas_set_font(
        canvas,
        FontPrimary);

    canvas_draw_str(
        canvas,
        2,
        10,
        "FLIPPER LABMATE");

    canvas_set_font(
        canvas,
        FontSecondary);

    /*
     * Five items do not fit with the old
     * subtitle layout, so use compact rows.
     */
    for(uint8_t i = 0;
        i < MENU_COUNT;
        i++) {

        uint8_t y =
            22 + (i * 10);

        if(i == app->selected) {
            canvas_draw_box(
                canvas,
                0,
                y - 8,
                128,
                10);

            canvas_set_color(
                canvas,
                ColorWhite);

            canvas_draw_str(
                canvas,
                5,
                y,
                menu_items[i]);

            canvas_set_color(
                canvas,
                ColorBlack);
        } else {
            canvas_draw_str(
                canvas,
                5,
                y,
                menu_items[i]);
        }
    }
}

static void draw_gpio(
    Canvas* canvas,
    LabMateApp* app) {

    char buffer[32];

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(
        canvas,
        2,
        10,
        "GPIO MONITOR");

    canvas_set_font(canvas, FontSecondary);

    snprintf(
        buffer,
        sizeof(buffer),
        "PIN: %s",
        gpio_names[app->gpio_index]);

    canvas_draw_str(
        canvas,
        2,
        23,
        buffer);

    snprintf(
        buffer,
        sizeof(buffer),
        "STATE: %s",
        app->gpio_state ?
            "HIGH" : "LOW");

    canvas_draw_str(
        canvas,
        2,
        34,
        buffer);

    snprintf(
        buffer,
        sizeof(buffer),
        "EDGES: %lu",
        (unsigned long)app->edges);

    canvas_draw_str(
        canvas,
        2,
        45,
        buffer);

    canvas_draw_str(
        canvas,
        84,
        23,
        app->hold ?
            "[HOLD]" : "[LIVE]");

    canvas_draw_str(
        canvas,
        2,
        56,
        "PIN LOCK");

    canvas_draw_str(
        canvas,
        73,
        56,
        "OK HOLD");
}

static void draw_frequency(
    Canvas* canvas,
    LabMateApp* app) {

    char buffer[32];

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(
        canvas,
        2,
        10,
        "FREQUENCY METER");

    canvas_set_font(canvas, FontSecondary);

    snprintf(
        buffer,
        sizeof(buffer),
        "PIN: %s",
        gpio_names[app->gpio_index]);

    canvas_draw_str(
        canvas,
        2,
        23,
        buffer);

    canvas_draw_str(
        canvas,
        84,
        23,
        app->hold ?
            "[HOLD]" : "[LIVE]");

    if(app->frequency_valid) {
        uint32_t whole =
            app->frequency_millihz / 1000;

        uint32_t decimal =
            (app->frequency_millihz % 1000) /
            10;

        snprintf(
            buffer,
            sizeof(buffer),
            "FREQ: %lu.%02lu Hz",
            (unsigned long)whole,
            (unsigned long)decimal);
    } else {
        snprintf(
            buffer,
            sizeof(buffer),
            "FREQ: --- Hz");
    }

    canvas_draw_str(
        canvas,
        2,
        36,
        buffer);

    snprintf(
        buffer,
        sizeof(buffer),
        "EDGES: %lu",
        (unsigned long)app->edges);

    canvas_draw_str(
        canvas,
        2,
        47,
        buffer);

    canvas_draw_str(
        canvas,
        2,
        59,
        "PIN LOCK");

    canvas_draw_str(
        canvas,
        73,
        59,
        "OK HOLD");
}

static void draw_pulse(
    Canvas* canvas,
    LabMateApp* app) {

    char buffer[32];

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(
        canvas,
        2,
        9,
        "PULSE ANALYZER");

    canvas_set_font(canvas, FontSecondary);

    snprintf(
        buffer,
        sizeof(buffer),
        "PIN:%s",
        gpio_names[app->gpio_index]);

    canvas_draw_str(
        canvas,
        2,
        19,
        buffer);

    canvas_draw_str(
        canvas,
        85,
        19,
        app->hold ?
            "HOLD" : "LIVE");

    if(app->pulse_high_valid) {
        snprintf(
            buffer,
            sizeof(buffer),
            "HIGH:%lu ms",
            (unsigned long)
                ticks_to_ms(
                    app->pulse_high_ticks));
    } else {
        snprintf(
            buffer,
            sizeof(buffer),
            "HIGH:--- ms");
    }

    canvas_draw_str(
        canvas,
        2,
        29,
        buffer);

    if(app->pulse_low_valid) {
        snprintf(
            buffer,
            sizeof(buffer),
            "LOW :%lu ms",
            (unsigned long)
                ticks_to_ms(
                    app->pulse_low_ticks));
    } else {
        snprintf(
            buffer,
            sizeof(buffer),
            "LOW :--- ms");
    }

    canvas_draw_str(
        canvas,
        2,
        39,
        buffer);

    if(app->pulse_period_valid) {
        uint32_t duty_whole =
            app->pulse_duty_permille / 10;

        uint32_t duty_decimal =
            app->pulse_duty_permille % 10;

        snprintf(
            buffer,
            sizeof(buffer),
            "PER:%lu D:%lu.%lu%%",
            (unsigned long)
                ticks_to_ms(
                    app->pulse_period_ticks),
            (unsigned long)duty_whole,
            (unsigned long)duty_decimal);
    } else {
        snprintf(
            buffer,
            sizeof(buffer),
            "PER:--- D:---");
    }

    canvas_draw_str(
        canvas,
        2,
        49,
        buffer);

    canvas_draw_str(
        canvas,
        2,
        61,
        "PIN LOCK");

    canvas_draw_str(
        canvas,
        73,
        61,
        "OK HOLD");
}

static void draw_generator(
    Canvas* canvas,
    LabMateApp* app) {

    char buffer[32];

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(
        canvas,
        2,
        10,
        "SIGNAL GENERATOR");

    canvas_set_font(canvas, FontSecondary);

    canvas_draw_str(
        canvas,
        2,
        23,
        "OUT: PA7");

    snprintf(
        buffer,
        sizeof(buffer),
        "FREQ: %lu Hz",
        (unsigned long)
            generator_frequencies[
                app->generator_freq_index]);

    canvas_draw_str(
        canvas,
        2,
        34,
        buffer);

    canvas_draw_str(
        canvas,
        2,
        45,
        "DUTY: 50%");

    canvas_draw_str(
        canvas,
        75,
        45,
        app->generator_running ?
            "RUN" : "STOP");

    canvas_draw_str(
        canvas,
        2,
        58,
        "< > FREQ");

    canvas_draw_str(
        canvas,
        72,
        58,
        "OK ON/OFF");
}

static void draw_about(
    Canvas* canvas) {

    canvas_set_font(
        canvas,
        FontPrimary);

    canvas_draw_str(
        canvas,
        2,
        12,
        "LabMate v1.0");

    canvas_set_font(
        canvas,
        FontSecondary);

    canvas_draw_str(
        canvas,
        2,
        25,
        "Digital Signal Toolkit");

    canvas_draw_str(
        canvas,
        2,
        36,
        "GPIO / FREQ / PULSE");

    canvas_draw_str(
        canvas,
        2,
        47,
        "TIM2 Signal Generator");

    canvas_draw_str(
        canvas,
        2,
        58,
        "3.3V GPIO ONLY");
}

static void render_callback(
    Canvas* canvas,
    void* ctx) {

    LabMateApp* app = ctx;

    furi_mutex_acquire(
        app->mutex,
        FuriWaitForever);

    canvas_clear(canvas);

    switch(app->screen) {
    case LabMateScreenMenu:
        draw_menu(canvas, app);
        break;

    case LabMateScreenGpio:
        draw_gpio(canvas, app);
        break;

    case LabMateScreenFrequency:
        draw_frequency(canvas, app);
        break;

    case LabMateScreenPulse:
        draw_pulse(canvas, app);
        break;

    case LabMateScreenGenerator:
        draw_generator(canvas, app);
        break;

    case LabMateScreenAbout:
        draw_about(canvas);
        break;
    }

    furi_mutex_release(
        app->mutex);
}

static void input_callback(
    InputEvent* input_event,
    void* ctx) {

    FuriMessageQueue* queue =
        ctx;

    furi_message_queue_put(
        queue,
        input_event,
        0);
}

static bool screen_uses_gpio(
    LabMateScreen screen) {

    return
        screen == LabMateScreenGpio ||
        screen == LabMateScreenFrequency ||
        screen == LabMateScreenPulse;
}

int32_t labmate_app(void* p) {
    UNUSED(p);

    LabMateApp* app =
        malloc(sizeof(LabMateApp));

    if(!app) {
        return -1;
    }

    memset(
        app,
        0,
        sizeof(LabMateApp));

    app->running = true;
    app->hold = false;
    app->selected = 0;
    app->gpio_index = 1; /* PC1 */
    app->generator_freq_index = 0; /* 1 Hz */
    app->screen = LabMateScreenMenu;

    app->mutex =
        furi_mutex_alloc(
            FuriMutexTypeNormal);

    if(!app->mutex) {
        free(app);
        return -1;
    }

    FuriMessageQueue* queue =
        furi_message_queue_alloc(
            16,
            sizeof(InputEvent));

    if(!queue) {
        furi_mutex_free(app->mutex);
        free(app);
        return -1;
    }

    ViewPort* viewport =
        view_port_alloc();

    if(!viewport) {
        furi_message_queue_free(queue);
        furi_mutex_free(app->mutex);
        free(app);
        return -1;
    }

    view_port_draw_callback_set(
        viewport,
        render_callback,
        app);

    view_port_input_callback_set(
        viewport,
        input_callback,
        queue);

    Gui* gui =
        furi_record_open(
            RECORD_GUI);

    gui_add_view_port(
        gui,
        viewport,
        GuiLayerFullscreen);

    InputEvent event;

    while(app->running) {
        FuriStatus status =
            furi_message_queue_get(
                queue,
                &event,
                10);

        furi_mutex_acquire(
            app->mutex,
            FuriWaitForever);

        if(screen_uses_gpio(
               app->screen)) {
            measurement_update(app);
        }

        if(status == FuriStatusOk &&
           event.type == InputTypePress) {

            if(app->screen ==
               LabMateScreenMenu) {

                if(event.key == InputKeyUp) {
                    if(app->selected == 0) {
                        app->selected =
                            MENU_COUNT - 1;
                    } else {
                        app->selected--;
                    }

                } else if(
                    event.key == InputKeyDown) {

                    app->selected++;

                    if(app->selected >=
                       MENU_COUNT) {
                        app->selected = 0;
                    }

                } else if(
                    event.key == InputKeyOk) {

                    switch(app->selected) {
                    case 0:
                        app->screen =
                            LabMateScreenGpio;
                        app->hold = false;
                        gpio_activate(app);
                        break;

                    case 1:
                        app->screen =
                            LabMateScreenFrequency;
                        app->hold = false;

                        measurement_reset(app);
                        frequency_interrupt_start(app);
                        break;

                    case 2:
                        app->screen =
                            LabMateScreenPulse;
                        app->hold = false;
                        gpio_activate(app);
                        break;

                    case 3:
                        app->screen =
                            LabMateScreenGenerator;
                        break;

                    case 4:
                        app->screen =
                            LabMateScreenAbout;
                        break;
                    }

                } else if(
                    event.key == InputKeyBack) {
                    app->running = false;
                }

            } else if(
                screen_uses_gpio(
                    app->screen)) {

                if(event.key == InputKeyLeft) {
                    gpio_change(app, -1);

                } else if(
                    event.key == InputKeyRight) {
                    gpio_change(app, 1);

                } else if(
                    event.key == InputKeyOk) {

                    app->hold =
                        !app->hold;

                    if(!app->hold) {
                        app->gpio_state =
                            furi_hal_gpio_read(
                                labmate_gpio_pins[
                                    app->gpio_index]);

                        app->gpio_previous_state =
                            app->gpio_state;

                        measurement_reset(app);
                    }

                } else if(
                    event.key == InputKeyBack) {

                    if(app->screen ==
                       LabMateScreenFrequency) {
                        frequency_interrupt_stop(app);
                    }

                    gpio_release(
                        app->gpio_index);

                    app->hold = false;
                    app->screen =
                        LabMateScreenMenu;
                }

            } else if(
                app->screen ==
                LabMateScreenGenerator) {

                if(event.key == InputKeyLeft) {
                    generator_change_frequency(
                        app,
                        -1);

                } else if(
                    event.key == InputKeyRight) {
                    generator_change_frequency(
                        app,
                        1);

                } else if(
                    event.key == InputKeyOk) {

                    if(app->generator_running) {
                        generator_stop(app);
                    } else {
                        generator_start(app);
                    }

                } else if(
                    event.key == InputKeyBack) {

                    /*
                     * Keep generator running in background.
                     * Use OK in Generator screen to stop it.
                     */
                    app->screen =
                        LabMateScreenMenu;
                }

            } else {
                if(event.key == InputKeyBack) {
                    app->screen =
                        LabMateScreenMenu;
                }
            }
        }

        furi_mutex_release(
            app->mutex);

        view_port_update(
            viewport);
    }

    if(app->generator_running) {
        generator_stop(app);
    }

    if(screen_uses_gpio(
           app->screen)) {
        gpio_release(
            app->gpio_index);
    }

    gui_remove_view_port(
        gui,
        viewport);

    view_port_free(
        viewport);

    furi_record_close(
        RECORD_GUI);

    furi_message_queue_free(
        queue);

    furi_mutex_free(
        app->mutex);

    free(app);

    return 0;
}























