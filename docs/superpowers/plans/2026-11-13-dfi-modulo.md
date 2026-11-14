# Módulo DFI para FronteraIQ — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir a FronteraIQ el asistente de INCOTERM (gratis), costo de capital y contenedores (Pro) y gastos desglosados por componente DFI (Agencia).

**Architecture:** Lógica pura en un archivo nuevo `dfi.py` (sin Streamlit, probado directo como `licencias.py`); `app.py` solo dibuja la interfaz y suma los resultados al costo landed. El nivel de licencia (`pro`/`agencia`), que Supabase ya devuelve pero la app descarta, se propaga para decidir qué función ve cada plan.

**Tech Stack:** Python 3.11+, Streamlit (`AppTest` para pruebas de interfaz), pandas, fpdf2, pytest.

**Spec:** `docs/superpowers/specs/2026-11-13-dfi-modulo-design.md`

## Global Constraints
- Importación a Colombia únicamente; exportación a Venezuela fuera de alcance.
- No cambiar las fórmulas de CIF, arancel, IVA, costo unitario ni precio sugerido (README, "Cómo se calcula").
- Funciones puras en `dfi.py`; nada de IA en la aritmética (`docs/ROADMAP-IA.md`).
- Reparto: INCOTERM gratis; capital y contenedores desde `pro`; desglose solo `agencia` (agencia incluye todo lo de pro).
- Capital = `valor_cop × tasa_anual_pct/100 × dias/365` (aprobado como punto de partida).
- Capacidades de contenedor (m³ / kg): `40HC` 76,35 / 26.660; `40R` 67,95 / 29.400; `ST20` 33,2 / 28.280; `ST40` 67,72 / 26.840.
- Toda cifra nueva aparece en el CSV y el PDF de la cotización con su supuesto.
- Texto de interfaz en español, sangría de 2 espacios como el resto del repo.

## Review Focus
- Con todas las funciones nuevas apagadas, el caso conocido da exactamente 61.178.600 de costo landed (regresión).
- Si Supabase cae, el nivel es `None` y no se ve ninguna función de pago (falla cerrada).
- Capital con tasa 0 o días 0 devuelve 0, sin error.
- Contenedores con volumen o peso 0 devuelve 0 contenedores; una carga mayor a un contenedor pide varios.
- Desglose con filas vacías, `NaN` o valores negativos: se tratan como 0 y no rompen el total.

## File Structure
- Create `dfi.py`: INCOTERM, capital, contenedores, desglose (todo puro).
- Modify `licencias.py`: `nivel_permite`.
- Modify `app.py`: `validar_licencia_nivel`, bloques de interfaz, `datos_cotizacion`, `fila_csv`, `lineas_liquidacion`, `generar_pdf_cotizacion`.
- Create `tests/test_dfi_*.py`, `tests/test_niveles.py`, `tests/test_dfi_ui.py`.
- Modify `README.md` (tabla de planes y fórmula).

---

### Task 1: Nivel de licencia (pro / agencia)

**Files:** Modify `licencias.py`, `app.py` (junto a `validar_licencia_pro`, ~línea 691); Test `tests/test_niveles.py`

**Interfaces:**
- Produces: `licencias.nivel_permite(nivel: str | None, requerido: str) -> bool`; `app.validar_licencia_nivel(clave: str) -> tuple[str | None, str | None]` (nivel o `None`, mensaje de error). `validar_licencia_pro` sigue devolviendo `(bool, error)` y delega en la anterior.

- [ ] **Step 1: Crear rama** `git switch -c feature/dfi-modulo`.
- [ ] **Step 2: Write the failing test** `tests/test_niveles.py`: `nivel_permite("agencia","pro")` y `("pro","pro")` son `True`; `("pro","agencia")`, `(None,"pro")` y `("desconocido","pro")` son `False`. Un test con `AppTest` o monkeypatch de `_consultar_licencia`: respuesta `{"valida": True, "nivel": "agencia"}` → `("agencia", None)`; la función lanza excepción → `(None, mensaje_de_rechazo("servicio_no_disponible"))`; clave de respaldo configurada → `("pro", None)`.
- [ ] **Step 3: Run** `pytest tests/test_niveles.py -v` → FAIL (funciones no definidas).
- [ ] **Step 4: Implement** `nivel_permite` con orden `{"pro": 1, "agencia": 2}` y `validar_licencia_nivel` reutilizando el cuerpo actual de `validar_licencia_pro` (devuelve `resultado.get("nivel")`; clave de respaldo → `"pro"`); `validar_licencia_pro` pasa a `nivel, error = validar_licencia_nivel(...); return nivel is not None, error`.
- [ ] **Step 5: Run** `pytest -q` → todo PASS (incluye `test_licencia.py`).
- [ ] **Step 6: Commit** `git commit -am "feat: propagar nivel de licencia (pro/agencia)"`.

