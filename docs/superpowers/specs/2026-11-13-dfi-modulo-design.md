# Módulo DFI para FronteraIQ — diseño

Fecha: 2026-11-13 · Estado: **aprobado por Ricardo (2026-11-13)** · Alcance: importación a Colombia

## Intención y por qué
El Simulador de Costos DFI de ProColombia calcula el costo de la Distribución Física
Internacional con más detalle que FronteraIQ (INCOTERM, componentes de costo, capital
del inventario, contenedores). Ricardo quiere replicar sus funciones útiles dentro de
FronteraIQ Pro para pymes, agencias de aduanas y agentes de carga de Cúcuta, sin perder
la rapidez de la calculadora actual. (El "por qué" más fino —qué piden sus clientes—
no fue respondido; se asume que es dar más detalle y credibilidad a la cotización.)

## Objetivos
1. Asistente de INCOTERM de 4 preguntas Sí/No que sugiere el término y lo muestra en la cotización.
2. Gastos desglosados por componente DFI que sustituyen los 4 campos fijos y suman al mismo costo landed.
3. Costo de capital del inventario como línea adicional del costo.
4. Calculadora de contenedores (20', 40', 40' HC, 40' R): ocupación por volumen y peso.

## No objetivos
- Exportación a Venezuela (decisión del diseñador; se revisa después).
- Réplica del asistente de 6 pasos, catálogos persistidos o costeo ABC.
- Cambiar las fórmulas actuales de CIF, arancel, IVA y precio sugerido.

## Anti-objetivos (fallaría aunque "funcione")
- Que la calculadora gratuita se vuelva más lenta o larga de llenar.
- Cifras sin trazabilidad: toda cifra nueva debe aparecer en la cotización/CSV/PDF con su supuesto.
- Mezclar IA en la aritmética (rige `docs/ROADMAP-IA.md`: motor 100 % determinístico).

## Restricciones
- Streamlit + pandas + Plotly + fpdf2; Python 3.11+.
- Funciones puras con pruebas en `tests/`, siguiendo el patrón de `calcular_embarque`.
- Licencias vía `licencias.py`/Supabase. Reparto aprobado:
  - Gratis: asistente de INCOTERM.
  - Pro Fronterizo: costo de capital del inventario y calculadora de contenedores.
  - Agencia: gastos desglosados por componente DFI.
- Fuera de alcance por ahora (decisión del diseñador, a revisar): PDF con logo de la agencia, historial de cotizaciones y pago por cotización.
- Fórmula de capital (valor × tasa × días/365) aprobada por Ricardo como punto de partida.
- Total de gastos desglosados = gastos_locales_cop actual cuando el usuario no usa el desglose (retrocompatible).

## Enfoques considerados
- **A. Módulo `dfi.py` sobre el motor actual — ELEGIDO.** Barato, incremental, reutiliza TRM/PDF/CSV.
- B. Réplica completa de la matriz DFI con Supabase: semanas de trabajo, desvía el producto hacia corporativos.
- C. Solo INCOTERM + capital: rápido, no cubre el desglose que piden las agencias.

## Diseño
Nuevo `dfi.py` (sin Streamlit):
- `sugerir_incoterm(respuestas)` → código + descripción (tabla de decisión de las 4 preguntas; el DFI llega a DDP con todo "Sí").
- `COMPONENTES_DFI`: lista de componentes de importación (transporte importador, almacenaje, capital inventario, seguro, documentación, agentes, bancarios, aduaneros…).
- `total_gastos(componentes)` → COP.
- `costo_capital(valor_cop, tasa_anual_pct, dias)` = valor × tasa/100 × dias/365. **Supuesto mío**: no se vio la fórmula del DFI; se valida con Ricardo.
- `contenedores_necesarios(volumen_m3, peso_kg, tipo)` con capacidades del DFI: 40 HC 76,35 m³/26.660 kg; 40 R 67,95/29.400; ST 20' 33,2/28.280; ST 40' 67,72/26.840.

Integración en `app.py`: bloque opcional (expander) bajo "Logística Frontera"; el total desglosado alimenta `gastos_locales_cop`. Cotización PDF/CSV agregan INCOTERM, días, tasa y componentes.

## Entrega por pasos (cada uno se prueba y entrega solo)
1. INCOTERM + pruebas. 2. Desglose de gastos. 3. Capital del inventario. 4. Contenedores.

## Queda al constructor
Textos y orden de los componentes, nombres de columnas, diseño visual, validar la fórmula de capital con Ricardo.
