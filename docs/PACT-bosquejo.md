# PACT — bosquejo de lenguaje agentic-first

Fecha: 13 de octubre de 2026. Revisión conceptual: 0.2. Estado: propuesta para discutir; no es una especificación aprobada ni existe todavía un compilador. Nombre provisional, sin comprobación de disponibilidad. Esta revisión incorpora juegos como dominio inicial, assets internos y contratos de responsabilidad.

## Propósito y criterio de éxito

Una persona y un agente acuerdan resultados, restricciones y ejemplos. El agente construye un programa estructurado. Herramientas independientes comprueban propiedades del programa y un runtime controla sus efectos. La persona conserva una representación legible, los contraejemplos y el historial de decisiones.

Agentic-first significa optimizar construcción, modificación, consulta y diagnóstico para agentes. No significa ocultar el programa a las personas. Una representación compacta puede reducir ambigüedad y también empeorar el consumo de contexto; hay que medirlo.

Hipótesis: contratos explícitos, efectos visibles y cambios estructurados reducen errores y ciclos de reparación frente a un lenguaje convencional con herramientas equivalentes. El éxito se medirá, no se asumirá.

## Alternativas

| Camino | Ventaja | Costo o límite |
| --- | --- | --- |
| Capa de contratos y herramientas sobre Rust o TypeScript | Permite medir pronto el valor del flujo agentic-first | Conserva semántica y complejidad del lenguaje anfitrión |
| Lenguaje pequeño con representación estructurada propia | Permite controlar reglas, diagnósticos y ejecución | Hay que implementar y mantener lenguaje, verificador y herramientas |
| Lenguaje general completo y backend nativo desde el inicio | Máxima libertad de diseño | Demasiados frentes antes de demostrar una ventaja |

Recomendación: investigar un lenguaje pequeño, con una línea de base fuerte sobre un lenguaje existente. Posponer un lenguaje general y la compilación nativa directa.

## Tres responsabilidades separadas

1. **Acuerdo:** intención en lenguaje natural, supuestos, entradas, salidas, ejemplos y propiedades formales. El texto natural orienta; no es semántica ejecutable.
2. **Programa:** funciones, tipos, flujo de datos y efectos expresados mediante un AST tipado. El agente puede proponer implementaciones sin editar el acuerdo por defecto.
3. **Política de ejecución:** capacidades, límites y destinos autorizados, definidos por el anfitrión. El programa declara necesidades; no puede concederse autoridad.

Un mismo programa puede ejecutarse con políticas distintas. Una firma identifica quién autorizó un artefacto, pero no demuestra que sea correcto.

La compilación no necesita consultar un modelo. Debe funcionar sin conexión con las dependencias fijadas y producir diagnósticos reproducibles.

## Representación y edición

La fuente canónica inicial sería un AST versionado en JSON, separado en módulos pequeños. JSON es el contenedor; la semántica está en los tipos de nodos y las reglas del lenguaje. No se aceptan claves duplicadas, referencias inexistentes o versiones desconocidas.

Cada entidad tendría un ID estable. Los hashes de contenido identificarían revisiones, no reemplazarían esos IDs. El agente enviaría operaciones como reemplazar una expresión, agregar una función o conectar un argumento, con una revisión esperada para detectar conflictos.

Una transacción de edición se valida antes de hacerse efectiva. No se comparte un programa parcialmente actualizado. Renombrar una función no rompe sus referencias internas por nombre.

Una vista textual legible se genera desde la fuente canónica. No habrá dos archivos editables que puedan contradecirse. El formato textual podría convertirse después en otro frontend mediante reglas de ida y vuelta explícitas.

Los diagnósticos tendrán código, ID del nodo, restricción incumplida, datos del contraejemplo cuando estén disponibles y referencias al contrato. Las reparaciones sugeridas no se aplican automáticamente.

## Núcleo inicial

- Enteros de tamaño fijo con overflow explícito; booleanos, registros, variantes, listas acotadas y funciones puras.
- Tipos nominales para distinguir cantidades como energía, vidas o dinero, aunque compartan representación numérica.
- Ausencia de valores mediante `Option`; fallos recuperables mediante `Result`. No hay `null` universal ni coerciones silenciosas.
- Valores inmutables por defecto. Una transición recibe un estado y devuelve otro.
- Evaluación secuencial con orden definido. Sin estado global mutable, hilos ni reflexión en v0.1.
- Sin recursión y con iteraciones acotadas en v0.1. Esta restricción reduce expresividad y facilita analizar terminación del núcleo; no demuestra que un servicio externo termine.
- Sin floating point en el núcleo inicial. Si se añade, se especificarán redondeo, NaN, infinito y criterios de comparación/reproducibilidad.
- Reglas explícitas para serialización y orden de colecciones. Las cadenas y el procesamiento Unicode quedan para una ampliación, salvo etiquetas no ejecutables.

