# ROCm Compass — Plan de Proyecto (v2)

> Nombre de trabajo (provisional): **ROCm Compass**. Sigue siendo un placeholder — ver sección 10.
> v2: incorpora el diferenciador técnico real (resolver de compatibilidad) y el loop de datos entre módulos, discutido y acordado con el usuario antes de escribir código.

## 0. Instrucciones para Claude Code

Este documento es el brief de arranque de un proyecto open source. Úsalo como fuente de verdad sobre el **qué** y el **por qué** antes de generar cualquier código. Si en algún momento la implementación empieza a parecerse a "escanear un repositorio de código y generar un score de portabilidad automático con IA", **detente y avisa** — esa idea específica ya existe en el mercado (ver sección 2) y NO es lo que este proyecto busca construir.

Este proyecto vive en un espacio adyacente y actualmente vacío: diagnóstico de entorno + resolución de compatibilidad + seguimiento del ecosistema, alimentados por un loop de datos compartido — no migración de código.

---

## 1. Resumen ejecutivo

**ROCm Compass** ataca la fricción de adopción de AMD ROCm desde un ángulo que nadie más cubre hoy: en vez de traducir o auditar código CUDA→HIP (terreno ya ocupado, ver sección 3), diagnosticamos **entornos rotos**, **resolvemos qué combinación de versiones instalar** para que un entorno dado funcione, y mantenemos un **mapa vivo y público de qué partes del ecosistema de IA en Python funcionan en ROCm hoy** — con los tres componentes alimentándose de la misma fuente de datos.

El diferenciador real de esta versión del plan frente a la v1 es doble:

1. **El Doctor no es solo un motor de reglas JSON ("si X entonces Y")** — es un **resolver de compatibilidad**: dado un entorno detectado (arquitectura GPU, versión de kernel, versión de ROCm, versiones de paquetes Python instalados), busca en un grafo de configuraciones conocidas-buenas la más cercana alcanzable y recomienda el cambio mínimo (qué versión subir/bajar) para llegar a un estado funcional. Esto es un problema de constraint-solving/graph-search real, no un lookup table — más defendible técnicamente ante un equipo de ingeniería como el de AMD.
2. **El Doctor y el Compass comparten una sola fuente de datos.** Cuando un usuario corre `rocm-doctor check --report`, el reporte anonimizado (arquitectura + versiones + qué funcionó/falló) se envía opcionalmente a un dataset central. Ese dataset es exactamente lo que alimenta al Compass — así el "caniuse.com de ROCm" no depende de que tú lo actualices a mano ni de un scraper externo: crece automáticamente con el uso real de la herramienta. Cuantos más devs corran el Doctor, más preciso se vuelve el Compass, y viceversa (el Compass te dice qué configuraciones ya reportó la comunidad, lo cual mejora las recomendaciones del resolver).

El objetivo personal detrás de este proyecto sigue siendo el mismo: una herramienta visible, útil y mantenida en el tiempo — no un demo de hackathon — como carta de presentación técnica ante AMD (y NVIDIA, Meta, Tesla), que además reduzca la dependencia del ecosistema de IA de un solo proveedor de hardware.

---

## 2. Contexto: por qué este problema importa

- NVIDIA domina la IA vía CUDA. Las GPUs son caras y escasas; AMD ofrece una alternativa real (arquitectura CDNA, GPUs Instinct MI300X/MI325X) con software 100% abierto salvo el firmware de bajo nivel.
- El puente entre ambos mundos es **HIP** (API de AMD para portar código CUDA con cambios mínimos) y **HIPify** (traductor oficial CUDA → HIP).
- El problema real: HIPify traduce sintaxis, pero no garantiza rendimiento óptimo ni anticipa qué se va a romper. Además, ROCm tiene fama histórica de instalación/drivers inestables — mucha gente prueba AMD, se frustra en la primera hora por un mismatch de versiones, y vuelve a NVIDIA.
- AMD reconoce esto como un problema serio: invirtió en su propio "ROCm.ai" y patrocinó hackathons enteros dedicados a la migración CUDA→ROCm.
- Consecuencia de esos hackathons: **ya existen al menos cuatro proyectos** que atacan la migración de código (ver sección 3). Ese sub-nicho está saturado. El nicho que sigue vacío es el de **diagnóstico + resolución de compatibilidad de entorno** y **visibilidad continua y auto-alimentada del estado del ecosistema** — nadie mantiene esto de forma pública, continua y con datos reales de uso.