### Task 2: Asistente de INCOTERM (gratis)

**Files:** Create `dfi.py`; Modify `app.py` (expander en la columna del formulario, y `datos_cotizacion`, `fila_csv`, `lineas_liquidacion`, PDF); Test `tests/test_dfi_incoterm.py`

**Interfaces:**
- Consumes: nada.
- Produces: `dfi.sugerir_incoterm(r1: bool, r2: bool, r3: bool, r4: bool) -> tuple[str, ...]` (códigos en mayúsculas, p. ej. `("DDP",)`); `dfi.DESCRIPCION_INCOTERM: dict[str, str]`.

- [ ] **Step 1: Capturar la tabla del simulador.** Con el navegador, abrir *Simulación → Modo guiado → Término de venta* y recorrer las 16 combinaciones Sí/No de las 4 preguntas anotando los términos que ofrece. Si no se puede, usar las reglas de Incoterms 2020 y dejar un comentario `# Supuesto: sin validar contra el DFI`. Avisar a Ricardo cuál de las dos se usó.
- [ ] **Step 2: Write the failing test:** `sugerir_incoterm(True,True,True,True) == ("DDP",)`; para las 16 combinaciones el resultado no está vacío y todo código está en `DESCRIPCION_INCOTERM`; `sugerir_incoterm(False,False,False,False)` coincide con lo capturado.
- [ ] **Step 3: Run** `pytest tests/test_dfi_incoterm.py -v` → FAIL.
- [ ] **Step 4: Implement** `sugerir_incoterm` como lookup sobre un diccionario `_TABLA` indexado por la tupla de 4 booleanos.
- [ ] **Step 5: Interfaz** en `calculadora()`: `st.expander("¿Qué INCOTERM te conviene?")` con 4 `st.radio` Sí/No (mismas preguntas del DFI), muestra términos y descripciones, y un selector del INCOTERM acordado. Guardar `incoterm` en `datos_cotizacion`; añadir columna `incoterm` en `fila_csv`, línea en `lineas_liquidacion` y en el PDF. Es informativo: no cambia ninguna cifra.
- [ ] **Step 6: Test de interfaz** en `tests/test_dfi_ui.py` con `AppTest`: plan gratuito ve el expander y el CSV trae la columna `incoterm`; el costo landed del caso conocido sigue en 61.178.600.
- [ ] **Step 7: Run** `pytest -q` → PASS. **Commit** `feat: asistente de INCOTERM`.

### Task 3: Costo de capital del inventario (Pro)

**Files:** Modify `dfi.py`, `app.py`; Test `tests/test_dfi_capital.py`, `tests/test_dfi_ui.py`

**Interfaces:**
- Consumes: `licencias.nivel_permite`, nivel de la sesión (guardar en una variable `nivel` en `calculadora()`).
- Produces: `dfi.costo_capital(valor_cop: float, tasa_anual_pct: float, dias: int) -> float`.

- [ ] **Step 1: Write the failing test:** `costo_capital(61_178_600, 12, 30) == pytest.approx(61_178_600*0.12*30/365)`; tasa 0 → 0; días 0 → 0; valor, tasa o días negativos → 0.
- [ ] **Step 2: Run** `pytest tests/test_dfi_capital.py -v` → FAIL.
- [ ] **Step 3: Implement** `costo_capital` con los valores negativos tratados como 0.
- [ ] **Step 4: Interfaz:** bloque Pro con `tasa anual (%)` y `días de inmovilización`; base = CIF + tributos + gastos (decisión mía; documentarla en pantalla). Línea "Costo de capital" aparte; se suma a `costo_total_landed_cop` solo si el bloque está activo. Sin Pro: teaser. Añadir `costo_capital_cop`, `tasa_capital_pct`, `dias_capital` a `datos_cotizacion`, CSV, líneas de liquidación y PDF.
- [ ] **Step 5: Test de interfaz:** con función apagada el landed es 61.178.600; con Pro y tasa 12 %, 30 días, el landed sube en el valor de `costo_capital`; con plan gratuito aparece el teaser.
- [ ] **Step 6: Run** `pytest -q` → PASS. **Commit** `feat: costo de capital del inventario (Pro)`.

