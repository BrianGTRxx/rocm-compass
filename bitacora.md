# Bitácora — ROCm Compass

Registro de avance del proyecto. Formato: fecha, qué se hizo, por qué, qué sigue.

---

## 2026-09-05

**Qué se hizo:**
- Discusión inicial del plan con Claude Code a partir de `Docs/rocm-compass-plan.md`. Feedback dado: la v1 del plan era buena en posicionamiento (evitar el subnicho saturado de migración CUDA→HIP) pero floja en diferenciador técnico (Doctor como simple motor de reglas, Compass como scraping/curaduría).
- Se restructuró el plan (v2) para incorporar:
  1. El Doctor como **resolver de compatibilidad** (grafo de configuraciones conocidas + búsqueda de camino mínimo, no reglas planas).
  2. Un **loop de datos compartido** entre Doctor y Compass: los reportes opcionales (`--report`) alimentan directamente la matriz pública, en vez de depender solo de mantenimiento manual o scraping.
- Se movió el plan a `docs/rocm-compass-plan.md` dentro del proyecto (antes vivía en `Desktop/Claude/Docs/`).
- Se creó la estructura completa del repo: `doctor/`, `compass/`, `shared/`, `tests/`, `docs/`, `.github/workflows/`.
- Se escribió el esqueleto funcional (no solo carpetas vacías):
  - `shared/schema.py`: dataclasses `EnvironmentSnapshot`, `PackageVersion`, `EnvironmentReport` (la pieza que conecta ambos módulos).
  - `doctor/compatibility_graph.json`: esquema del grafo con 2 nodos de ejemplo (marcados `source: "example"`, pendientes de reemplazar con datos reales).
  - `doctor/detectors.py`: parseo de `rocminfo`/`rocm-smi`, con soporte para pasar texto de log simulado (sin GPU AMD disponible).
  - `doctor/resolver.py`: Dijkstra sobre el grafo de compatibilidad (nodo de entrada más cercano al snapshot detectado + camino más barato hacia un nodo conocido-funcional).
  - `doctor/cli.py`: comando `rocm-doctor check` con Typer (modos texto y `--json`, flag `--report` todavía no conectado).
  - `compass/packages.json`: lista inicial de 12 paquetes con estado `pending_research` (pendiente poblar en Fase 0).
  - `compass/scraper.py` y `compass/api.py`: esqueletos, funciones puras donde tenía sentido (testeable sin red).
  - `tests/test_resolver.py`: valida el resolver contra los nodos de ejemplo del grafo.
  - `pyproject.toml` (entry point `rocm-doctor`), `.gitignore`, `README.md`, `CONTRIBUTING.md`, `COMO_EJECUTAR.md`.

**Por qué:** dejar el proyecto en un estado donde ya se puede correr algo real (`pip install -e .` + `rocm-doctor check` + `pytest`) en vez de solo carpetas vacías, para validar la arquitectura antes de invertir en la Fase 0 (investigación de reglas/paquetes reales).

**Qué sigue (Fase 0 del plan):**
- [x] Investigar issues públicos de ROCm/PyTorch en GitHub y reemplazar los nodos de ejemplo en `doctor/compatibility_graph.json` con datos reales.
- [x] Poblar `compass/packages.json` con el estado real (manual) de los 12 paquetes.
- [ ] Decidir nombre final del proyecto (ver `docs/rocm-compass-plan.md` sección 10).
- [ ] Revisar a fondo el esqueleto de código (no solo correrlo) antes de seguir construyendo encima — pendiente, explícitamente dejado para después de esta investigación.

---

## 2026-09-05 (sesión 2 — investigación real)

**Qué se hizo:**