---

## 3. Qué NO vamos a construir (para no duplicar esfuerzo)

| Proyecto existente | Qué hace | Por qué no competimos ahí |
|---|---|---|
| **HIPify** (oficial, AMD) | Traduce sintaxis CUDA → HIP | Es la base sobre la que todo lo demás se construye; no tiene sentido reinventarlo |
| **PortPilot** | Score determinístico de portabilidad de un repo (AST + reglas) | Ya resuelto, con producto en vivo |
| **ROCmPorter Agent** | Escanea repo, genera reporte y parches con LLM local, con verificación | Ya resuelto, proyecto de hackathon AMD |
| **HIPForge** | Sube proyecto CUDA completo, traduce, compila, repara errores con IA en loop | Ya resuelto, proyecto de hackathon AMD |
| **ROCm Migration Copilot** | Pipeline agentic completo (LangGraph) de porting + build + tuning de rendimiento | Ya resuelto, el más completo de los cuatro |

**Conclusión:** evitar cualquier feature que sea "pega tu repo → recibe un score o un parche". Ese terreno ya tiene jugadores serios.

---

## 4. Qué SÍ vamos a construir

### 4.1 Módulo A — ROCm Doctor (diagnóstico + resolver de compatibilidad)

**Qué es:** un CLI (`rocm-doctor check`) que audita el estado de instalación de ROCm en una máquina, explica en lenguaje claro qué está mal, y **calcula la ruta mínima de cambios** para llegar a una configuración conocida-funcional — en vez de que el usuario pase horas buscando en foros o adivinando qué versión downgradear.

**Qué diagnostica (capa de detección, igual que v1):**
- Versión de kernel de Linux vs. versión de ROCm instalada
- Versión de drivers `amdgpu` vs. lo requerido por la versión de ROCm
- Arquitectura de GPU detectada (`gfx90a`, `gfx942`, etc.) vs. soporte oficial de esa versión de ROCm
- Conflictos conocidos (paquetes Python compilados contra otra versión de ROCm, variables de entorno mal configuradas, permisos de grupo `render`/`video` faltantes)
- Salida de `rocminfo` y `rocm-smi` interpretada, no solo mostrada en crudo

**Capa nueva — el resolver:**
- Modelamos el espacio de configuraciones como un **grafo de nodos** `(arquitectura GPU, versión ROCm, versión kernel, versión paquete)`. Las aristas conectan nodos que la comunidad (o release notes oficiales) confirmó como compatibles.
- Dado el entorno detectado del usuario (que probablemente NO es un nodo válido — por eso está roto), el resolver busca el nodo válido más cercano por una función de distancia simple (cuántos componentes hay que cambiar y qué tan lejos está cada versión), usando búsqueda en el grafo (BFS/Dijkstra con pesos por "costo de cambiar cada componente" — downgradear un paquete Python es barato, reinstalar el kernel es caro).
- Output: no solo "esto está mal" sino "cambia X de la versión A a la versión B, y con eso llegas a una configuración que N personas ya reportaron como funcional" (cuando hay dato comunitario) o "…que las release notes de ROCm confirman como soportada" (cuando el dato viene de fuentes oficiales).
- Esto convierte al Doctor en algo más cercano a un resolver de dependencias (estilo SAT simplificado / pathfinding) que a un sistema experto de reglas planas — mismo espíritu técnico que un resolver de paquetes, pero aplicado a compatibilidad de stack de IA.

**Cómo se construye:**
- Backend en Python puro (subprocess para invocar `rocminfo`/`rocm-smi`, parseo de su salida)
- Grafo de compatibilidad versionado en el repo (JSON o SQLite), poblado inicialmente con datos de release notes e issues públicos de ROCm/PyTorch, y luego enriquecido por reportes de la comunidad (ver 4.3)
- Algoritmo de resolución en Python puro (sin dependencias pesadas de grafos — un BFS/Dijkstra manual es más que suficiente para el tamaño de este problema)
- Output: reporte en terminal (con opción `--json`) + comandos exactos sugeridos para cada cambio recomendado
- Flag opcional `--report`: si el usuario acepta, envía un reporte anonimizado (arquitectura + versiones + resultado) al dataset compartido

