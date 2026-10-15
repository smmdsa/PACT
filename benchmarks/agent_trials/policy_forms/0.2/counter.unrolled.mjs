export const counter = [2147483646, -2147483647];

export function advance(index, amount) {
    if (index < 0 || index >= counter.length) throw new RangeError("bounds");
    counter[index] = (counter[index] + amount) | 0;
    counter[index] = (counter[index] + amount) | 0;
    counter[index] = (counter[index] + amount) | 0;
    counter[index] = (counter[index] + amount) | 0;
}
