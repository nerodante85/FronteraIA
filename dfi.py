"""Módulo DFI (Distribución Física Internacional) de FronteraIQ.

Lógica pura, sin Streamlit: se prueba directo, igual que `licencias.py`.
Inspirado en el Simulador de Costos DFI de ProColombia. Solo importación a Colombia.
"""
import math

DESCRIPCION_INCOTERM = {
    "EXW": "En fábrica: el vendedor deja la mercancía en sus instalaciones; el comprador asume todo desde ahí.",
    "FCA": "Franco transportista: el vendedor entrega al transportista que designa el comprador.",
    "FAS": "Franco al costado del buque: el vendedor entrega junto al buque en el puerto de embarque.",
    "FOB": "Franco a bordo: el vendedor entrega la mercancía a bordo del buque en el puerto de embarque.",
    "CFR": "Costo y flete: el vendedor paga el transporte hasta el puerto de destino; el riesgo pasa al embarcar.",
    "CIF": "Costo, seguro y flete: como CFR, y además el vendedor contrata el seguro.",
    "CPT": "Transporte pagado hasta: el vendedor paga el transporte hasta el destino convenido.",
    "CIP": "Transporte y seguro pagados hasta: como CPT, y además el vendedor contrata el seguro.",
    "DAP": "Entregada en lugar: el vendedor entrega en el destino, listo para descargar, sin trámites de importación.",
    "DPU": "Entregada y descargada: como DAP, pero el vendedor también descarga en el destino.",
    "DDP": "Entregada derechos pagados: el vendedor lleva todo al destino y paga los trámites e impuestos de importación.",
}


def sugerir_incoterm(r1, r2, r3, r4):
  """Términos de venta que sugiere el asistente a partir de las 4 preguntas del DFI (Sí/No).

  r1: ¿asume todos los costos y riesgos hasta las instalaciones del comprador?
  r2: ¿puede llevar la mercancía hasta el lugar de entrega acordado (al otro lado de la frontera)?
  r3: ¿puede entregarla sin poner en peligro el pago?
  r4: ¿puede obtener la autorización de importación, hacer los trámites y recuperar el IVA?

  Supuesto: solo "todo Sí" → DDP está confirmado contra el simulador; el resto sigue las reglas
  de Incoterms 2020 y no se ha validado contra el DFI.
  """
  if r1 and r2 and r3:
    return ("DDP",) if r4 else ("DAP", "DPU")
  if r1 and r2:  # no puede asegurar el pago: conviene soltar el control antes del destino
    return ("CPT", "CIP")
  if r1:  # quiere asumir todo pero no puede llegar al lugar acordado
    return ("CPT", "CIP")
  if r2:
    return ("CPT", "CIP", "CFR", "CIF")
  return ("EXW", "FCA", "FAS", "FOB") if r3 else ("FCA", "FOB")


def costo_capital(valor_cop, tasa_anual_pct, dias):
  """Costo de financiar el inventario: valor × tasa anual × días / 365 (en COP).

  Supuesto aprobado como punto de partida (no se vio la fórmula exacta del DFI).
  Valor, tasa o días negativos o cero dan 0.
  """
  valor, tasa, dias = max(float(valor_cop), 0.0), max(float(tasa_anual_pct), 0.0), max(float(dias), 0.0)
  return valor * (tasa / 100) * dias / 365


# Capacidades tomadas del simulador DFI de ProColombia (unidades de carga precargadas).
CONTENEDORES = {
    "40HC": {"nombre": "CONTENEDOR 40 HC", "volumen_m3": 76.35, "peso_kg": 26660},
    "40R": {"nombre": "CONTENEDOR 40 R", "volumen_m3": 67.95, "peso_kg": 29400},
    "ST20": {"nombre": "CONTENEDOR ST 20'", "volumen_m3": 33.2, "peso_kg": 28280},
    "ST40": {"nombre": "CONTENEDOR ST 40'", "volumen_m3": 67.72, "peso_kg": 26840},
}


def contenedores_necesarios(volumen_m3, peso_kg, tipo):
  """Cuántos contenedores de `tipo` hacen falta y qué tan llenos quedan.

  Devuelve cantidad (int), ocupacion_volumen_pct y ocupacion_peso_pct (sobre el total de
  contenedores usados) y limitante ("volumen" o "peso"; None si no hay carga).
  Lanza KeyError si el tipo no existe. Volumen o peso negativos cuentan 0.
  """
  cap = CONTENEDORES[tipo]
  volumen, peso = max(float(volumen_m3), 0.0), max(float(peso_kg), 0.0)
  cantidad = max(math.ceil(volumen / cap["volumen_m3"]), math.ceil(peso / cap["peso_kg"]))
  if cantidad == 0:
    return {"cantidad": 0, "ocupacion_volumen_pct": 0.0, "ocupacion_peso_pct": 0.0, "limitante": None}
  ocup_vol = volumen / (cantidad * cap["volumen_m3"]) * 100
  ocup_peso = peso / (cantidad * cap["peso_kg"]) * 100
  return {
      "cantidad": cantidad, "ocupacion_volumen_pct": ocup_vol, "ocupacion_peso_pct": ocup_peso,
      "limitante": "volumen" if ocup_vol >= ocup_peso else "peso",
  }
