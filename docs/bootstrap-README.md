# PACT 0.0.1 — primera célula ejecutable

PACT explora un lenguaje cuyo cliente principal es un agente. Su fuente es un grafo con IDs estables y operaciones explícitas. Este prototipo compila realmente a WebAssembly y ejecuta el resultado con un host separado.

No se eligió una escritura exótica para aparentar ser alienígena. JSON transporta una estructura semántica: no existen variables por nombre, parser de expresiones textuales, clases ni sobrecargas en este núcleo. Las referencias son IDs y el orden significativo está en las aristas, no en las líneas del archivo.

Esto es una hipótesis medible de diseño. Todavía no demuestra que un agente sea más productivo que con lenguajes y herramientas existentes.

## Ejecutar el hola mundo

Requisitos: Python 3.10+ y Node 20+. No hay dependencias que descargar. Abrir una terminal en esta carpeta; en Windows puede usarse `python` en lugar de `python3`.

```sh
python3 -m pact check examples/hello.pact.json
python3 -m pact build examples/hello.pact.json -o build/hello.wasm
node host/run.mjs build/hello.wasm --allow stdout
```

Salida exacta:

```text
hola mundo, from an alien language
```

El ZIP incluye `build/hello.wasm` y su manifiesto; se pueden ejecutar directamente mediante el tercer comando. El programa compilado no necesita Python, ni un modelo, ni conexión de red.

Interpretación de referencia y suite de pruebas:

```sh
python3 -m pact interpret examples/hello.pact.json --allow stdout
python3 -m unittest discover -v
```

Sin `--allow stdout`, interpretar o ejecutar devuelve `CAPABILITY_DENIED` y no emite el saludo. `--max-output N` reduce el presupuesto del host, medido en bytes UTF-8, antes de cualquier salida.

## La fuente alienígena

```json
{
  "format": "pact.graph/0.0.1",
  "responsibility": "demo.alien_greeting",
  "entry": "e0",
  "effects": ["stdout"],
  "nodes": [
    {"id": "v0", "op": "utf8.literal", "value": "hola mundo, "},
    {"id": "v1", "op": "utf8.literal", "value": "from an alien language\n"},
    {"id": "v2", "op": "utf8.concat", "args": ["v0", "v1"]},
    {"id": "e0", "op": "stdout.emit", "args": ["v2"]}
  ],
  "contracts": [
    {"id": "c0", "op": "stdout.exact", "value": "hola mundo, from an alien language\n"}
  ]
}
```

El array `nodes` puede reordenarse sin alterar el artefacto. Los argumentos de `utf8.concat` o `effect.sequence` sí tienen orden. Los datos puros pueden compartirse; un nodo con efectos no puede ejecutarse dos veces.

`responsibility` es un ID declarativo. No prueba que el naming o la responsabilidad sean correctos. Esa evaluación semántica sigue requiriendo acuerdos, contratos y revisión.

## Reglas implementadas

| Operación | Entrada | Resultado | Efecto |
| --- | --- | --- | --- |
| `utf8.literal` | Texto válido | `Utf8` | Ninguno |
| `utf8.concat` | 1–64 referencias `Utf8` | `Utf8` | Ninguno |
| `stdout.emit` | Una referencia `Utf8` | `Unit` | `stdout` |
| `effect.sequence` | 1–64 referencias `Unit` | `Unit` | Efectos de sus hijos, en orden |

El grafo debe ser acíclico, completamente alcanzable y de tipos válidos. Se rechazan campos desconocidos, IDs repetidos, referencias inexistentes, claves JSON duplicadas y efectos no declarados. Máximo 256 nodos, 16 KiB de texto/salida y 1 MiB de fuente.

Los contratos `stdout.exact` se evalúan contra la salida completa antes de generar el artefacto. Esto es evaluación exacta de un programa estático sin entradas, no un sistema general de demostración formal ni un runner de tests escritos en PACT.

