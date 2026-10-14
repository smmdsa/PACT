#define _POSIX_C_SOURCE 200809L
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

extern int32_t counter[2];
extern int advance(int32_t index, int32_t amount);

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    int32_t n = (int32_t)strtol(argv[1], NULL, 10);
    int32_t warmup = (int32_t)strtol(argv[2], NULL, 10);
    for (int32_t i = 0; i < warmup; i++) if (!advance(i % 2, 1)) return 3;
    counter[0] = 2147483646;
    counter[1] = -2147483647;
    struct timespec start, stop;
    if (clock_gettime(CLOCK_MONOTONIC, &start)) return 4;
    for (int32_t i = 0; i < n; i++) if (!advance(i % 2, 1)) return 3;
    if (clock_gettime(CLOCK_MONOTONIC, &stop)) return 4;
    int64_t elapsed = (int64_t)(stop.tv_sec - start.tv_sec) * 1000000000LL + stop.tv_nsec - start.tv_nsec;
    uint32_t checksum = 3u * (uint32_t)counter[0] + (uint32_t)counter[1];
    printf("{\"elapsed_ns\":%" PRId64 ",\"state\":[%" PRId32 ",%" PRId32 "],\"checksum\":%" PRIu32 ",\"pid\":%ld}\n",
           elapsed, counter[0], counter[1], checksum, (long)getpid());
    return 0;
}
