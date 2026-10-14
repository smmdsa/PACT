# Real browser smoke tests

The optional browser-test package pins Playwright 1.61.1 ; its bundled browser manifest selects the Chromium revision. It is separate from the standard-library compiler and the documentation parser. The dedicated workflow builds the checked game and docs, installs Chromium on an Ubuntu runner, then exercises the generated self-contained files in a real headless browser.

At desktop 1400×1000 and mobile-shaped 390×844 viewports, assertions cover semantic Markdown/table rendering without document overflow, a nonblank multi-color game canvas, actual start-button interaction, right movement from keyboard or pointer controls, paused state/tick stability, and absence of browser console/page errors. The touch-enabled context additionally verifies a jump from a touch tap. The test reads the existing `PACTGame` debug API for state assertions; movement inputs go through DOM events. It does not directly set guest state.

Screenshots and a result JSON record browser/version, viewport assertions and the generated game HTML hash. See [workflow runs](https://github.com/smmdsa/PACT/actions/workflows/browser.yml). The [first successful CI run](https://github.com/smmdsa/PACT/actions/runs/38524413016) passed all 11 assertions in Chromium 149.0.7827.55. The [frozen JSON report](../benchmarks/results/browser-chromium.json) records the tested HTML hash and CI provenance; it is a historical snapshot, not certification of every future build.

These are functional smoke checks, not a visual regression baseline or approval of art quality. A mobile viewport with touch emulation is not a real device. Firefox, WebKit, audio quality, gamepad behavior, accessibility auditing and the full browser-driven victory remain planned; Node's input-only victory is separately verified.

## Reproduce

```sh
python -m pip install -r docs/site-requirements.txt
python -m tools.build_site
npm ci --prefix browser-tests --ignore-scripts
browser-tests/node_modules/.bin/playwright install chromium
node browser-tests/smoke.mjs
```

Linux may need `playwright install --with-deps chromium`; the CI workflow uses that form. Runtime test files load through local file URLs, keeping the demo self-contained. Browser installation needs network access; the smoke test does not contact a model or external service.
