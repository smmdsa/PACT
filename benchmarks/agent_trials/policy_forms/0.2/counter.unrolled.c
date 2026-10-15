#include <stdint.h>

int32_t counter[2] = {2147483646, -2147483647};

int advance(int32_t index, int32_t amount) {
    if (index < 0 || index >= 2) return 0;
    {
        uint32_t sum = (uint32_t)counter[index] + (uint32_t)amount;
        counter[index] = sum <= INT32_MAX ? (int32_t)sum : (int32_t)((int64_t)sum - 4294967296LL);
    }
    {
        uint32_t sum = (uint32_t)counter[index] + (uint32_t)amount;
        counter[index] = sum <= INT32_MAX ? (int32_t)sum : (int32_t)((int64_t)sum - 4294967296LL);
    }
    {
        uint32_t sum = (uint32_t)counter[index] + (uint32_t)amount;
        counter[index] = sum <= INT32_MAX ? (int32_t)sum : (int32_t)((int64_t)sum - 4294967296LL);
    }
    {
        uint32_t sum = (uint32_t)counter[index] + (uint32_t)amount;
        counter[index] = sum <= INT32_MAX ? (int32_t)sum : (int32_t)((int64_t)sum - 4294967296LL);
    }
    return 1;
}