No se promete verificar cualquier programa. Un primer comprobador podría resolver rangos, operaciones aritméticas simples y algunas condiciones antes/después. Las propiedades fuera del fragmento soportado quedan identificadas como pendientes o se rechazan según el perfil.

## Contratos y evidencias

Cada operación pública declara entradas, salida, precondiciones, postcondiciones y efectos. Los ejemplos ayudan a detectar malentendidos; no sustituyen propiedades generales.

La evidencia se registra por propiedad:

| Estado | Significado |
| --- | --- |
| Demostrada | Verificada dentro del modelo formal y sus supuestos, con herramienta y versión identificadas |
| Probada con tests | Se ejecutaron casos concretos; no es una demostración universal |
| Asumida | Depende de una condición externa o una frontera de confianza declarada |
| Pendiente | No hay evidencia suficiente o el comprobador no resolvió la obligación |

Un timeout del solver nunca equivale a éxito. Una propiedad requerida por el perfil de publicación bloquea ese perfil si falta la evidencia exigida. Durante desarrollo se permiten programas incompletos, siempre identificados como tales.

No se etiqueta el programa entero como seguro porque una postcondición fue demostrada. Compilador, comprobador, runtime y adaptadores pertenecen a la base de confianza. Un defecto en cualquiera puede invalidar garantías.

## Ejemplo conceptual

Esta es una vista de diseño, no sintaxis implementada:

```text
operation consume_energy
  inputs
    available: Energy<0..100>
    cost: Energy<0..100>
  output
    Success { remaining: Energy<0..100> }
    | Insufficient { unchanged: Energy<0..100> }
  effects: none

  ensures
    available >= cost => Success(available - cost)
    available < cost  => Insufficient(available)

  implementation
    if available >= cost
      Success(available - cost)
    else
      Insufficient(available)

  examples
    (10, 3) => Success(7)
    (2, 3)  => Insufficient(2)
    (0, 0)  => Success(0)
```

La decisión importante aparece en el contrato: energía insuficiente rechaza la operación y conserva el valor. Si queremos gasto parcial o prohibir costo cero, debemos modificar el acuerdo de manera visible.

Si una implementación usa `available + cost`, el comprobador debe detectar el desacuerdo para el fragmento soportado. El agente no puede borrar la condición para hacer que la comprobación pase.

## Efectos y seguridad

El núcleo puro no tiene acceso a disco, red, reloj, aleatoriedad, secretos o procesos. Esas operaciones requieren interfaces del anfitrión.

Las declaraciones de efectos describen comportamiento posible; las capacidades representan autoridad efectiva. Marcar una función como `network` no le da acceso a Internet. El runtime concede handles opacos y controla cada operación.

Las políticas pueden restringir directorios, lectura/escritura, destinos de red, operaciones, presupuesto, tamaños de respuesta y duración. Una red restringida por dominio exige validar también redirecciones y la resolución de destinos en el adaptador; una etiqueta en el código no alcanza.

Los secretos se obtienen mediante handles del anfitrión y se evitan en logs. Para v0.1 se excluye red y gestión de secretos. El aislamiento no impide por sí solo que un programa exfiltre información si se le conceden lectura sensible y un canal de salida.

El runtime limita memoria, instrucciones, salida y duración. El agotamiento devuelve un fallo identificado. Reloj y aleatoriedad, cuando existan, se inyectan y se registran para replay. Determinismo solo se promete bajo entradas y efectos registrados equivalentes.

Texto recibido de Internet es dato, nunca autoridad para cambiar políticas. Esto requiere también controles en el agente y sus herramientas de edición; el lenguaje aislado no resuelve prompt injection.

Publicar un artefacto vincula por hashes programa, contrato, política y evidencia. Una modificación invalida las evidencias afectadas. El host debe ejecutar exactamente el artefacto comprobado. Los cambios del acuerdo o los permisos siguen un canal distinto de los cambios de implementación.

No se promete rollback de correos, pagos u otras acciones externas. Los adaptadores futuros definirán idempotencia, reintentos y compensaciones por operación.

