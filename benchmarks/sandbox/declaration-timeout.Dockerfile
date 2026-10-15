# Authored fault-injection image, used only by CI to stall the trusted test host.
ARG RUNTIME_IMAGE=pact-counter-verifier
FROM ${RUNTIME_IMAGE}
COPY benchmarks/sandbox/declaration-timeout.mjs /opt/runtime/tools/check_module.mjs
