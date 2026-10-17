#pragma once

#include <stdbool.h>

/* Shared LabMate-owned communication hardware policy.
 * This protects only the local LabMate app. It is NOT a firmware-wide GPIO
 * mutex or a substitute for HAL-acquire/release ownership.
 */
typedef enum {
    LabMateCommNone = 0,
    LabMateCommI2c3, /* PC0 SCL and PC1 SDA, 3.3 V only */
    LabMateCommOneWirePa4, /* standalone 1-Wire DQ, non-PB14, 3.3 V */
} LabMateCommOwner;

typedef struct {
    bool capture_active;      /* PC0/PC1/PB3/other capture owner */
    bool gpio_monitor_active; /* polling GPIO also changes pin state */
    bool pwm_active;          /* conservatively exclude TIM1 PA7 */
    bool uart_active;         /* conservatively exclude USART */
    bool logger_active;       /* capture and ongoing SD operation */
} LabMateCommBusy;

/* Reject unknown owner, second claim and active legacy instruments. */
bool labmate_comm_local_can_claim(
    LabMateCommOwner current, LabMateCommOwner requested, LabMateCommBusy busy);

/* Returns true only on successful application-local claim. */
bool labmate_comm_local_claim(
    LabMateCommOwner* current, LabMateCommOwner requested, LabMateCommBusy busy);

/* A non-owner STOP must not steal or release another owner's resources. */
bool labmate_comm_local_release(
    LabMateCommOwner* current, LabMateCommOwner stopping);