## Compilación propuesta

1. Validar esquema y referencias del AST.
2. Resolver módulos y tipos, con versiones fijadas.
3. Comprobar efectos y necesidades de capacidades.
4. Comprobar los contratos soportados y producir evidencias por propiedad.
5. Bajar a una representación intermedia sencilla y luego generar WebAssembly.
6. Empaquetar artefacto, interfaces, contratos, versiones y evidencia.

Un intérprete de referencia, con las mismas reglas semánticas, precedería al backend compilado. Compararíamos ambos sobre casos y programas generados. Esa comparación detecta errores; no demuestra equivalencia completa del compilador.

Rust es una opción para implementar las herramientas. El primer backend puede emitir Wasm directamente desde una IR pequeña; no necesitamos desarrollar un optimizador general ni integrar LLVM al comienzo. La ruta concreta se decidirá tras fijar el núcleo.

## Compatibilidad

WebAssembly es el destino portátil inicial. El núcleo puro se ejecutaría dentro de un runtime compatible. El acceso al sistema usaría adaptadores versionados; WASI es un candidato para interfaces estándar.

| Destino | Ruta propuesta | Condición |
| --- | --- | --- |
| Windows, Linux y macOS | Wasm dentro de runtime de escritorio | Distribuir y probar runtime, arquitectura e interfaces elegidas |
| Navegador | Wasm con anfitrión JavaScript | Implementar adaptadores; no asumir WASI integrado |
| Android e iOS | Runtime embebido y adaptadores de la aplicación | Comprobar políticas, modo de ejecución e integración en cada plataforma |
| Sistemas pequeños o no habituales | Perfil reducido o backend adicional | Solo declarar soporte tras pruebas de conformidad |

Portabilidad del núcleo no implica portabilidad de GUI, GPU, drivers o todas las capacidades del sistema. Un programa que necesita una capacidad ausente debe rechazarse antes de ejecutarse; no degradar su contrato silenciosamente.

Una ruta nativa posterior podría reutilizar LLVM u otro backend, pero sería un trabajo nuevo de preservación semántica, aislamiento y conformidad. No afirmaríamos compatibilidad con todos los sistemas operativos.

## Primer experimento y evaluación

v0.1 se limita a funciones puras, tipos básicos y nominales, variantes, contratos numéricos simples, diagnósticos estructurados y modificaciones transaccionales. Después: intérprete de referencia, backend Wasm y host con una capacidad pequeña, como escribir un resultado en un directorio autorizado.

No entran inicialmente red, agente embebido, concurrencia, paquetes públicos, GUI, compilación nativa ni inferencia de especificaciones generales desde texto.

Evaluar las mismas tareas y modelos en PACT y en una línea de base convencional con contratos, tests y herramientas comparables. Medir resultados correctos, regresiones, permisos excedidos, tokens, latencia, ciclos de reparación y esfuerzo de revisión humana. Reservar tests externos que el agente no pueda debilitar.

Casos iniciales: consumo de energía, movimiento en una grilla y combinación de inventario. Introducir bugs deliberados en implementación y contratos; los segundos requieren revisión del acuerdo y ejemplos externos, no solo verificar la implementación contra ellos.

Si una capa sobre un lenguaje existente ofrece el mismo beneficio con menos costo, ese será un resultado válido. La novedad debe estar en una mejora medida, no en tener extensión propia.

## Dominio elegido: juego de plataformas como prueba del lenguaje

El usuario eligió juegos y propuso un objetivo de complejidad media/alta inspirado en Mario Bros. 2 de NES. Para este bosquejo se asume la variante occidental, con interacción de levantar/lanzar objetos. Esta interpretación sigue siendo corregible. Se proponen personajes, niveles y assets originales; la referencia define mecánicas y escala, no un requisito de copiar contenido.

Es una meta de validación, no el primer hito completo. El lenguaje mínimo se prueba antes de construir todo el juego. La biblioteca de juego tampoco formará parte del núcleo obligatorio: PACT puede seguir sirviendo a otros dominios.

### Assets internos tipados

Separar `Tile<8,8>`, `SpriteFrame` y `Atlas`. Un frame puede consistir en un tile 8×8 o componerse de varios, por ejemplo para personajes mayores. El atlas se genera desde declaraciones de assets, preferentemente durante el build, y se incluye en el artefacto. No requiere imágenes externas ni se regenera cada tick.

