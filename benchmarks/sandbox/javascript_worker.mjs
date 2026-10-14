// Runs only inside the configured container; never import candidate code on the host.
import { readFileSync } from 'node:fs';

const result = {
    execution_status: 'compile_error', initial_counter: null, cases: [], reset_case: null,
    runtime: { engine: 'node', node: process.version, v8: process.versions.v8 },
};

async function candidateScope(reset) {
    // Distinct module URLs re-evaluate top-level state for the reset observation.
    const scope = await import(`file:///tmp/candidate.mjs?reset=${reset}`);
    if (typeof scope.advance !== 'function' || !Array.isArray(scope.counter) || scope.counter.length !== 2)
        throw new Error('Expected exported advance and two-element counter');
    return scope;
}

function observe(scope, args) {
    let status = 'ok';
    try { scope.advance(...args); }
    catch (error) {
        if (error instanceof RangeError) status = 'bounds';
        else throw error;
    }
    return { args, status, counter: [...scope.counter] };
}

try {
    const request = JSON.parse(readFileSync(process.argv[2], 'utf8'));
    const scope = await candidateScope(false);
    result.initial_counter = [...scope.counter];
    result.execution_status = 'error';
    for (const args of request.cases) result.cases.push(observe(scope, args));
    result.reset_case = observe(await candidateScope(true), request.reset_args);
    result.execution_status = 'completed';
} catch (error) {
    console.error(String(error).slice(0, 512));
}
console.log(JSON.stringify(result));
