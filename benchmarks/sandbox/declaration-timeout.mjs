// Trusted fixture: stall after the worker has flushed its reference checkpoint.
await new Promise(resolve=>setTimeout(resolve,60000));
