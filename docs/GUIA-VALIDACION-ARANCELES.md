# Guía de validación de aranceles (para el agente de aduanas)

FronteraIQ Pro muestra arancel e IVA de **referencia** para 7 partidas. Mientras un agente
de aduanas no las confirme, la app las marca como "pendientes de validación". Esta guía
explica cómo validarlas en unos 30 minutos.

## Qué se pide
Abrir `docs/validacion-nandina.csv` (se abre en Excel) y completar, por cada fila, estas
columnas. **Una fila sin todos los campos obligatorios no se considera validada.**

| Columna | Obligatoria | Qué poner |
| --- | --- | --- |
| `arancel_validado_pct` | Sí | Arancel ad valorem vigente, en %. Si coincide con `arancel_app_pct`, repítelo igualmente. Decimales con punto o coma. |
| `iva_validado_pct` | Sí | IVA aplicable, en % (0 si es excluido o exento). |
| `fuente_normativa` | Sí | Norma o arancel consultado: decreto, número y año (p. ej. "Decreto xxxx de 20xx, Arancel de Aduanas"). |
| `fecha_vigencia` | Sí | Fecha desde la que rige lo que validaste, formato `AAAA-MM-DD`. No puede ser futura. |
| `validado_por` | Sí | Nombre y, si aplica, número de agencia o tarjeta del agente. |
| `condiciones_especiales` | No | Gravamen mixto o específico, contingentes, salvaguardias, licencia previa, registro o permiso (INVIMA, ICA, etc.), tratados de libre comercio. |
| `observaciones` | No | Cualquier aclaración, o si la subpartida de la app es incorrecta y cuál sería. |

## Qué revisar en cada partida
1. Que la **subpartida de 10 dígitos** corresponda al producto descrito. Si no, anótalo en `observaciones`.
2. Que el arancel sea el **vigente a hoy** para importaciones desde terceros países.
3. Si hay **gravamen mixto o específico**, o una salvaguardia: anótalo en `condiciones_especiales`. La app calcula solo un arancel ad valorem, así que una condición así cambia el costo real y hay que saberlo.
4. Si exige **permisos o registros previos**: anótalo; no cambia el cálculo pero sí el riesgo.

## Qué pasa después
Al fusionar el archivo, la app:
- muestra la fuente y la vigencia en lugar del aviso "pendiente";
- usa el arancel y el IVA validados como valores por defecto de esa partida;
- si hay una fila incompleta o con datos inválidos, **no** la marca como validada.

Las validaciones envejecen: conviene repetirlas cuando cambie el arancel y, como mínimo, una vez al año.

## Alcance y responsabilidad
La validación confirma los porcentajes de **referencia** de la tabla. La app es una
estimación y no reemplaza la liquidación oficial de la DIAN ni la asesoría de la agencia.
