/* Read-only reference LCD renderer host contract, without firmware GPIO.
 * cc -std=c11 -Wall -Wextra -Werror -pedantic \
 *   -Itests/host_stubs -Isrc \
 *   tests/test_scope_reference_view.c \
 *   src/labmate_scope_reference_view.c src/labmate_scope_tolerance.c \
 *   src/labmate_scope_compare.c -o /tmp/test_scope_reference_view
 */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "labmate_scope_reference_view.h"

struct Canvas {
    unsigned count;
    char lines[12][32];
};

void canvas_set_font(Canvas* canvas, Font font) {
    (void)canvas;
    assert(font == FontSecondary);
}

void canvas_draw_str(Canvas* canvas, int32_t x, int32_t y, const char* text) {
    assert(canvas && text);
    assert(x >= 0 && x < 128 && y >= 0 && y < 64);
    assert(canvas->count < 12U);
    (void)snprintf(
        canvas->lines[canvas->count], sizeof(canvas->lines[0]), "%s", text);
    ++canvas->count;
}

void canvas_draw_line(
    Canvas* canvas, int32_t x0, int32_t y0, int32_t x1, int32_t y1) {
    assert(canvas);
    assert(x0 >= 0 && x0 < 128 && x1 >= 0 && x1 < 128);
    assert(y0 >= 0 && y0 < 64 && y1 >= 0 && y1 < 64);
}

static bool contains(const Canvas* canvas, const char* exact) {
    for(unsigned i = 0U; i < canvas->count; ++i) {
        if(strcmp(canvas->lines[i], exact) == 0) return true;
    }
    return false;
}

static LabMateScopeMetrics one_complete_cycle(void) {
    const LabMateScopeEdge e[] = {
        {.tick = 100U, .delta_ticks = 0U, .high = true},
        {.tick = 600U, .delta_ticks = 500U, .high = false},
        {.tick = 1100U, .delta_ticks = 500U, .high = true},
    };
    const LabMateScopeMetrics m =
        labmate_scope_metrics_from_edges(e, 3U, 1000000U);
    assert(m.status == LabMateScopeMetricsReady && !m.truncated);
    return m;
}

static void test_real_metrics_and_invalid_no_fake_pass(void) {
    LabMateScopeReference reference = {0};
    assert(labmate_scope_reference_preset(
        LabMateScopeReference1kHz50, &reference));
    LabMateScopeMetrics m = one_complete_cycle();
    LabMateScopeToleranceResult result = labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationComplete);
    assert(result.verdict == LabMateScopeVerdictPass);
    Canvas canvas = {0};
    assert(labmate_scope_reference_view_draw(
        &canvas, LabMateScopeReference1kHz50, result, &m));
    assert(contains(&canvas, "PASS"));
    assert(contains(&canvas, "MEAS 1000.00Hz"));
    assert(contains(&canvas, "DUTY 50.0%"));
    assert(contains(&canvas, "TARGET 1kHz 50%"));
    assert(contains(&canvas, "UP:REF DN:PG BK:EXIT"));

    /* Same metrics but changed 100 Hz preset: previous 1 kHz PASS cannot
     * be reused as a plausible new PASS. */
    canvas = (Canvas){0};
    assert(!labmate_scope_reference_view_draw(
        &canvas, LabMateScopeReference100Hz50, result, &m));
    assert(canvas.count == 0U);

    /* Even with the same preset, altered measured data and stale error
     * fields must be rejected before any LCD pixels are painted. */
    LabMateScopeMetrics altered = m;
    altered.duty_permille = 495U; /* still PASS, but stale error=0 */
    canvas = (Canvas){0};
    assert(!labmate_scope_reference_view_draw(
        &canvas, LabMateScopeReference1kHz50, result, &altered));
    assert(canvas.count == 0U);
    altered.duty_permille = 450U; /* both the verdict and errors change */
    canvas = (Canvas){0};
    assert(!labmate_scope_reference_view_draw(
        &canvas, LabMateScopeReference1kHz50, result, &altered));
    assert(canvas.count == 0U);

    m.truncated = true;
    result = labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationComplete);
    assert(result.verdict == LabMateScopeVerdictInvalid);
    canvas = (Canvas){0};
    assert(labmate_scope_reference_view_draw(
        &canvas, LabMateScopeReference1kHz50, result, NULL));
    assert(!contains(&canvas, "PASS"));
    assert(contains(&canvas, "RESULT WAIT / INVALID"));
    assert(contains(&canvas, "NO VALID CAPTURE"));

    result = labmate_scope_tolerance_evaluate(
        &reference, NULL, LabMateScopeObservationNoSignalConfirmed);
    assert(result.verdict == LabMateScopeVerdictNoSignal);
    canvas = (Canvas){0};
    assert(labmate_scope_reference_view_draw(
        &canvas, LabMateScopeReference1kHz50, result, NULL));
    assert(contains(&canvas, "RESULT NO SIGNAL"));
    assert(!contains(&canvas, "PASS"));
}

static void test_busy_and_bad_data(void) {
    Canvas canvas = {0};
    LabMateScopeReference reference = {0};
    assert(labmate_scope_reference_preset(
        LabMateScopeReference100Hz50, &reference));
    LabMateScopeToleranceResult result = labmate_scope_tolerance_evaluate(
        &reference, NULL, LabMateScopeObservationBusy);
    assert(labmate_scope_reference_view_draw(
        &canvas, LabMateScopeReference100Hz50, result, NULL));
    assert(contains(&canvas, "BUSY"));
    assert(!contains(&canvas, "PASS"));

    assert(!labmate_scope_reference_view_draw(
        NULL, LabMateScopeReference100Hz50, result, NULL));
    assert(!labmate_scope_reference_view_draw(
        &canvas, (LabMateScopeReferencePreset)99, result, NULL));
    const LabMateScopeToleranceResult forged = {.verdict = LabMateScopeVerdictPass};
    assert(!labmate_scope_reference_view_draw(
        &canvas, LabMateScopeReference100Hz50, forged, NULL));
}

int main(void) {
    test_real_metrics_and_invalid_no_fake_pass();
    test_busy_and_bad_data();
    puts("scope reference Canvas host regression: PASS");
    return 0;
}
