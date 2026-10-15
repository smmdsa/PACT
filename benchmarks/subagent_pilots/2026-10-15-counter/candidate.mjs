export const counter = [2147483646, -2147483647];

export function advance(index, amount) {
    if (index < 0 || index >= counter.length) throw new RangeError("bounds");
    for (let i = 0; i < 4; i++) counter[index] = (counter[index] + amount) | 0;
}