1. **`doctor/compatibility_graph.json` reescrito con datos reales** (nodos de ejemplo eliminados). 15 nodos + 12 aristas cubriendo `torch` en 3 arquitecturas (gfx90a = MI200, gfx942 = MI300, gfx1100 = Radeon RX 7900/RDNA3) a través de 5 versiones de ROCm (6.3.2 → 6.4.3 → 7.0.1 → 7.1.1 → 7.2.1). Fuentes: la matriz oficial de compatibilidad de ROCm (`compatibility-matrix.html`), la página de compatibilidad PyTorch↔ROCm, comandos `pip install` reales encontrados para cada versión, y `SUPPORTED_GPUS.md` de ROCm/TheRock. Cada nodo referencia su fuente en `sources` (top-level del JSON). Nota importante detectada: AMD advierte explícitamente que los wheels *nightly* de pytorch.org "no están probados extensivamente" comparado con los de `repo.radeon.com` — eso quedó documentado como nota en el nodo de ROCm 7.2.1 en vez de modelarse como un path del grafo.
2. **Nuevo módulo `doctor/known_issues.json` + `doctor/known_issues.py`**: reglas de diagnóstico que el grafo de versiones no cubre porque no son un problema de "qué versión instalar" sino de configuración rota. Tres casos reales documentados con fuente:
   - Permiso denegado en `/dev/kfd` porque el usuario no está en el grupo `render`/`video` (issues reales: ROCm/rocminfo#34, ROCm/ROCm#1798).
   - `HSA_OVERRIDE_GFX_VERSION` como workaround para GPUs de consumo no soportadas oficialmente (ej. RX 6600 gfx1032 → forzar gfx1030), con la advertencia real de que en ROCm 6.4.3+/7.2.x esto puede cargar el modelo y luego crashear (segfault) en el primer prompt, sin fix confirmado a la fecha.
   - Regresión de ABI en `torch.version.hip` tras un cambio de formato en el build system de TheRock, que rompe librerías como bitsandbytes/ComfyUI que parsean ese string (ROCm/TheRock#5425) — documentado como "advisory" porque no tiene fix del lado del usuario.
   - Se conectó al CLI (`rocm-doctor check --log-file <archivo>`) para escanear un log guardado contra estas reglas.
3. **`compass/packages.json` reescrito con estado real** de los 12 paquetes (antes todos en `pending_research`). Resumen de lo encontrado:
   - **Soporte oficial (`official`)**: `torch`, `triton` (el backend AMD ya está mergeado upstream en triton-lang/triton, no es un fork aparte), `vllm` (wheels oficiales de AMD), `sglang` (soporte fuerte en Instinct MI300X/325X/350X; Radeon recién en ROCm 7.14 y con workarounds).
   - **Soporte parcial (`partial`)**: `flash-attn` (el repo oficial Dao-AILab NO soporta AMD; hay que usar el fork ROCm/flash-attention), `xformers` (sin soporte nativo sólido; Axolotl documenta textualmente que "xformers appears to be incompatible with ROCm"; AMD empuja su propio AITER como alternativa), `bitsandbytes` (soporte multi-backend en alpha/experimental), `deepspeed` (soporte oficial pero con fricción real documentada — un issue abierto preguntando qué versión de ROCm soporta, y Axolotl reportando que "no funcionó" en sus pruebas), `apex` (fork mantenido por ROCm, no el NVIDIA/apex upstream), `unsloth` (soporte activo y evolucionando pero con bugs abiertos recientes, incluyendo uno de junio 2026 de que dejó de funcionar en builds recientes de Studio), `axolotl` (guía oficial existe pero para ROCm 5.7.1/gfx90a con caveats reales: DeepSpeed no funcionó, xformers incompatible; hay un fork comunitario para ROCm 6.2+/MI300).
   - **Sin soporte (`unsupported`)**: `xla` (torch_xla no tiene backend PJRT para AMD, apunta a TPU/CPU/CUDA — se dejó explícito en vez de omitirlo, para que la matriz responda la pregunta en vez de quedarse callada).
4. Se actualizó `doctor/resolver.py` para leer el campo opcional `amdgpu_driver_version` de cada nodo (dato real disponible en la matriz oficial), y se propagó al output del CLI (texto y `--json`).
5. Se reescribió `tests/test_resolver.py` (los datos de ejemplo que probaba ya no existen) y se añadió `tests/test_known_issues.py`. Verificado manualmente con `python` (sin pytest instalado en el intérprete de sistema usado para la prueba rápida): resolver y matcher de known_issues corren correctamente sobre los datos reales.

**Por qué:** el usuario pidió explícitamente que la investigación fuera "real y funcional", no placeholders — cada nodo del grafo y cada paquete del Compass ahora tiene una fuente citada (doc oficial de AMD o issue de GitHub) en vez de datos inventados.

**Qué sigue:**
- [x] Revisar el esqueleto completo de código a fondo con el venv correcto (`3.11.6_env`).
- [ ] Ampliar el grafo de compatibilidad más allá de `torch` (cada paquete adicional necesita su propia cadena de nodos).
- [ ] Decidir nombre final del proyecto.

---

## 2026-09-05 (sesión 3 — revisión del esqueleto con el venv correcto)

**Qué se hizo:** `pip install -e ".[dev]"` con `3.11.6_env` (no el Python 3.7 de sistema usado antes solo para pruebas rápidas), y se corrió todo el flujo real: `pytest`, `rocm-doctor check` instalado como comando de verdad, `rocm-doctor check --json`, `rocm-doctor check --log-file`, e import de `compass.api`/`compass.scraper`. Esto sacó a la luz **dos bugs reales** que las pruebas rápidas con `python -c "..."` no habían detectado porque llamaban a las funciones directamente en vez de pasar por el CLI instalado:

1. **Typer colapsaba el subcomando `check`.** Con un solo `@app.command()` registrado, Typer asume que no hace falta nombrar el subcomando y invertía el propio nombre "check" como si fuera un argumento inesperado (`rocm-doctor check` fallaba con "Got unexpected extra argument(s) (check)"; solo `rocm-doctor --package ...` funcionaba). Esto habría roto silenciosamente cada ejemplo de uso escrito en el README, `COMO_EJECUTAR.md`, el docstring del CLI y hasta el plan. Fix: se agregó un `@app.callback()` vacío en `doctor/cli.py` — es la forma documentada de forzar a Typer a seguir pidiendo el nombre del subcomando aunque solo haya uno (deja además espacio para agregar comandos hermanos como `report` más adelante sin romper nada).
2. **El detector crasheaba con traceback crudo si `rocminfo`/`rocm-smi` no existían en el sistema** (`FileNotFoundError` sin capturar en `doctor/detectors.py::_run`). Este es exactamente el escenario más común de primer uso: una máquina sin ROCm instalado (como esta misma, Windows sin GPU AMD). Fix: `_run()` ahora captura `FileNotFoundError`/`OSError` y devuelve `""`, dejando que el snapshot caiga a `"unknown"` en vez de reventar.
3. **Bug de correctitud, no solo de crash:** una vez arreglado el punto 2, `rocm-doctor check` seguía corriendo `resolve()` incluso con `gpu_arch=unknown`, y el resolver —al no tener ninguna arquitectura real con la cual comparar— igual elegía el nodo "más cercano" y lo reportaba con **costo 0**, como si el entorno ya estuviera en una configuración conocida-funcional. Eso es literalmente lo opuesto de la verdad (no se detectó nada). Fix: `doctor/cli.py` ahora detecta explícitamente el caso `gpu_arch == "unknown" and rocm_version == "unknown"`, se salta la resolución por completo, y muestra un mensaje claro de "no se pudo detectar una instalación de ROCm" en vez de una recomendación falsa.

**Por qué importa:** los tres bugs son del tipo que solo aparece corriendo el flujo real end-to-end (CLI instalado, sin GPU AMD) — ninguno se veía llamando a las funciones de Python directamente, que es como se habían "probado" en la sesión anterior. Confirma que vale la pena el paso de `pip install -e .` + probar el comando real antes de dar por buena cualquier función nueva.

**Verificado después del fix:** `pytest` (5/5 passed), `rocm-doctor check` (mensaje correcto de "no detectado"), `rocm-doctor check --json` (campo nuevo `rocm_detected: false`), `rocm-doctor check --log-file` con un log simulado de error real de `/dev/kfd` (matchea `kfd-permission-denied` correctamente), `compass.api` importa, `compass.scraper` imprime el estado real de los 12 paquetes.

**Qué sigue:**
- [ ] Simular un entorno "sano" end-to-end (no solo en tests unitarios) para confirmar visualmente el mensaje de recomendación con `--package torch` en un caso que sí resuelve.
- [ ] Considerar exponer `rocminfo_text`/`rocm_smi_text` (ya soportados en `detect_environment()`) como flags del CLI para poder hacer demos sin GPU AMD sin tener que escribir Python a mano.
- [ ] Ampliar el grafo de compatibilidad más allá de `torch`.
- [ ] Decidir nombre final del proyecto.

---

## 2026-09-05 (sesión 4 — notas de Obsidian)

**Qué se hizo:** Brian preguntó si hacía falta Graphify (herramienta CLI de terceros que registra un skill dentro de Claude Code y otros asistentes) para tener un grafo visual en Obsidian. Investigué la herramienta antes de recomendarla: el repo reporta 115,000 estrellas en GitHub (cifra implausible para una herramienta casi desconocida, comparable a repos como VS Code), existen varios repos casi idénticos bajo distintas cuentas con el mismo texto promocional, y hay una ola de artículos de blog casi simultáneos con el mismo ángulo de marketing — patrón típico de astroturfing. Recomendé no instalarla y, en su lugar, generar el grafo con el graph view nativo de Obsidian (que Brian ya tiene instalado), sin necesidad de ningún plugin de terceros.

Se creó `scripts/generate_obsidian_notes.py`: lee `doctor/compatibility_graph.json`, `compass/packages.json` y `doctor/known_issues.json`, y genera 34 notas `.md` con `[[wikilinks]]` en `obsidian/`:
- `Grafo de Compatibilidad/` — un nodo por combinación arquitectura+ROCm+paquete, enlazado a su arquitectura y con "Anterior"/"Siguiente" según las aristas del grafo.
- `Arquitecturas/` — nota hub por `gfx90a`/`gfx942`/`gfx1100`, listando sus nodos en orden de versión de ROCm.
- `Paquetes/` — una nota por paquete del Compass con estado, fuente y notas.
- `Problemas Conocidos/` — una nota por regla de `known_issues.json`.
- `Indice.md` — mapa de contenido enlazando todo.

Se generó el vault, se revisó el contenido de una muestra de cada tipo de nota, y se encontró un bug menor (la nota `torch.md` se autoenlazaba a sí misma sin sentido) que se corrigió en el generador antes de regenerar.

**Por qué:** el proyecto ya tiene los datos estructurados (JSON); generar las notas en vez de escribirlas a mano evita que se desactualicen cuando el grafo/Compass crezcan en Fase 0, y es coherente con la filosofía del proyecto (nada de mantenimiento manual que se pueda automatizar).

**Decisión de repo:** `obsidian/` se agregó a `.gitignore` — es 100% derivado de los tres JSON fuente, se regenera con un comando, y no debe editarse ni versionarse a mano.

**Qué sigue:**
- [ ] Simular un entorno "sano" end-to-end (no solo en tests unitarios) para confirmar visualmente el mensaje de recomendación con `--package torch` en un caso que sí resuelve.
- [ ] Considerar exponer `rocminfo_text`/`rocm_smi_text` como flags del CLI para demos sin GPU AMD.
- [ ] Ampliar el grafo de compatibilidad más allá de `torch` (el generador de Obsidian ya está listo para escalar con esos datos sin cambios).
- [ ] Decidir nombre final del proyecto.

---

## 2026-09-05 (sesión 5 — git init + Fase 2: el loop de datos)

**Qué se hizo:**

1. **`git init`** en `ROCm_AMD/` (todavía sin ningún commit -- se preguntó explícitamente antes de commitear, siguiendo la regla de nunca commitear sin pedido directo).
2. **Implementada la Fase 2 completa del plan** (el loop de datos, section 4.3):
   - **`shared/store.py`** (nuevo): SQLite mínimo (`shared/reports.db`, no versionado) con `save_report()`/`load_reports()` sobre `EnvironmentReport`. Justo lo que la sección 6 del plan pedía ("SQLite al inicio, nada de bases de datos complejas").
   - **`compass/aggregate.py`** (nuevo): lee `shared/reports.db` y agrega por paquete (`total_reports`, `worked`, `failed`, `partial`, `known_good_combos`) -- la mitad "Compass" del loop.
   - **`doctor/detectors.py`**: se agregó `detect_installed_package_version()` (vía `importlib.metadata`) -- sin esto, un reporte no podía saber qué versión del paquete se estaba probando realmente (antes no existía ningún detector de versión de paquetes Python, solo de ROCm/GPU).
   - **`doctor/cli.py`**: `--report` dejó de ser un mensaje ("not wired up yet") y ahora valida (`--outcome` obligatorio, entorno detectado, versión de paquete resoluble o `--package-version` explícito) y guarda de verdad vía `shared/store.save_report`. Se agregó `--outcome` y `--notes` como opciones nuevas.
   - **`compass/api.py`**: `/packages` y `/packages/{name}` ya no devuelven `[]` -- combinan la metadata estática de `packages.json` con el agregado en vivo de `compass/aggregate.py`.
3. **Tests nuevos** (18 en total ahora, todos verdes): `test_store.py`, `test_aggregate.py`, `test_cli_report.py` (incluye los casos de rechazo: sin `--outcome`, sin ROCm detectado, sin versión de paquete detectable), `test_api.py` (smoke test HTTP con `TestClient`), y sobre todo **`test_loop_end_to_end.py`** -- el ítem literal del checklist de Fase 2 ("verificar que un reporte nuevo del Doctor actualiza la matriz del Compass"), que guarda un reporte simulado de `vllm` vía `_submit_report()` y confirma que `aggregate_reports_by_package("vllm")` lo refleja, sin tocar ningún otro paquete.
4. Se agregó `httpx` a las dependencias de dev (necesario para `fastapi.testclient.TestClient`).
5. **Verificado end-to-end con el venv correcto**, no solo con tests unitarios: `rocm-doctor check --report --outcome worked` en esta máquina (sin ROCm) rechaza correctamente con "no ROCm environment was detected -- nothing to report" (texto y `--json`), y `compass.api` sirviendo `/packages/torch` de verdad devuelve el bloque `community_reports` calculado en vivo (no un mock).

**Por qué:** esta es la pieza que convierte "un CLI de diagnóstico" + "una tabla de estado" en el proyecto que describe el plan -- sin este loop, Doctor y Compass eran dos cosas separadas que compartían un esquema de datos pero no un dataset real.

**Qué queda abierto (documentado, no resuelto):** cómo llegan al dataset los reportes de máquinas de OTRAS personas una vez el proyecto sea público (PR/issue automático vs. un endpoint real) sigue siendo la pregunta abierta de la sección 10 del plan -- lo que se construyó hoy es el contrato local (guardar/leer), no el mecanismo de transporte para cuando esto salga a producción.

**Qué sigue:**
- [ ] Decidir el mecanismo de transporte para reportes de terceros (PR/issue bot vs. endpoint HTTP real) cuando el proyecto se publique.
- [ ] Ampliar el grafo de compatibilidad y el loop de reportes más allá de `torch`.
- [ ] Decidir nombre final del proyecto.
- [ ] Hacer el primer commit (pendiente de confirmación explícita).

---

## 2026-09-05 (sesión 6 — auditoría de bugs pre-publicación)

**Qué se hizo:** antes de publicar en GitHub, Brian pidió una revisión a fondo ("no quiero errores simples") de todo el código, librerías y lógica. Cada hallazgo se verificó **ejecutando código real** antes de reportarlo (no especulación). Se encontraron y corrigieron 6 bugs reales:

1. **Fuga de conexiones SQLite (`shared/store.py`).** `with _connect(db_path) as conn:` nunca cerraba la conexión -- es un comportamiento documentado de `sqlite3.Connection` (el context manager solo hace commit/rollback, no `close()`). Verificado de forma contundente: tras el `with`, la conexión seguía usable, y Windows literalmente rechazó borrar el archivo temporal por estar "en uso por otro proceso". Grave porque `compass/api.py` es un servidor de larga duración -- cada `GET /packages` llamaba a `aggregate_reports_by_package()` 12 veces (una por paquete), filtrando 12 conexiones por request. Fix: `contextlib.closing()` envolviendo la conexión en `save_report`/`load_reports`.
2. **El resolver podía reportar "costo 0" falso (`doctor/resolver.py`).** La heurística de distancia comparaba versiones de ROCm como string exacto; si el ROCm real no matcheaba ningún nodo del grafo (el caso normal, dado que las versiones patch varían constantemente), el desempate caía arbitrariamente en el nodo **más viejo** del grafo, con costo 0. Reproducido: `rocm_version="7.9.9"` en gfx1100 (no existe en el grafo) devolvía "ya estás bien en rocm 6.3.2, costo 0" -- literalmente al revés de la realidad. Fix de raíz, no parche: se creó `shared/versions.py` (comparación numérica de versiones en vez de string) y se reescribió el algoritmo de `resolve()` como **Dijkstra multi-fuente** -- cada nodo arranca con su propio costo de entrada (la distancia heurística real a lo detectado) en vez de descartarlo al elegir un único "punto de entrada" a costo 0. Verificado: el mismo caso ahora da `total_cost=6`, y una versión cercana (6.3.5) da menor costo que una lejana (7.9.9) -- la comparación numérica funciona.
3. **Advertencias de seguridad se perdían en silencio (`doctor/known_issues.py`).** El dataclass `KnownIssue` no tenía campo `caveats`, así que la advertencia real de que `HSA_OVERRIDE_GFX_VERSION` puede causar un **segfault** en ROCm 6.4.3+/7.2.x (y no funciona en Windows) nunca llegaba al usuario del CLI. Fix: se agregó el campo, se pobló desde el JSON, y se agregó la línea `Caveats:` al output de `rocm-doctor check --log-file`. Verificado end-to-end con el CLI real.
4. **Comparación de versiones como texto rompe con doble dígito (`scripts/generate_obsidian_notes.py`).** `sorted(versions)` como string pondría `"6.10.0"` antes que `"6.3.2"`. Mismo root cause que el bug 2 -- se resolvió con el mismo `shared/versions.py` (`version_sort_key`), reutilizado en vez de duplicar la lógica.
5. **Nombre de paquete no coincidía con el nombre real de instalación (`compass/packages.json`).** Se trackeaba `torch_xla` como `"xla"`, pero el paquete real en PyPI es `torch-xla`. Esto hacía que `detect_installed_package_version("xla")` fallara siempre, aunque el usuario sí tuviera `torch-xla` instalado -- bloqueando `--report` para ese paquete por un mismatch de nombre, no por falta de instalación real. Fix: renombrado en `packages.json` (y en `docs/rocm-compass-plan.md`, mención de la lista inicial).
6. **(Encontrado al verificar el fix #5) El generador de Obsidian nunca borraba notas obsoletas.** Al renombrar `xla` -> `torch-xla` y regenerar, quedó un `xla.md` huérfano junto al nuevo `torch-xla.md`. Fix: `scripts/generate_obsidian_notes.py` ahora borra `obsidian/` por completo antes de regenerar.

**Bonus (no era un bug reportado, pero se corrigió junto con el #1):** `tests/test_api.py` no aislaba su base de datos -- correrlo solo creaba de verdad `shared/reports.db` en el repo, porque `compass/api.py` no tenía forma de inyectar una ruta distinta. Fix: se agregó una dependencia de FastAPI (`get_db_path`, inyectable vía `Depends`) que los tests sobreescriben con `app.dependency_overrides` -- además deja la puerta abierta para configurar la ubicación de la DB en un despliegue real más adelante.

**Tests:** de 18 a 20 (se agregaron `test_a_rocm_version_absent_from_the_graph_never_reports_zero_cost` y `test_a_nearby_untracked_version_costs_less_than_a_distant_one`, que reproducen exactamente el bug 2 para que no vuelva a colarse). El test `test_older_rocm_resolves_towards_a_newer_known_good_node`, que antes esperaba `total_cost == 0`, en realidad estaba **codificando el bug** sin que nadie se diera cuenta -- se corrigió a `total_cost == 1` (el mismatch real de kernel_version).

**Por qué importa:** varios de estos bugs son exactamente el tipo de cosa que solo se nota corriendo el código de verdad contra casos reales (una versión de ROCm no listada, un servidor de larga duración, un nombre de paquete real) -- ninguno era detectable con una lectura superficial del código.

**Qué sigue:**
- [ ] Decidir el mecanismo de transporte para reportes de terceros.
- [ ] Ampliar el grafo de compatibilidad más allá de `torch`.
- [ ] Decidir nombre final del proyecto.
- [ ] Hacer el primer commit y publicar en GitHub.
