FROM node:24-bookworm-slim

ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 HOME=/tmp NODE_ENV=production DEBUG=pw:browser
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/verify
COPY browser-tests/package.json browser-tests/package-lock.json ./
# Playwright is an exact, lockfile-pinned dev dependency of the trusted harness.
RUN npm ci --ignore-scripts --include=dev --no-audit --no-fund \
    && npm cache clean --force
COPY benchmarks/metroidvania_pilot/verify_browser.mjs ./verify_browser.mjs
USER 65534:65534
ENTRYPOINT ["node", "/opt/verify/verify_browser.mjs"]