La API semántica de un pixel sería `Transparent | ColorKey<Palette>`. Si conservamos el formato propuesto por el usuario, el serializador representa transparencia como -1 y colores mediante índices; esos enteros no aparecen como convenciones sueltas en lógica de gameplay. Una biblioteca de paletas contiene nombres; la definición de cada paleta sí debe especificar valores de color concretos. Los nombres no pueden eliminar esos valores necesarios.

Ejemplo de vista declarativa, no sintaxis implementada:

```text
palette HeroPalette
  Ink   = rgb8(24, 24, 40)
  Skin  = rgb8(248, 184, 136)
  Cloth = rgb8(72, 104, 216)

tile HeroIdle: Tile<8,8,HeroPalette>
  symbols
    . = Transparent
    I = HeroPalette.Ink
    S = HeroPalette.Skin
    B = HeroPalette.Cloth
  pixels
    "........"
    "..IIII.."
    "..ISSS.."
    "..ISSI.."
    "...BB..."
    "..BBBB.."
    "..B..B.."
    "..I..I.."
```

El build comprueba ocho filas y ocho celdas, símbolos válidos, pertenencia a la paleta, referencias, pivotes dentro del frame y composición de tiles. Una animación exige frames existentes y duraciones positivas expresadas en ticks. Restricciones de paleta adicionales pertenecen al perfil de assets y no se imponen a todo el lenguaje.

La forma visual no se puede validar solamente con esos checks. Una preview permite revisar legibilidad y consistencia del arte. Las colisiones se definen como datos independientes, no se deducen del alfa de un sprite.

### La responsabilidad debe tener semántica explícita

Un nombre es una etiqueta, no una prueba del comportamiento. No se promete descubrir automáticamente una única responsabilidad semántica a partir de nombres o tests.

Cada operación exportada declara un identificador de propósito estable, entradas/salidas estrechas, efectos, propiedades y evidencias requeridas. Los IDs son únicos; los nombres son únicos dentro de un namespace. Dos helpers pueden contribuir al mismo propósito sin ser necesariamente duplicación indebida.

Ejemplo de contrato:

```text
operation decide_jump
  responsibility: player.jump_decision
  inputs
    grounded: Bool
    jump_pressed: Bool
    current_velocity: VerticalVelocity
    jump_impulse: VerticalVelocity
  output: JumpDecision { velocity: VerticalVelocity, started: Bool }
  effects: none

  ensures
    grounded and jump_pressed
      => velocity == jump_impulse and started == true
    otherwise
      => velocity == current_velocity and started == false
```

No recibe un `GameState` enorme ni tiene capacidad para escribir vidas, inventario o audio. Devuelve una decisión específica que un orquestador integra. Un orquestador puede coordinar varias operaciones si su responsabilidad declarada es avanzar un tick; responsabilidad única no significa una sola línea o una sola llamada.

Reglas automáticas: referencias y símbolos sin ambigüedad; efectos inferidos dentro de los declarados; transiciones restringidas a su dominio; propiedades comprobables; dependencias de módulos permitidas. Las entradas/salidas por sí solas no demuestran un único propósito semántico. Una evaluación de nombres, cohesión o responsabilidades superpuestas sería un diagnóstico de revisión, no una garantía del compilador.

No se permiten propósitos vacíos como `misc` o `do_stuff` en interfaces publicadas. El registro exige descripción de outcome y vínculo a requisitos. Un nombre aceptable tampoco basta para publicar una operación sin contrato.

### Tests como condición de build

`check` valida estructura, tipos y efectos; `verify` comprueba contratos soportados; `test` ejecuta pruebas en aislamiento; `build --profile=release` exige la política de evidencia del proyecto. Estos comandos son parte de la toolchain propuesta, no herramientas existentes.

El comprobador puede exigir que una operación pública con comportamiento relevante tenga evidencias vinculadas por ID. El runner verifica resultados; la mera existencia de un método llamado `test_*` no basta. Se requieren aserciones ejecutadas y vinculación a propiedades, con límites de recursos y sin capacidades externas por defecto.

Helpers triviales y propiedades ya demostradas pueden estar cubiertos mediante una política explícita; no se exige un test redundante por cada función. Un test de formato de sprite tampoco reemplaza comprobar si un salto o una colisión son correctos.

Ejemplos de pruebas de juego:

