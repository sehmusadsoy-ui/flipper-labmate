#pragma once
#include <stdbool.h>

typedef struct Expansion Expansion;
bool expansion_is_connected(Expansion* expansion);
void expansion_disable(Expansion* expansion);
void expansion_enable(Expansion* expansion);
