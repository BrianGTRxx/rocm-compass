# Cómo ejecutar ROCm Compass

Guía rápida para correr el proyecto en desarrollo, tanto desde Visual Studio Code como desde la terminal (PowerShell / cmd). Ninguno de los dos módulos necesita una GPU AMD para desarrollarse: el Doctor se prueba con logs simulados (`rocminfo`/`rocm-smi` guardados) y el Compass es agregación de datos, no ejecución en GPU.

## 1. Crear y activar un entorno virtual

Requiere Python 3.11+ puro (sin dependencias de ML pesadas -- Typer, FastAPI, uvicorn, pytest solamente).

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (cmd):**
```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

**VS Code:** `Ctrl+Shift+P` → `Python: Select Interpreter` → selecciona el intérprete dentro de `.venv`. Con eso la terminal integrada y el botón "Run" ya usan el venv correcto.

## 2. Instalar el proyecto en modo editable

Desde la raíz del repo, una sola vez (o cada vez que cambien las dependencias en `pyproject.toml`):

```bash
pip install -e ".[dev]"
```

Esto instala `typer`, `fastapi`, `uvicorn`, `pytest`, y registra el comando `rocm-doctor` apuntando a `doctor/cli.py`.

## 3. Correr el Doctor (CLI)

```bash
rocm-doctor check
```

```bash
rocm-doctor check --package torch --json
```

Si `rocm-doctor` no se reconoce como comando (por ejemplo, si prefieres no reinstalar tras cada cambio), se puede correr directamente como módulo:

```bash
python -m doctor.cli check
```

> Nota: mientras no haya GPU AMD disponible, `detect_environment()` intenta llamar a `rocminfo`/`rocm-smi` reales, no los encuentra en esta máquina (Ryzen + RTX 4050), y cae a `gpu_arch=unknown`/`rocm_version=unknown` en vez de crashear — el CLI lo reporta como "no se pudo detectar una instalación de ROCm" en vez de inventar una recomendación. Por la misma razón, `--report` se niega a guardar nada en esta máquina (no hay nada real que reportar). Para probar el resolver o el loop de reportes contra un caso que sí resuelve, usa `doctor/detectors.py::detect_environment(rocminfo_text=..., rocm_smi_text=...)` con texto de log simulado (ver `tests/test_resolver.py`, `tests/test_cli_report.py`).

## 4. El loop de datos: `--report`

Si `rocm-doctor check` sí detectó un entorno ROCm real, puedes compartir el resultado (queda guardado localmente en `shared/reports.db`, que no se versiona en git):

```bash
rocm-doctor check --package torch --report --outcome worked --notes "instalé con el wheel oficial de rocm6.4, funcionó de una"
```

`--outcome` es obligatorio junto con `--report` (`worked` | `failed` | `partial`). La versión del paquete se detecta sola vía metadata de pip; si no se puede (por ejemplo, lo compilaste desde fuente), pásala explícita con `--package-version`.

## 5. Correr la API del Compass

```bash
uvicorn compass.api:app --reload --port 8000
```

Abre `http://localhost:8000/docs` para la documentación interactiva (Swagger), `http://localhost:8000/health` para el check rápido, o `http://localhost:8000/packages` para ver la matriz completa -- cada paquete trae su bloque `community_reports` (`total_reports`, `worked`, `failed`, `partial`, `known_good_combos`), calculado en vivo desde `shared/reports.db`. Es decir: cualquier `--report` que guardes con el Doctor aparece aquí sin pasos intermedios -- ese es el loop completo del plan (sección 4.3).

## 6. Correr los tests

```bash
pytest
```

## 7. Generar el vault de Obsidian (opcional)

`obsidian/` no se versiona en git -- son notas generadas automáticamente a partir de `doctor/compatibility_graph.json`, `compass/packages.json` y `doctor/known_issues.json`. Para (re)generarlas:

```bash
python scripts/generate_obsidian_notes.py
```

Luego, en Obsidian: `Abrir carpeta como vault` → selecciona la carpeta `obsidian/` (o agrégala como carpeta dentro de un vault existente). El graph view nativo de Obsidian ya muestra las conexiones entre arquitecturas, versiones de ROCm, paquetes y problemas conocidos -- no hace falta ningún plugin. Vuelve a correr el script cada vez que cambie alguno de los tres JSON fuente; no edites las notas a mano, se sobreescriben.

## 8. Estructura del repo

```
ROCm_AMD/
├── doctor/            # Módulo A: CLI + resolver de compatibilidad
│   ├── compatibility_graph.json
│   ├── known_issues.json
│   ├── detectors.py
│   ├── resolver.py
│   ├── known_issues.py
│   └── cli.py          # `rocm-doctor check` (incluye --report)
├── compass/           # Módulo B: matriz pública del ecosistema
│   ├── packages.json
│   ├── aggregate.py     # lee shared/reports.db -> resumen por paquete
│   ├── scraper.py
│   └── api.py           # FastAPI: /packages, /packages/{name}
├── shared/            # esquema + almacenamiento compartido entre A y B
│   ├── schema.py
│   ├── store.py         # SQLite (shared/reports.db, no versionado)
│   └── versions.py       # comparación numérica de versiones (usado por el resolver)
├── scripts/
│   └── generate_obsidian_notes.py   # genera obsidian/ a partir de los JSON de datos
├── obsidian/          # vault generado (no versionado, ver sección 7)
├── tests/
├── docs/
│   └── rocm-compass-plan.md   # plan completo del proyecto (qué, por qué, fases)
├── bitacora.md         # registro de avance del mantenedor (no versionado, ver .gitignore)
├── README.md
├── CONTRIBUTING.md
└── pyproject.toml
```

Para el "por qué" de cada decisión de arquitectura, ver `docs/rocm-compass-plan.md`.
