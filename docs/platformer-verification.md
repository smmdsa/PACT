# PACT 0.1 — verificación final

- Ran 75 tests in 5.335s; resultado OK.
- Build público ejecutó los dos tests declarados en la fuente y produjo Wasm de 28940 bytes.
- Partida completa con inputs, sin inyección de estado de gameplay: victoria en 1216 ticks, 3 cristales, boss HP 0, bandera activa y 2 vidas.
- VM Python independiente y Wasm real coinciden para la secuencia de inputs de regresión.
- Host con Wasm/Canvas nativos y adaptador DOM mínimo: inicio, teclado, touch, derrota, reinicio y replay de victoria comprobados.
- Assets: paleta simbólica y tiles 8×8 compilados dentro de memoria. Sin imágenes externas.
- Scripts embebidos: sintaxis comprobada; ninguna dependencia externa de script/imagen.
- Revisión independiente: cinco hallazgos importantes corregidos con tests de regresión.
- Publicación privada: confirmada por resultado nativo succeeded.

URL: https://alien-harvest-pact-lab.mrtiagosan.chatgpt.site

SHA-256 Wasm: `d3d6713334cce5ad60fb463b40f9c833036431ea06052039707525e9cdd3ec76`

SHA-256 HTML: `30ae841799df19652c0000ad8ba44e9c9cf36359c9c98309f9aedfad7782fee4`

Entorno: Linux, Python 3.12.14, Node v24.19.0.

## Límite de QA

No hubo prueba en navegador real: faltaba Chromium y el entorno no tenía el plugin de control gestionado. La prueba del host utiliza un adaptador DOM mínimo, no Chromium. No se verificaron CSS responsive, audio audible, móviles ni otros sistemas operativos. El Canvas real sí ejecutó el dibujo del juego. No se presenta este prototipo como demostración de productividad agentic-first ni como verificación formal universal.

Logs, replay y resultados completos en build/.
