"""Carga de las partidas arancelarias validadas por un agente de aduanas.

Fuente única: docs/validacion-nandina.csv. Una fila cuenta como validada solo si TODOS
los campos obligatorios están completos y son coherentes; una fila a medio llenar nunca
marca la partida como validada (falla cerrada), y se reporta con el motivo.
"""
import csv
from datetime import date

OBLIGATORIOS = (
    "arancel_validado_pct", "iva_validado_pct", "fuente_normativa",
    "fecha_vigencia", "validado_por",
)


def _porcentaje(texto):
  valor = float(texto.strip().replace(",", "."))
  if not 0 <= valor <= 100:
    raise ValueError("fuera de 0 a 100")
  return valor


def cargar_validaciones(ruta, hoy=None):
  """Devuelve (validadas, problemas).

  validadas: {subpartida: {arancel, iva, fuente, vigencia, validado_por, condiciones}}
  problemas: lista de textos, uno por fila incompleta o inválida (las filas totalmente
  vacías en los campos de validación son simplemente "pendientes" y no son problema).
  """
  hoy = hoy or date.today()
  validadas, problemas = {}, []
  try:
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
      filas = list(csv.DictReader(archivo))
  except FileNotFoundError:
    return {}, [f"No existe {ruta}"]
  for n, fila in enumerate(filas, start=2):
    codigo = (fila.get("subpartida") or "").strip()
    campos = {k: (fila.get(k) or "").strip() for k in OBLIGATORIOS}
    if not any(campos.values()):
      continue  # pendiente de validar
    faltan = [k for k, v in campos.items() if not v]
    if faltan or not codigo:
      problemas.append(f"Fila {n} ({codigo or 'sin subpartida'}): faltan {', '.join(faltan) or 'subpartida'}")
      continue
    try:
      arancel = _porcentaje(campos["arancel_validado_pct"])
      iva = _porcentaje(campos["iva_validado_pct"])
      vigencia = date.fromisoformat(campos["fecha_vigencia"])
    except ValueError as error:
      problemas.append(f"Fila {n} ({codigo}): valor inválido ({error})")
      continue
    if vigencia > hoy:
      problemas.append(f"Fila {n} ({codigo}): la vigencia {vigencia} está en el futuro")
      continue
    validadas[codigo] = {
        "producto": (fila.get("producto") or "").strip(),
        "arancel": arancel, "iva": iva, "fuente": campos["fuente_normativa"],
        "vigencia": vigencia.isoformat(), "validado_por": campos["validado_por"],
        "condiciones": (fila.get("condiciones_especiales") or "").strip(),
    }
  return validadas, problemas


def catalogo_ampliado(base, validadas):
  """Tabla de partidas de la app: las de referencia más las nuevas ya validadas.

  Una partida candidata del CSV solo entra al selector cuando un agente la validó (así
  nunca se muestra un arancel sin respaldo). Las ya presentes en `base` no se duplican.
  """
  catalogo = dict(base)
  codigos = {v["codigo"] for v in base.values() if v["codigo"]}
  for codigo, v in sorted(validadas.items(), key=lambda kv: kv[1]["producto"].lower()):
    if codigo in codigos or not v["producto"] or v["producto"] in catalogo:
      continue
    catalogo[v["producto"]] = {"codigo": codigo, "arancel": v["arancel"], "iva": v["iva"]}
  return catalogo
