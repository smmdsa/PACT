counter = [2147483646, -2147483647]

def advance(index, amount):
    if not 0 <= index < len(counter):
        raise IndexError("bounds")
    counter[index] = (counter[index] + amount + 2**31) % 2**32 - 2**31
    counter[index] = (counter[index] + amount + 2**31) % 2**32 - 2**31
    counter[index] = (counter[index] + amount + 2**31) % 2**32 - 2**31
    counter[index] = (counter[index] + amount + 2**31) % 2**32 - 2**31
