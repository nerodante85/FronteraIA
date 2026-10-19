"""Consulta del Arancel de Aduanas en la DIAN (MUISCA, régimen de importación).

Lee, para una subpartida de 10 dígitos: descripción, gravamen arancelario, arancel variable,
tarifas de IVA (con sus condiciones) y gravámenes preferenciales por acuerdo y país.
Todo lo que se lee es tarifa general vigente; la subpartida correcta la define el usuario.
"""
import html
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date

BASE = "https://muisca.dian.gov.co/WebArancel"
PAGINA = f"{BASE}/DefConsultaGeneralNomenclaturas.faces"
FORM = "vistaSalidaLugarEmbarque:formConsultaNomenclaturas:"
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
         "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
ESPERA_TRAS_FALLO_S = 60
HILOS = 6


class DianNoDisponible(Exception):
  """La DIAN no respondió o cambió el formato de su página."""


@dataclass(frozen=True)
class Tarifa:
  concepto: str
  porcentaje: float
  desde: date | None
  hasta: date | None


@dataclass(frozen=True)
class OpcionIva:
  producto: str          # condición del producto ("" si la tarifa es única)
  porcentaje: float
  etiqueta: str          # "", "EXENTO" o "EXCLUIDO"
  desde: date | None
  hasta: date | None


@dataclass(frozen=True)
class Acuerdo:
  acuerdo: str
  pais: str
  porcentaje: float
  desde: date | None
  hasta: date | None


@dataclass(frozen=True)
class ConsultaArancel:
  codigo: str            # 10 dígitos sin puntos
  descripcion: str
  fecha_consulta: str    # AAAAMMDD, la que usa la DIAN
  arancel_general: float | None
  arancel_variable: float | None   # solo si está vigente hoy
  iva: tuple[OpcionIva, ...]
  acuerdos: tuple[Acuerdo, ...]

  @property
  def arancel_aplicable(self):
    """El arancel variable reemplaza al general mientras esté vigente."""
    return self.arancel_variable if self.arancel_variable is not None else self.arancel_general


def formatear_codigo(codigo):
  c = re.sub(r"\D", "", codigo)
  return ".".join(p for p in (c[:4], c[4:6], c[6:8], c[8:10]) if p)


def normalizar_codigo(texto):
  """Devuelve los dígitos de una subpartida de 6, 8 o 10 cifras; si no es válida, lanza ValueError."""
  digitos = re.sub(r"[\s.\-]", "", texto or "")
  if not digitos.isdigit() or len(digitos) not in (6, 8, 10):
    raise ValueError("Escribe la subpartida con 6, 8 o 10 dígitos, por ejemplo 6109.10.00.00")
  return digitos


# ---------------------------------------------------------------- lectura de las páginas
def _texto(fragmento):
  return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", fragmento))).strip()


def _filas(contenido):
  """Celdas de cada fila del cuerpo (tbody) de las tablas de datos de una ventana de la DIAN."""
  filas = []
  for cuerpo in re.findall(r"(?is)<tbody>(.*?)</tbody>", contenido):
    for fila in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", cuerpo):
      celdas = [_texto(c) for c in re.findall(r"(?is)<td[^>]*>(.*?)</td>", fila)]
      if celdas:
        filas.append(celdas)
  return filas


def _fecha(texto):
  m = re.fullmatch(r"(\d{1,2})-([a-záéíóú]{3})[a-z]*-(\d{4})", (texto or "").strip().lower())
  if not m or m.group(2) not in MESES:
    return None  # "..." = sin fecha de fin
  return date(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))


def _porcentaje(texto):
  m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", texto or "")
  return float(m.group(1).replace(",", ".")) if m else None


def vigente(desde, hasta, hoy):
  return (desde is None or desde <= hoy) and (hasta is None or hasta >= hoy)


def leer_gravamen(contenido):
  tarifas = []
  for c in _filas(contenido):
    if len(c) >= 4 and _porcentaje(c[1]) is not None:
      tarifas.append(Tarifa(c[0].upper(), _porcentaje(c[1]), _fecha(c[2]), _fecha(c[3])))
  return tarifas


def leer_iva(contenido):
  opciones = []
  for c in _filas(contenido):
    if len(c) >= 5:
      producto, tarifa, desde, hasta = c[0], c[1], c[2], c[3]
    elif len(c) == 4:
      producto, (tarifa, desde, hasta) = "", c[:3]
    else:
      continue
    pct = _porcentaje(tarifa)
    if pct is not None:
      etiqueta = "EXENTO" if "EXENTO" in tarifa.upper() else "EXCLUIDO" if "EXCLUIDO" in tarifa.upper() else ""
      opciones.append(OpcionIva(producto, pct, etiqueta, _fecha(desde), _fecha(hasta)))
  return opciones


def leer_acuerdos(contenido):
  acuerdos = []
  for c in _filas(contenido):
    if len(c) >= 9 and "GRAVAMEN" in c[2].upper() and _porcentaje(c[3]) is not None:
      acuerdos.append(Acuerdo(c[0], c[1], _porcentaje(c[3]), _fecha(c[6]), _fecha(c[7])))
  return acuerdos


def _campo(contenido, nombre):
  m = re.search(r'id="vistaPerfilMercancia:formPerfilMercancia:%s"[^>]*value="([^"]*)"' % nombre, contenido)
  return html.unescape(m.group(1)) if m else None