Ejemplo de diagnóstico para una referencia inexistente:

```json
{"status":"rejected","code":"REFERENCE_MISSING","message":"Reference missing does not exist.","node":"e0"}
```

## Compilación y host

El compilador evalúa la composición constante y produce memoria de texto más una función Wasm `main`. Esta llama al único import permitido, `pact.emit_utf8`. La memoria es una página de 64 KiB, con máximo fijo; no hay loops, crecimiento de memoria, start section ni imports de disco/red.

Un manifiesto acompaña al módulo. Contiene plan, tipos inferidos, evidencia de contratos, hash canónico de fuente y hash de bytecode. El host comprueba límites, forma del manifiesto y hash, y además reconstruye independientemente el único perfil permitido de bytecode. Rechaza diferencias antes de instanciar. Actualizar solo el hash no permite introducir un módulo arbitrario o un loop infinito.

La duplicación limitada del emisor entre Python y JavaScript es intencional: el host comprueba el perfil de ejecución sin importar el compilador. Su igualdad se comprueba con tests de ejecución, incluidos Unicode, múltiples rangos de LEB128 y el límite de texto.

**Límites de seguridad:** los hashes identifican contenido y detectan desacuerdos; no autentican autoría. Una persona que puede cambiar todo el paquete puede crear otro programa permitido y otras declaraciones de evidencia. El host comprueba estructura/perfil y no revalida contratos de una fuente que no se le entrega. El permiso stdout autoriza el texto del paquete seleccionado, no su significado. No es un sandbox general de Wasm ni una herramienta para ejecutar cualquier binario descargado.

La toolchain y el host leen las rutas seleccionadas por quien los ejecuta y escriben los resultados solicitados. El guest no recibe esa autoridad. El host no concede acceso a archivos, red o procesos al programa.

Las escrituras de `.wasm` y manifiesto son atómicas individualmente, no como pareja. Un fallo o interrupción entre ambas puede dejar una pareja inconsistente; el host la rechaza. La distribución debe incluir ambos archivos de la misma compilación.

## Estructura del proyecto

| Archivo | Responsabilidad |
| --- | --- |
| `pact/schema.py` | Esquema cerrado y límites |
| `pact/graph.py` | Referencias, tipos, evaluación y contratos |
| `pact/diagnostics.py` | Rechazos estructurados |
| `pact/wasm.py` | Codificación binaria WebAssembly |
| `pact/__main__.py` | CLI y escritura de artefactos |
| `host/profile.mjs` | Comprobador independiente del perfil de artefactos |
| `host/run.mjs` | Lectura acotada y capacidad stdout |
| `examples/hello.pact.json` | Primer programa PACT |
| `tests/` | Pruebas reales del analizador, compilador y host |
| `docs/` | Bosquejo, especificación del núcleo, plan y evidencia |
| `build/` | Hola mundo compilado y salida verificada |

## Qué sigue

1. Comparar construcción, edición y reparación de este grafo con una línea de base convencional.
2. Agregar tipos numéricos, inputs, decisiones y contratos limitados para `decide_jump`.
3. Agregar assets tipados: paletas, tiles 8×8, frames, animaciones y atlas.
4. Implementar host gráfico y una habitación con movimiento, salto y colisiones.
5. Ampliar al juego de plataformas de referencia después de validar esos cortes.

Los cambios estructurados transaccionales, contratos protegidos por permisos de edición y publicación firmada siguen siendo diseño futuro. El nombre PACT es provisional; no se comprobó disponibilidad.

Pruebas actuales realizadas en Linux, Python 3.12 y Node 24. No se ejecutaron en Windows, macOS, móviles o navegador. El núcleo Wasm es independiente de Python; los adaptadores y las plataformas todavía requieren su propia validación.

Formato Wasm consultado: https://webassembly.github.io/spec/core/binary/modules.html

API JavaScript consultada: https://webassembly.github.io/spec/js-api/index.html
