#include <stdio.h>
#include <inttypes.h>

extern int32_t counter[2];
int advance(int32_t index, int32_t amount);

int main(void) {
    int32_t index, amount;
    while (scanf("%" SCNd32 " %" SCNd32, &index, &amount) == 2) {
        const char *status = advance(index, amount) ? "ok" : "bounds";
        printf("%s %" PRId32 " %" PRId32 "\n", status, counter[0], counter[1]);
    }
    return 0;
}
