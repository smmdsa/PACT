FROM python:3.12-slim
RUN mkdir -p /opt/runtime
COPY pact /opt/runtime/pact
COPY benchmarks/sandbox/worker.py /opt/worker.py
USER 65534:65534
ENTRYPOINT ["python3", "-I", "-B", "/opt/worker.py"]
