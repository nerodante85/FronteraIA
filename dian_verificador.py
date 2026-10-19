"""Verificación periódica de aranceles contra la Consulta de Arancel de la DIAN (MUISCA).

Compara las filas validadas de docs/validacion-nandina.csv con la tarifa vigente publicada
por la DIAN. Uso: python dian_verificador.py  (código de salida 0 = sin diferencias,
1 = hay diferencias, 2 = no se pudo consultar la DIAN).
"""
import html
import re
import sys
import time

from partidas_validadas import cargar_validaciones

BASE = "https://muisca.dian.gov.co/WebArancel"
FORM = "vistaSalidaLugarEmbarque:formConsultaNomenclaturas:"


def _texto(contenido):
  contenido = re.sub(r"(?is)<(script|style).*?</\1>", " ", contenido)
  return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", contenido))).strip()


def _porcentajes(texto):
  return [float(p.replace(",", ".")) for p in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", texto)]


def porcentajes_gravamen(contenido):
  """Tarifas de 'GRAVAMEN ARANCELARIO' del popup de gravamen (la tarifa general)."""
  texto = _texto(contenido)
  return [float(p.replace(",", ".")) for p in
          re.findall(r"GRAVAMEN ARANCELARIO\s+(\d+(?:[.,]\d+)?)\s*%", texto)]


def porcentajes_iva(contenido):
  """Todas las tarifas de IVA del popup (puede haber una por condición)."""
  return _porcentajes(_texto(contenido))


def _hidden(contenido):
  campos = {}
  for etiqueta in re.findall(r"<input[^>]*>", contenido):
    if 'type="hidden"' in etiqueta:
      nombre = re.search(r'name="([^"]*)"', etiqueta)
      valor = re.search(r'value="([^"]*)"', etiqueta)
      if nombre:
        campos[html.unescape(nombre.group(1))] = html.unescape(valor.group(1)) if valor else ""
  return campos


def _valor(contenido, campo):
  m = re.search(r'id="vistaPerfilMercancia:formPerfilMercancia:%s"[^>]*value="([^"]*)"' % campo, contenido) \
      or re.search(r'value="([^"]*)"[^>]*id="vistaPerfilMercancia:formPerfilMercancia:%s"' % campo, contenido)
  return m.group(1) if m else None


def consultar(sesion, subpartida):
  """Devuelve {'gravamen': [...], 'iva': [...]} o None si la subpartida no existe."""
  codigo = subpartida.replace(".", "")
  pagina = sesion.get(f"{BASE}/DefConsultaGeneralNomenclaturas.faces", timeout=30)
  pagina.raise_for_status()
  datos = _hidden(pagina.text)
  datos[FORM + "codNomenclatura"] = codigo
  datos[FORM + "btConsultarNomenclatura.x"] = "5"
  datos[FORM + "btConsultarNomenclatura.y"] = "5"
  perfil = sesion.post(f"{BASE}/DefConsultaGeneralNomenclaturas.faces", data=datos, timeout=30)
  perfil.raise_for_status()
  ide = _valor(perfil.text, "strNomenclatura")
  fecha = _valor(perfil.text, "strFechaConsulta")
  if not ide or _valor(perfil.text, "codNomenclatura") != codigo:
    return None
  consulta = f"nomenclatura={ide}&codNomenclatura={codigo}&regimen=1&fechaConsulta={fecha}&modoPresentacionSeleccionBO=dialogo"
  gravamen = sesion.get(f"{BASE}/DefGravamenPopUp.faces?{consulta}&componente=3", timeout=30)
  iva = sesion.get(f"{BASE}/DefIvaPopUp.faces?{consulta}&componente=4", timeout=30)
  return {"gravamen": porcentajes_gravamen(gravamen.text), "iva": porcentajes_iva(iva.text)}


def comparar(validadas, consulta):
  """Lista de diferencias entre el CSV y la DIAN. `consulta(subpartida)` devuelve el dict o None."""
  diferencias = []
  for codigo, v in sorted(validadas.items()):
    dian = consulta(codigo)
    if dian is None:
      diferencias.append(f"{codigo} ({v['producto']}): la subpartida ya no existe en el Arancel")
      continue
    if not dian["gravamen"]:
      diferencias.append(f"{codigo} ({v['producto']}): no se pudo leer el gravamen de la DIAN")
    elif v["arancel"] not in dian["gravamen"]:
      diferencias.append(f"{codigo} ({v['producto']}): arancel {v['arancel']:g} % en la app, DIAN {dian['gravamen']}")
    if not dian["iva"]:
      diferencias.append(f"{codigo} ({v['producto']}): no se pudo leer el IVA de la DIAN")
    elif v["iva"] not in dian["iva"]:
      diferencias.append(f"{codigo} ({v['producto']}): IVA {v['iva']:g} % en la app, DIAN {dian['iva']}")
  return diferencias


def main(ruta="docs/validacion-nandina.csv"):
  import requests
  validadas, problemas = cargar_validaciones(ruta)
  if not validadas or problemas:  # un CSV vacío o dañado no puede dar un "todo coincide"
    print(f"No hay partidas validadas que verificar o el CSV tiene problemas: {problemas}")
    return 2
  sesion = requests.Session()
  sesion.headers["User-Agent"] = "Mozilla/5.0 (FronteraIQ verificador mensual)"

  def consulta(codigo):
    time.sleep(0.3)
    return consultar(sesion, codigo)

  try:
    diferencias = comparar(validadas, consulta)
  except Exception as error:  # DIAN caída, bloqueo antibots o cambio de formato
    print(f"No se pudo consultar la DIAN: {error}")
    return 2
  if diferencias:
    print(f"{len(diferencias)} diferencia(s) con la DIAN:")
    print("\n".join(f"- {d}" for d in diferencias))
    return 1
  print(f"Las {len(validadas)} partidas validadas coinciden con la DIAN.")
  return 0


if __name__ == "__main__":
  sys.exit(main())
