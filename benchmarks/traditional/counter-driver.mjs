import fs from 'node:fs';
import {advance, counter} from './counter.mjs';

for (const line of fs.readFileSync(0, 'utf8').trim().split('\n')) {
    const [index, amount] = line.split(' ').map(Number);
    let status = 'ok';
    try { advance(index, amount); }
    catch (error) {
        if (!(error instanceof RangeError)) throw error;
        status = 'bounds';
    }
    console.log(status, ...counter);
}