### 4.2 Módulo B — ROCm Compass (rastreador vivo del ecosistema)

**Qué es:** un recurso público y actualizado (piensa en "caniuse.com" pero para IA en ROCm) que responde: *"¿este paquete que uso a diario funciona en ROCm, con qué versión de qué combinación, y qué tan bien?"*

**Qué rastrea (lista inicial sugerida):** `torch`, `triton`, `flash-attn`, `xformers`, `bitsandbytes`, `deepspeed`, `vllm`, `sglang`, `apex`, `torch-xla`, `unsloth`, `axolotl` — ampliable con el tiempo.

**Para cada paquete se registra:**
- Estado: soporte oficial / parcial (fork o flag) / sin soporte
- Combinaciones específicas reportadas como funcionales (arquitectura GPU + versión ROCm + versión del paquete) — esto es lo nuevo: no es un solo semáforo por paquete, es una matriz de combinaciones
- Última verificación (fecha) y fuente (release notes, issue, PR, reporte comunitario vía el Doctor, benchmark propio)
- Notas de rendimiento si existen

**Cómo se mantiene actualizado (dos fuentes, no una):**
1. **Loop automático desde el Doctor** (la fuente principal y el diferenciador): cada `--report` enviado se agrega al dataset y actualiza la matriz de compatibilidad — dato real de uso, no scraping.
2. **Scraper complementario** (GitHub Actions, cron semanal) que revisa releases/issues de cada repo buscando menciones de ROCm/HIP/AMD, para cubrir paquetes donde todavía no hay suficientes reportes de la comunidad.

**Output:** sitio estático simple o tabla Markdown auto-generada en el README al inicio (evitar sobre-construir un frontend) + JSON público consultable vía API simple.

### 4.3 El loop de datos (lo que conecta A y B)

- Esquema de datos único y compartido: un reporte de instalación (`environment snapshot` + `resultado` + `timestamp`) es la unidad atómica.
- El Doctor **consume** el dataset (para el resolver: "¿qué configuraciones cercanas ya funcionaron?") y **produce** nuevos registros (`--report`, opt-in, anonimizado — sin IPs ni datos identificables, solo arquitectura/versiones/resultado).
- El Compass **consume** el mismo dataset para generar la matriz de compatibilidad pública.
- Esto es lo que hace que el proyecto se mantenga solo con el tiempo en vez de depender 100% de que tú (Brian) actualices todo a mano — el mecanismo de crecimiento es el uso real de la herramienta, no el mantenimiento manual.

---

## 5. Usuarios objetivo

1. Desarrolladores individuales evaluando si migrar su proyecto a AMD
2. Equipos técnicos/CTOs decidiendo si comprar hardware AMD Instinct en vez de NVIDIA
3. La propia comunidad ROCm — como recurso de referencia compartido

---

## 6. Arquitectura técnica propuesta

- **Lenguaje principal:** Python (coincide con tu experiencia actual)
- **Módulo A (Doctor):** CLI con `Typer` o `Click`; grafo de compatibilidad versionado en el repo (JSON o SQLite); algoritmo de resolución (BFS/Dijkstra) en Python puro, sin dependencias de grafos pesadas
- **Módulo B (Compass):** backend simple con `FastAPI` sirviendo la matriz de compatibilidad generada a partir del dataset compartido; frontend inicial: tabla Markdown auto-generada en el README (evitar frontend complejo hasta validar interés)
- **Dataset compartido:** SQLite al inicio — un archivo, un esquema simple (`environment_reports`), consumido por ambos módulos. Nada de bases de datos complejas hasta que haya tracción real
- **Envío de reportes (`--report`):** al inicio puede ser tan simple como abrir un PR/issue automático en el repo con el JSON del reporte (cero infraestructura de servidor); si crece, se puede migrar a un endpoint real
- **CI/CD:** GitHub Actions para correr el scraper semanalmente, regenerar la matriz del Compass a partir del dataset, y validar que el grafo de compatibilidad del Doctor no tenga inconsistencias

