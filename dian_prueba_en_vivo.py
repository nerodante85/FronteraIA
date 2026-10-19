"""Prueba de humo de la consulta en vivo contra la DIAN real (se ejecuta en GitHub Actions)."""
import sys
import time

import dian_arancel as d
from partidas_validadas import cargar_validaciones


def main():
  validadas, _ = cargar_validaciones("docs/validacion-nandina.csv")
  codigo, v = next((c, x) for c, x in sorted(validadas.items()) if len(c.replace(".", "")) == 10)
  limpio = codigo.replace(".", "")
  cliente = d.ClienteDian()
  fallos = []
  c = cliente.consultar(limpio)
  print("consulta:", c)
  if c is None or c.arancel_general != v["arancel"] or v["iva"] not in {o.porcentaje for o in c.iva}:
    fallos.append(f"consulta de {codigo} no coincide con el CSV ({v})")
  if not c or not c.descripcion:
    fallos.append("sin descripción")
  t = time.time()
  hijos8 = cliente.subdivisiones(limpio[:8])
  print("subdivisiones 8 dígitos:", hijos8, round(time.time() - t, 1), "s")
  if limpio not in [h[0] for h in hijos8]:
    fallos.append("subdivisiones de 8 dígitos no incluye el código")
  t = time.time()
  hijos6 = cliente.subdivisiones(limpio[:6])
  print("subdivisiones 6 dígitos:", len(hijos6), round(time.time() - t, 1), "s")
  if limpio not in [h[0] for h in hijos6]:
    fallos.append("subdivisiones de 6 dígitos no incluye el código")
  print("FALLOS:", fallos)
  return 1 if fallos else 0


if __name__ == "__main__":
  sys.exit(main())