### Task 4: Calculadora de contenedores (Pro)

**Files:** Modify `dfi.py`, `app.py`; Test `tests/test_dfi_contenedores.py`, `tests/test_dfi_ui.py`

**Interfaces:**
- Produces: `dfi.CONTENEDORES: dict[str, dict]` (claves `40HC`, `40R`, `ST20`, `ST40`, con `nombre`, `volumen_m3`, `peso_kg`); `dfi.contenedores_necesarios(volumen_m3: float, peso_kg: float, tipo: str) -> dict` con claves `cantidad: int`, `ocupacion_volumen_pct: float`, `ocupacion_peso_pct: float`, `limitante: "volumen" | "peso" | None`.

- [ ] **Step 1: Write the failing test:** 30 m³ y 20.000 kg en `ST20` → 1 contenedor, ocupación volumen ≈ 90,4 %, limitante `volumen`; 100 m³ y 1.000 kg en `ST40` → 2 contenedores; 0 m³ y 0 kg → 0 contenedores sin error; 10 m³ y 40.000 kg en `ST20` → 2 contenedores, limitante `peso`; tipo desconocido → `KeyError`.
- [ ] **Step 2: Run** `pytest tests/test_dfi_contenedores.py -v` → FAIL.
- [ ] **Step 3: Implement** con `max(ceil(vol/cap_vol), ceil(peso/cap_peso))` y ocupación sobre el total de contenedores usados.
- [ ] **Step 4: Interfaz Pro:** entradas de volumen (m³) y peso (kg) de la carga; tabla con los 4 tipos (cantidad y ocupación). Se agrega al CSV/PDF solo el tipo que el usuario elija. No altera cifras de costo. Sin Pro: teaser.
- [ ] **Step 5: Test de interfaz** (gratuito ve teaser; Pro ve la tabla). **Run** `pytest -q` → PASS. **Commit** `feat: calculadora de contenedores (Pro)`.

### Task 5: Gastos desglosados por componente DFI (Agencia)

**Files:** Modify `dfi.py`, `app.py` (`total_gastos_locales_cop`, ~línea 1040), `README.md`; Test `tests/test_dfi_desglose.py`, `tests/test_dfi_ui.py`

**Interfaces:**
- Produces: `dfi.COMPONENTES_IMPORTACION: tuple[str, ...]` = `("Transporte importador","Almacenaje","Aduaneros","Agentes","Bancarios","Documentación","Seguro local","Manipuleo de desembarque","Otros")`; `dfi.total_gastos(filas: list[dict]) -> float` donde cada fila trae `componente` y `valor_cop`.

- [ ] **Step 1: Write the failing test:** suma de `[{"componente":"Almacenaje","valor_cop":300000},{"componente":"Agentes","valor_cop":450000}]` = 750.000; filas con `valor_cop` `None`, `float("nan")` o negativo cuentan 0; lista vacía → 0.
- [ ] **Step 2: Run** `pytest tests/test_dfi_desglose.py -v` → FAIL.
- [ ] **Step 3: Implement** `total_gastos`.
- [ ] **Step 4: Interfaz Agencia:** interruptor "Desglosar gastos por componente DFI" con `st.data_editor` dinámico (columnas Componente y Valor COP), precargado con los 4 gastos actuales (Agenciamiento→Agentes, Bodegaje→Almacenaje, Transporte local→Transporte importador, Otros→Otros). Si está activo y el nivel es `agencia`, `total_gastos_locales_cop = dfi.total_gastos(filas)`; si no, queda la suma actual. Las filas viajan a CSV (columna por componente) y PDF. Nivel `pro` o gratuito: teaser.
- [ ] **Step 5: Test de interfaz:** sin activar, landed 61.178.600; con `agencia` activado y los mismos 4 valores precargados, el landed es idéntico; con `pro` solo se ve el teaser.
- [ ] **Step 6: Documentar** en `README.md` la tabla de planes (Gratuito / Pro / Agencia) y la fórmula del costo de capital.
- [ ] **Step 7: Run** `pytest -q` → PASS. **Commit** `feat: gastos desglosados DFI (Agencia)`.