def leer_perfil(contenido):
  """(ide, codigo, fecha, descripción) del perfil de la mercancía, o None si no existe."""
  ide, codigo, fecha = _campo(contenido, "strNomenclatura"), _campo(contenido, "codNomenclatura"), \
      _campo(contenido, "strFechaConsulta")
  if not (ide and codigo and fecha):
    return None
  limpio = re.sub(r"(?is)<(script|style).*?</\1>", " ", contenido)
  texto = _texto(limpio).replace("\xad", "")
  i, j = texto.find("Descripción"), texto.find("Unidad física")
  descripcion = texto[i + len("Descripción"):j] if 0 <= i < j else ""
  descripcion = re.sub(r"\s*\d{1,2}-[a-z]{3}-\d{4}\s*(\.\.\.|\d{1,2}-[a-z]{3}-\d{4})?\s*$", "", descripcion.strip())
  return ide, codigo, fecha, descripcion.strip()


# ---------------------------------------------------------------- cliente
class ClienteDian:
  def __init__(self, sesion=None, reloj=time.monotonic):
    if sesion is None:
      import requests
      sesion = requests.Session()
      sesion.headers["User-Agent"] = "Mozilla/5.0 (FronteraIQ consulta de arancel)"
    self.sesion = sesion
    self._reloj = reloj
    self._ocultos = None
    self._ocultos_hasta = 0.0
    self._bloqueo = threading.Lock()
    self._reintentar_desde = 0.0

  def _get(self, url):
    try:
      r = self.sesion.get(url, timeout=(5, 15))
      r.raise_for_status()
      return r.text
    except Exception as error:
      self._reintentar_desde = self._reloj() + ESPERA_TRAS_FALLO_S
      raise DianNoDisponible(str(error)) from error

  def _estado_formulario(self):
    with self._bloqueo:
      if self._ocultos is None or self._reloj() > self._ocultos_hasta:
        pagina = self._get(PAGINA)
        ocultos = {}
        for etiqueta in re.findall(r"<input[^>]*>", pagina):
          if 'type="hidden"' in etiqueta:
            n = re.search(r'name="([^"]*)"', etiqueta)
            v = re.search(r'value="([^"]*)"', etiqueta)
            if n:
              ocultos[html.unescape(n.group(1))] = html.unescape(v.group(1)) if v else ""
        if not ocultos:
          raise DianNoDisponible("La página de la DIAN cambió de formato")
        self._ocultos, self._ocultos_hasta = ocultos, self._reloj() + 600
      return dict(self._ocultos)

  def perfil(self, codigo):
    """Perfil de la subpartida (para un código corto, el de su primera subdivisión) o None."""
    if self._reloj() < self._reintentar_desde:
      raise DianNoDisponible("La DIAN no respondió hace poco; se reintentará en un minuto")
    datos = self._estado_formulario()
    datos[FORM + "codNomenclatura"] = codigo
    datos[FORM + "btConsultarNomenclatura.x"] = "5"
    datos[FORM + "btConsultarNomenclatura.y"] = "5"
    try:
      r = self.sesion.post(PAGINA, data=datos, timeout=(5, 15))
      r.raise_for_status()
    except Exception as error:
      self._reintentar_desde = self._reloj() + ESPERA_TRAS_FALLO_S
      raise DianNoDisponible(str(error)) from error
    perfil = leer_perfil(r.text)
    if perfil is None:
      return None
    ide, cod, fecha, descripcion = perfil
    if len(codigo) == 10 and cod != codigo:
      return None
    return {"id": ide, "codigo": cod, "fecha": fecha, "descripcion": descripcion}

  def consultar(self, codigo, hoy=None):
    """ConsultaArancel de una subpartida de 10 dígitos, o None si no existe."""
    hoy = hoy or date.today()
    p = self.perfil(codigo)
    if p is None:
      return None

    def ventana(pagina, componente):
      return self._get(f"{BASE}/{pagina}.faces?nomenclatura={p['id']}&codNomenclatura={p['codigo']}"
                       f"&componente={componente}&regimen=1&fechaConsulta={p['fecha']}"
                       "&modoPresentacionSeleccionBO=dialogo")

    gravamen = [t for t in leer_gravamen(ventana("DefGravamenPopUp", 3)) if vigente(t.desde, t.hasta, hoy)]
    general = next((t.porcentaje for t in gravamen if t.concepto == "GRAVAMEN ARANCELARIO"), None)
    variable = next((t.porcentaje for t in gravamen if "VARIABLE" in t.concepto), None)
    iva = [o for o in leer_iva(ventana("DefIvaPopUp", 4)) if vigente(o.desde, o.hasta, hoy)]
    acuerdos = [a for a in leer_acuerdos(ventana("DefTarifasAcuerdoPopUp", 6)) if vigente(a.desde, a.hasta, hoy)]
    if general is None or not iva:
      raise DianNoDisponible("No se pudo leer la tarifa de la DIAN para esa subpartida")
    return ConsultaArancel(p["codigo"], p["descripcion"], p["fecha"], general, variable,
                           tuple(iva), tuple(acuerdos))

  def subdivisiones(self, prefijo):
    """[(codigo, descripcion)] de las subpartidas de 10 dígitos que empiezan por un código de 6 u 8 cifras."""
    with ThreadPoolExecutor(HILOS) as pool:
      if len(prefijo) == 6:
        primeras = pool.map(lambda mm: self.perfil(f"{prefijo}{mm:02d}"), range(100))
        prefijos8 = sorted({p["codigo"][:8] for p in primeras if p and p["codigo"].startswith(prefijo)})
      else:
        prefijos8 = [prefijo]
      candidatos = [f"{p8}{ss:02d}" for p8 in prefijos8 for ss in range(100)]
      perfiles = pool.map(self.perfil, candidatos)
      return sorted({(p["codigo"], p["descripcion"]) for p in perfiles if p})