- Saltar desde el suelo inicia la velocidad acordada; intentar saltar en el aire no inicia otro salto.
- Recibir daño durante invulnerabilidad no descuenta otra vida.
- Levantar un objeto transfiere su ownership, sin duplicarlo en el mundo.
- Lanzarlo lo libera y aplica el impulso de configuración.
- Cambiar de animación preserva la hitbox salvo una regla explícita.
- Misma entrada, estado inicial, semilla y cantidad de ticks producen el mismo estado serializado.
- Colisiones en bordes y a velocidad máxima no atraviesan paredes para el perfil físico especificado.

Pruebas generativas exploran muchas entradas y mutation testing comprueba si errores deliberados son detectados. Ninguna proporciona una prueba universal. Parte de los criterios de aceptación debe quedar fuera del alcance de edición del agente que implementa, para evitar que código y tests compartan el mismo malentendido.

### Ejecución determinista del juego

La simulación recibe `State × Input × Tick` y devuelve estado/eventos mediante operaciones puras. El host llama al tick, captura inputs y presenta el resultado; el programa no necesita recursión ni un bucle interno infinito.

Propuesta inicial: 60 ticks por segundo, X positiva a la derecha, Y positiva hacia abajo, posiciones y velocidades con unidades explícitas y aritmética de punto fijo. Se especificarán escala, redondeo y overflow antes de implementar. El render puede interpolar sin modificar la simulación. El ritmo de presentación no define el paso físico.

La configuración nombra velocidad, gravedad, impulso e invulnerabilidad. Un literal de color dentro de una paleta o una constante con unidad explícita es válido; un número sin propósito conocido en el gameplay se diagnostica. No se prohíben indiscriminadamente todos los números.

El host ofrece capacidades estrechas para recibir input, dibujar y reproducir audio. Los adaptadores gráficos y de sonido son parte de la base de confianza; la semántica no depende de una API gráfica concreta. El núcleo inicial sin GUI del bosquejo anterior se mantiene como primer hito, y el host gráfico es un hito posterior.

### Arquitectura del juego de referencia

| Módulo | Responsabilidad | Restricción importante |
| --- | --- | --- |
| Assets | Paletas, tiles, frames, animaciones y atlas | Sin dependencia de gameplay |
| Level | Geometría, objetos de nivel y spawns | Datos acotados y referencias válidas |
| Movement | Proponer movimiento y resolver colisiones | No administrar vidas ni inventario |
| Interaction | Levantar, sostener y lanzar objetos | Ownership explícito |
| Combat | Daño, invulnerabilidad y derrota | Eventos y cambios de dominio declarados |
| Enemies | Decisiones por estado | Entradas limitadas al contexto necesario |
| Progress | Checkpoints, puertas y victoria | Transiciones de estado válidas |
| Presentation | Comandos de dibujo y sonido | No escribir estado de simulación |
| GameTick | Coordinar el avance de la simulación | Orden documentado y replay verificable |

La implementación concreta puede repartir proponer movimiento y resolver colisiones en operaciones separadas dentro de Movement. Los presupuestos de entidades, tamaños de mapas y comandos de dibujo son explícitos. Si se exceden, el programa devuelve un fallo definido o aplica una política acordada; no descarta entidades silenciosamente.

### Hitos propuestos, todavía sin plan de implementación aprobado

1. Núcleo del lenguaje con `decide_jump`, verificación limitada y diagnósticos estructurados.
2. Tiles, paletas, compilación de atlas y preview de assets.
3. Host gráfico y una habitación con movimiento, salto y colisiones.
4. Slice jugable: levantar/lanzar, dos enemigos, daño e invulnerabilidad, checkpoint, puerta, mini jefe, victoria/derrota y reinicio.
5. Ampliar a más niveles después de comparar productividad, errores y reparación contra la línea de base.

La complejidad media/alta está en la meta de validación; no se impone toda al primer compilador. Los sprites y el motor son la prueba del lenguaje, no una razón para incrustar todas las mecánicas de plataformas en su núcleo.

## Precedentes consultados

- Dafny: contratos y verificación respecto de especificaciones. https://dafny.org/
- Koka: tipos que registran efectos. https://koka-lang.github.io/koka/doc/book.html
- WASI: seguridad basada en capacidades e interfaces para Wasm. https://wasi.dev/security y https://wasi.dev/
- Wasmtime: matriz de plataformas soportadas. https://docs.wasmtime.dev/stability-platform-support.html

Estos precedentes fundamentan piezas existentes. La integración y las reglas de PACT son propuestas pendientes de diseño, implementación y evaluación.
