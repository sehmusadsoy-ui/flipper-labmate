/* Logger CSV tests on native host, without Flipper SDK. */
#include "labmate_logger_codec.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void check(const LabMateLogRow* sample, const char* expected) {
    char text[128] = {0};
    int n = labmate_logger_format_row(text, sizeof(text), sample);
    assert(n == (int)strlen(expected));
    assert(strcmp(text, expected) == 0);
    char short_buf[6] = {'X','X','X','X','X','Z'};
    n = labmate_logger_format_row(short_buf, 5U, sample);
    assert(n == (int)strlen(expected));
    assert(short_buf[4] == '\0' && short_buf[5] == 'Z');
}
int main(void) {
    uint16_t id=0;
    assert(labmate_logger_filename_id("log_0001.csv", &id) && id==1U);
    assert(labmate_logger_filename_id("log_9999.csv", &id) && id==9999U);
    assert(!labmate_logger_filename_id("log_0000.csv", &id));
    assert(!labmate_logger_filename_id("log_10000.csv", &id));
    assert(!labmate_logger_filename_id("Log_0001.csv", &id));
    assert(!labmate_logger_filename_id("log_0001.CSV", &id));
    assert(!labmate_logger_filename_id("log_01a1.csv", &id));
    assert(!labmate_logger_filename_id("log_0001.csv.bak", &id));
    assert(!labmate_logger_filename_id("log_0001.csv", NULL));
    assert(!labmate_logger_filename_id(NULL, &id));
    LabMateLogRow row={.source=LabMateLogRowFrequencyLow,.elapsed_ms=1000U,
       .valid=true,.frequency_millihz=1000125U};
    check(&row,"1000,FREQ,PC1,1,1000.125,,,,\n");
    row.source=LabMateLogRowFrequencyHigh;row.frequency_millihz=50000000U;
    check(&row,"1000,FREQ,PB3,1,50000.000,,,,\n");
    row.valid=false;check(&row,"1000,FREQ,PB3,0,0.000,,,,\n");
    row.source=LabMateLogRowPulse;row.valid=true;row.elapsed_ms=2500U;
    row.pulse_high_us=500U;row.pulse_low_us=500U;row.pulse_period_us=1000U;
    row.pulse_duty_permille=505U;
    check(&row,"2500,PULSE,PC1,1,,500,500,1000,50.5\n");
    row.valid=false;check(&row,"2500,PULSE,PC1,0,,0,0,0,0.0\n");
    char buf[64];row.source=(LabMateLogRowSource)99;
    assert(labmate_logger_format_row(buf,sizeof(buf),&row)<0);
    assert(labmate_logger_format_row(NULL,sizeof(buf),&row)<0);
    assert(labmate_logger_format_row(buf,0U,&row)<0);
    assert(labmate_logger_format_row(buf,sizeof(buf),NULL)<0);
    puts("v1.6.1 logger codec PASS");
    return 0;
}
