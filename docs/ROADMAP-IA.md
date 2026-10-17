# 🛣️ Roadmap de Integración de IA & Marco de Gobernanza (FronteraIQ Pro)

Este documento establece las directrices de arquitectura, seguridad y gobernanza técnica para la futura integración de módulos de Inteligencia Artificial en **FronteraIQ Pro**, cumpliendo con los hallazgos de la auditoría de confiabilidad (**AI-RELIABILITY-REPORT**).

---

## 📌 Estado Actual (determinístico, sin IA)
Actualmente, **FronteraIQ Pro** no usa ningún componente de IA y opera bajo un esquema **100% determinístico**:
* Todos los tributos (Arancel, IVA), bases gravables y costos *landed* son calculados mediante reglas aritméticas explícitas en código Python (`app.py`).
* La búsqueda arancelaria se basa en una tabla estática NANDINA (pendiente de validación con fuente y fecha de vigencia) y la TRM se consulta al servicio de datos abiertos del Estado colombiano (`datos.gov.co`).
* **Pendiente de corrección:** si la consulta de la TRM falla, la app usa un valor de respaldo (4.000 COP/USD) sin avisar al usuario. La auditoría indica que la consulta actual probablemente falla (hallazgo F-01).
* Al no haber IA, no existen riesgos de alucinación; los riesgos actuales son de calidad de datos y están documentados en la auditoría.

---

## 🎯 Arquitectura Híbrida para la Versión 3.0 (IA Asistida)

Al integrar Modelos de Lenguaje (LLM) para procesamiento de lenguaje natural o asistencia al usuario, la arquitectura **DEBE** mantener una separación estricta entre la capa de interpretación (IA) y la capa de cálculo (Motor Determinístico).

```
   ┌─────────────────────────────────────────────────────────┐
   │ 1. ENTRADA DEL USUARIO (Texto / Factura / Documento)    │
   └─────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │ 2. CAPA DE IA (Extracción de parámetros y contexto)    │
   │    - Extrae: FOB, Flete, Producto, Cantidad             │
   │    - Sugiere: Subpartida NANDINA + Nivel de Confianza    │
   └─────────────────────────────────────────────────────────┘
                                │
                                ▼ (Validación Humana Requiere Confirmación)
   ┌─────────────────────────────────────────────────────────┐
   │ 3. MOTOR DETERMINÍSTICO EN PYTHON (Core de app.py)      │
   │    - Calcula: CIF, Arancel, Base IVA, Total Landed      │
   │    - Cero intervención del LLM en aritmética o tasas    │
   └─────────────────────────────────────────────────────────┘
```

---

## 🛡️ Principios Mandatorios de Gobernanza de IA

Para la implementación de funciones con IA se deben cumplir 5 requisitos mínimos antes de cualquier despliegue en producción:

### 1. Independencia del Cálculo Tributario
* La IA **NUNCA** calculará impuestos, gravámenes, TRM ni subtotales.
* La función de la IA se limitará exclusivamente a la interpretación de texto, resúmenes descriptivos o sugerencias de clasificación.

### 2. Clasificación NANDINA Asistida con Validación Humana (HITL)
* Las sugerencias de subpartida arancelaria hechas por el modelo deben incluir un indicador visible de confianza (Ejemplo: `Confianza: 85%`).
* **Regla estricta:** La aplicación **nunca** autocompletará ni liquidará tributos definitivos basados en la respuesta de la IA sin la confirmación explícita del usuario mediante un botón de validación.

### 3. Tolerancia a la Incertidumbre (Fallback Explícito)
* Ante entradas ambiguas, la IA debe abstenerse de adivinar. La respuesta `"No es posible determinar la subpartida arancelaria con la información suministrada"` debe ser un estado válido y visible.
* Se derivará al usuario a la selección manual de la tabla NANDINA cuando la confianza sea inferior al 70%.

### 4. Privacidad y Tratamiento de Datos Sensibles
* Todos los datos enviados a APIs de terceros (OpenAI, Anthropic, Google Gemini, etc.) deben ser anonimizados.
* No se transmitirán NITs, nombres de empresas, datos bancarios ni identidades de proveedores extranjeros en los *prompts*.

### 5. Suite de Pruebas Anti-Alucinación
Previo al lanzamiento de funciones con IA, se ejecutará una suite de pruebas automatizadas (`test_ia_governance.py`, **pendiente de crear**) para validar:
* Manejo de partidas arancelarias inexistentes o derogadas.
* Detección de descripciones ambiguas o contradictorias.
* Identificación de mercancías de prohibida o restringida importación en Colombia (precursores químicos, fauna, material bélico) emitiendo alertas de Vistos Buenos (INVIMA / ICA / MinCIT). Requiere una tabla de mercancías controladas que **aún no existe**.

---

## 🗓️ Cronograma de Implementación (Fases)

* **Fase 1 (En curso):** Corrección de los bloqueadores de la auditoría (TRM, licencia Pro, PDF y validación de la tabla NANDINA), seguida de una beta controlada y validación de mercado en Cúcuta.
* **Fase 2:** Integración de parser de facturas comerciales (OCR + Extracción de campos FOB/Flete).
* **Fase 3:** Asistente de clasificación arancelaria con validación humana y alertas de regulaciones fronterizas.
