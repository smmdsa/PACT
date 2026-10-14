# Verificación PACT 0.0.1

Entorno: Linux, Python 3.12.14, Node v24.19.0.

- Suite completa: Ran 38 tests in 4.737s; resultado OK.
- CLI check: aceptó el grafo y produjo tipos/evidencia estructurados.
- Build público: generó WebAssembly de 123 bytes y manifiesto.
- Ejecución Wasm y evaluación de referencia: salida idéntica, incluidos los bytes de nueva línea.
- Sin capacidad stdout: rechazo CAPABILITY_DENIED, sin salida.
- Revisión independiente: sin hallazgos importantes en el código de producción.
- SHA-256 hello.wasm: `9abf5d8ec784809abf64e90264bd3b8218d62c847c8e3f67bbe8b3b9fb0eef06`.

Salida ejecutada:

```text
hola mundo, from an alien language
```

La suite incluye grafos inválidos, efectos compartidos, contratos incumplidos, Unicode y presupuestos, bytecode/manifiestos alterados y rechazo de un módulo válido con loop infinito.

Esta es evaluación de programas estáticos, no verificación formal general. La prueba de mayor comodidad/productividad agentic-first queda pendiente. No se probaron otros sistemas operativos.

Los resultados y logs se incluyen en `build/`.