**Estructura de repo sugerida:**
```
rocm-compass/
├── doctor/                   # Módulo A: CLI de diagnóstico + resolver
│   ├── compatibility_graph.json   # nodos y aristas de configuraciones conocidas
│   ├── resolver.py                # BFS/Dijkstra sobre el grafo
│   ├── detectors.py                # parseo de rocminfo/rocm-smi/kernel/drivers
│   └── cli.py
├── compass/                  # Módulo B: rastreador de ecosistema
│   ├── packages.json          # metadata estática de paquetes rastreados
│   ├── scraper.py              # fuente complementaria (releases de GitHub)
│   └── api.py
├── shared/                   # el loop de datos
│   ├── schema.py                # esquema del reporte compartido
│   └── reports.db                # SQLite con los environment_reports
├── .github/workflows/         # automatización (scraper semanal + regeneración de matriz)
├── README.md
└── CONTRIBUTING.md            # clave para atraer reportes de la comunidad
```

---

## 7. Contexto de hardware del desarrollador (importante)

- **Equipo disponible:** Ryzen 7 7735HS + RTX 4050 (NVIDIA) + 32GB RAM DDR5
- **Implicación:** esta máquina NO puede correr ROCm nativamente. Perfecta para desarrollar toda la lógica, el resolver, el scraper y el frontend, pero no para probar el diagnóstico contra una instalación real de ROCm.
- **Cómo lo resolvemos:**
  1. Ambos módulos están diseñados para minimizar la necesidad de GPU AMD propia — los detectores parsean texto (simulable con logs de ejemplo durante desarrollo), el resolver opera sobre un grafo de datos (no necesita GPU para correr), y el Compass es research/agregación, no ejecución en GPU.
  2. **Para validar contra la realidad:** rentar una GPU AMD Instinct por horas (TensorWave ronda $1.71–2/hora por MI300X, spot desde ~$0.95/hora). Con 2-3 sesiones cortas alcanza para validar el Doctor y poblar los primeros nodos reales del grafo.
  3. **Costo cero:** pedir en r/ROCm o Discord de AMD que la gente corra `rocm-doctor check --report` en su propia máquina — esto puebla el grafo de compatibilidad Y la matriz del Compass al mismo tiempo, gracias al loop de datos compartido.

---

## 8. Plan por fases

**Fase 0 — Preparación (semana 1)**
- Investigar issues públicos de ROCm/PyTorch en GitHub para poblar los primeros 15-20 nodos/aristas del grafo de compatibilidad
- Definir el esquema del `environment_report` compartido (la pieza que conecta todo)
- Definir la lista inicial de 10-12 paquetes para el Compass

**Fase 1 — MVP del Doctor + resolver (semanas 2-3)**
- Detectores funcionales (parseo de `rocminfo`/`rocm-smi`, kernel, drivers) probados con logs simulados
- Resolver básico (BFS sobre el grafo) que recomienda el cambio mínimo dado un nodo detectado
- CLI con salida legible y modo `--json`
- Validar con al menos una sesión de GPU rentada

**Fase 2 — Loop de datos + MVP del Compass (semanas 4-5)** ✅ completa (2026-09-05)
- [x] Implementar `--report` (local, `shared/reports.db`) y `--submit` (vía PR/issue automático -- GitHub Issue + `.github/workflows/ingest-reports.yml`)
- [x] Generar la matriz inicial del Compass a partir del dataset (`compass/packages.json` con estado real de 12 paquetes; scraper básico sigue siendo un esqueleto, no prioritario mientras el loop de reportes sea la fuente principal)
- [x] Verificar que un reporte nuevo del Doctor efectivamente actualiza la matriz del Compass (`tests/test_loop_end_to_end.py`, y ahora también para el transporte de terceros vía `compass/community_reports.jsonl`)

