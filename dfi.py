"""Módulo DFI (Distribución Física Internacional) de FronteraIQ.

Lógica pura, sin Streamlit: se prueba directo, igual que `licencias.py`.
Inspirado en el Simulador de Costos DFI de ProColombia. Solo importación a Colombia.
"""

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
