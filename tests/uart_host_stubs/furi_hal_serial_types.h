#pragma once
#include <stdint.h>

typedef struct FuriHalSerialHandle FuriHalSerialHandle;
typedef uint32_t FuriHalSerialRxEvent;

enum {
    FuriHalSerialRxEventData = 1U << 0,
    FuriHalSerialRxEventFrameError = 1U << 1,
    FuriHalSerialRxEventNoiseError = 1U << 2,
    FuriHalSerialRxEventOverrunError = 1U << 3,
    FuriHalSerialRxEventParityError = 1U << 4,
};

typedef enum {
    FuriHalSerialIdUsart = 0
} FuriHalSerialId;

typedef enum {
    FuriHalSerialDataBits8 = 8
} FuriHalSerialDataBits;
typedef enum {
    FuriHalSerialParityNone = 0
} FuriHalSerialParity;
typedef enum {
    FuriHalSerialStopBits1 = 1
} FuriHalSerialStopBits;