**Fase 3 — Lanzamiento y comunidad (semana 6+)**
- Publicar en GitHub con README claro, ejemplos, capturas, y una explicación simple del loop de datos (por qué correr `--report` ayuda a todos)
- Compartir en r/ROCm, foros de desarrolladores de AMD, y (con cuidado, sin spam) etiquetar cuentas de DevRel de AMD cuando el proyecto ya tenga valor demostrable
- Iterar según feedback real y según qué tan rápido crece el dataset

---

## 9. Métricas de éxito

- Estrellas/forks en GitHub (señal de interés)
- Número de reportes (`--report`) recibidos — la métrica más importante, porque mide si el loop de datos realmente funciona
- Número de paquetes y combinaciones rastreadas en el Compass, y frecuencia de actualización
- Precisión percibida del resolver (¿la gente reporta que la recomendación funcionó?)
- Cualquier mención o interacción de cuentas oficiales de AMD/ROCm

---

## 10. Preguntas abiertas

- ~~¿Nombre final del proyecto?~~ **Resuelto:** se queda "ROCm Compass" / `rocm-compass` — está libre en GitHub y PyPI, ya está en todo el código, y "compass" (brújula) describe bien lo que hace el resolver (te dice hacia dónde moverte). Verificado 2026-09-05.
- ¿El dashboard del Compass empieza como tabla en README o vale la pena un sitio web desde el día 1? — Recomendación: README primero, sitio solo si hay tracción (evita sobre-construir). Sigue abierta.
- ~~¿El envío de reportes (`--report`) empieza como PR/issue automático (cero infra) o vale la pena montar un endpoint desde el día 1?~~ **Resuelto:** se implementó la opción de cero infraestructura. `rocm-doctor check --report --submit` abre un GitHub Issue (vía `gh issue create` o un link pre-llenado) con el reporte en JSON; `.github/workflows/ingest-reports.yml` lo valida y lo agrega a `compass/community_reports.jsonl` automáticamente, comenta y cierra el issue. Ver `compass/ingest.py`, `shared/issue_format.py`, y `.github/ISSUE_TEMPLATE/environment_report.md` para reportes manuales. Migrar a un endpoint real sigue siendo una opción futura si el volumen lo justifica, pero no hace falta hoy.

---

## 11. Primeros pasos concretos (checklist para Claude Code)

- [x] Crear la estructura de repositorio descrita en la sección 6
- [x] Definir `shared/schema.py` con el esquema del `environment_report` (la pieza que conecta Doctor y Compass)
- [x] Escribir `doctor/compatibility_graph.json` con nodos reales basados en docs oficiales de ROCm (15 nodos de `torch`, 2 de `vllm` -- no 15-20 nodos de un solo golpe como preveía el plan original, sino ampliado incrementalmente con datos verificados; `flash-attn` deliberadamente sin nodo, ver sección 4.1)
- [x] Implementar `doctor/resolver.py` (Dijkstra multi-fuente sobre el grafo de compatibilidad -- más robusto que el BFS de un solo punto de entrada previsto originalmente, ver bitácora)
- [x] Implementar `doctor/detectors.py` y `rocm-doctor check` (con modo de prueba usando logs de ejemplo, ya que el entorno de desarrollo no tiene GPU AMD)
- [x] Implementar `--report` (local) y `--submit` (envío de reporte anonimizado vía PR/issue automático)
- [x] Poblar `compass/packages.json` con el estado real (investigado, no solo manual) de 12 paquetes clave
- [ ] Escribir `compass/scraper.py` de verdad (hoy es un esqueleto -- no prioritario mientras el loop de reportes de `--submit` sea la fuente principal de datos)
- [x] Verificar el loop end-to-end: un reporte simulado del Doctor actualiza la matriz del Compass (`tests/test_loop_end_to_end.py`), y lo mismo para un reporte de terceros ingerido desde un issue (`tests/test_aggregate.py::test_aggregate_merges_local_db_and_community_jsonl`)
- [x] Configurar GitHub Action -- no la del scraper semanal (sigue pendiente), sino la de ingesta de reportes (`ingest-reports.yml`), que resultó ser la pieza de automatización más importante
- [x] Escribir README.md con la visión del proyecto, el loop de datos, cómo instalarlo, y cómo contribuir
