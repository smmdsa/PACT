FROM node:24-bookworm-slim AS javascript_runtime
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 gcc libc6-dev && rm -rf /var/lib/apt/lists/* && mkdir -p /opt/runtime
COPY --from=javascript_runtime /usr/local/bin/node /usr/local/bin/node
COPY pact /opt/runtime/pact
COPY benchmarks/sandbox/worker.py /opt/worker.py
COPY benchmarks/sandbox/javascript_worker.mjs /opt/javascript_worker.mjs
COPY benchmarks/sandbox/c_worker.py /opt/runtime/c_worker.py
COPY benchmarks/sandbox/c_driver.c /opt/c_driver.c
USER 65534:65534
ENTRYPOINT ["python3", "-I", "-B", "/opt/worker.py"]
