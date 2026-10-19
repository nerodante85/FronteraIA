"""Consulta en vivo del Arancel de la DIAN, con páginas simuladas que imitan el formato real."""
from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

import dian_arancel as d
from conftest import APP_PATH

HOY = date(2026, 10, 19)


def _tabla(*filas):
  celdas = "".join("<tr>" + "".join(f'<td class="tdtextoAncho300"><span>{c}</span></td>' for c in f) + "</tr>"
                   for f in filas)
  return f"<html><body><table><thead><tr><th>x</th></tr></thead><tbody>{celdas}</tbody></table>" \
         "<script>var z = '99 %';</script></body></html>"


GRAVAMEN = _tabla(["GRAVAMEN ARANCELARIO", "15 %", "01-ene-2017", "...", "Dec.1881"],
                  ["ARANCEL VARIABLE", "33 %", "16-oct-2026", "31-oct-2026", "Dec.1"],
                  ["ARANCEL VARIABLE", "20 %", "01-ene-2026", "15-oct-2026", "Dec.1"])
IVA = _tabla(["Portátiles hasta 50 UVT", "0.0 % - EXCLUIDO", "01-ene-2020", "...", "Ley 2010"],
             ["Los demás", "19.0 %", "01-ene-2020", "...", "Ley 2010"])
IVA_UNICO = _tabla(["19.0 %", "01-ene-2020", "...", "Ley 2010"])
ACUERDOS = _tabla(["UE-Colombia", "ALEMANIA", "GRAVAMEN ARANCELARIO", "0 %", "1", "0", "01-ene-2013", "...", "L"],
                  ["Mercosur", "BRASIL", "GRAVAMEN ARANCELARIO", "5 %", "1", "0", "01-ene-2013", "30-dic-2020", "L"])


def perfil(codigo, descripcion="Camisetas de algodón"):
  campos = "".join(f'<input type="hidden" id="vistaPerfilMercancia:formPerfilMercancia:{n}" value="{v}"/>'
                   for n, v in (("strNomenclatura", "777"), ("codNomenclatura", codigo),
                                ("strFechaConsulta", "20261019")))
  return (f"<html><head><script>var Descripción = 1;</script></head><body>{campos}"
          f"<span>Descripción</span><span>{descripcion}</span><span>Unidad física</span></body></html>")


class Respuesta:
  def __init__(self, texto, error=False):
    self.text, self._error = texto, error

  def raise_for_status(self):
    if self._error:
      raise RuntimeError("503")


class SesionFalsa:
  def __init__(self, existentes=("6109100010",), caida=False, iva=IVA):
    self.existentes, self.caida, self.iva, self.posts = set(existentes), caida, iva, 0

  def get(self, url, timeout=None):
    if self.caida:
      return Respuesta("", True)
    if "DefConsultaGeneral" in url:
      return Respuesta('<input type="hidden" name="javax.faces.ViewState" value="s1"/>')
    for clave, texto in (("DefGravamenPopUp", GRAVAMEN), ("DefIvaPopUp", self.iva),
                         ("DefTarifasAcuerdoPopUp", ACUERDOS)):
      if clave in url:
        return Respuesta(texto)
    raise AssertionError(url)

  def post(self, url, data=None, timeout=None):
    self.posts += 1
    if self.caida:
      return Respuesta("", True)
    codigo = data[d.FORM + "codNomenclatura"]
    primero = next((e for e in sorted(self.existentes) if e.startswith(codigo)), None)
    if primero:  # un código corto devuelve su primera subdivisión
      return Respuesta(perfil(primero))
    return Respuesta("<html>No existen nomenclaturas</html>")


def test_normaliza_codigos_y_rechaza_los_invalidos():
  assert d.normalizar_codigo("6109.10.00.00") == "6109100000"
  assert d.normalizar_codigo(" 6109 10 ") == "610910"
  for malo in ("", "61091", "abcdefghij", "6109.10.00.0"):
    with pytest.raises(ValueError):
      d.normalizar_codigo(malo)
  assert d.formatear_codigo("6109100000") == "6109.10.00.00"


def test_lee_gravamen_iva_y_acuerdos_ignorando_scripts():
  g = d.leer_gravamen(GRAVAMEN)
  assert [(t.concepto, t.porcentaje) for t in g][:2] == [("GRAVAMEN ARANCELARIO", 15.0), ("ARANCEL VARIABLE", 33.0)]
  assert g[1].desde == date(2026, 10, 16) and g[0].hasta is None
  iva = d.leer_iva(IVA)
  assert [(o.porcentaje, o.etiqueta) for o in iva] == [(0.0, "EXCLUIDO"), (19.0, "")]
  assert d.leer_iva(IVA_UNICO)[0].porcentaje == 19.0 and d.leer_iva(IVA_UNICO)[0].producto == ""
  assert [(a.pais, a.porcentaje) for a in d.leer_acuerdos(ACUERDOS)] == [("ALEMANIA", 0.0), ("BRASIL", 5.0)]


def test_consulta_aplica_arancel_variable_solo_si_esta_vigente_y_filtra_acuerdos_vencidos():
  c = d.ClienteDian(SesionFalsa()).consultar("6109100010", HOY)
  assert (c.arancel_general, c.arancel_variable, c.arancel_aplicable) == (15.0, 33.0, 33.0)
  assert c.descripcion == "Camisetas de algodón" and c.codigo == "6109100010"
  assert [a.pais for a in c.acuerdos] == ["ALEMANIA"]  # el de Brasil venció
  assert max(o.porcentaje for o in c.iva) == 19.0
  fuera = d.ClienteDian(SesionFalsa()).consultar("6109100010", date(2026, 11, 20))
  assert fuera.arancel_variable is None and fuera.arancel_aplicable == 15.0


def test_subpartida_inexistente_da_none_y_subdivisiones_se_enumeran():
  cliente = d.ClienteDian(SesionFalsa(existentes=("6109100010", "6109100090")))
  assert cliente.consultar("6109100099", HOY) is None
  assert [c for c, _ in cliente.subdivisiones("61091000")] == ["6109100010", "6109100090"]
  assert [c for c, _ in cliente.subdivisiones("610910")] == ["6109100010", "6109100090"]


def test_dian_caida_lanza_error_y_espera_antes_de_reintentar():
  t = [0.0]
  sesion = SesionFalsa(caida=True)
  cliente = d.ClienteDian(sesion, reloj=lambda: t[0])
  with pytest.raises(d.DianNoDisponible):
    cliente.consultar("6109100010", HOY)
  sesion.caida = False
  with pytest.raises(d.DianNoDisponible, match="reintentar"):
    cliente.consultar("6109100010", HOY)
  t[0] = 100
  assert cliente.consultar("6109100010", HOY) is not None


def test_lectura_sin_iva_no_se_da_por_buena():
  with pytest.raises(d.DianNoDisponible):
    d.ClienteDian(SesionFalsa(iva="<html></html>")).consultar("6109100010", HOY)


# ---------------------------------------------------------------- en la calculadora
def _consulta(**extra):
  base = dict(codigo="6109100010", descripcion="Camisetas de algodón", fecha_consulta="20261019",
              arancel_general=15.0, arancel_variable=None,
              iva=(d.OpcionIva("", 19.0, "", None, None),), acuerdos=())
  base.update(extra)
  return d.ConsultaArancel(**base)


def _app(monkeypatch, consulta, error=None):
  def falsa(self, codigo, hoy=None):
    if error:
      raise error
    return consulta
  monkeypatch.setattr(d.ClienteDian, "consultar", falsa)
  at = AppTest.from_file(APP_PATH, default_timeout=60).run()
  at.selectbox[0].set_value("Personalizado / Otra partida").run()
  return at


def _escribir(at, texto):
  caja = next(t for t in at.text_input if t.label.startswith("Subpartida Arancelaria"))
  caja.set_value(texto).run()
  return at


def test_calculadora_trae_arancel_e_iva_de_la_dian(nueva_app, monkeypatch):
  at = _escribir(_app(monkeypatch, _consulta(arancel_general=40.0)), "6109.10.00.10")
  assert not at.exception
  assert next(n for n in at.number_input if n.label == "Arancel (%)").value == 40.0
  assert next(n for n in at.number_input if n.label == "IVA (%)").value == 19.0
  assert any("Camisetas de algodón" in c.value for c in at.caption)


def test_arancel_variable_y_acuerdo_por_pais(nueva_app, monkeypatch):
  c = _consulta(arancel_general=15.0, arancel_variable=33.0,
                acuerdos=(d.Acuerdo("UE-Colombia", "ALEMANIA", 0.0, None, None),))
  at = _escribir(_app(monkeypatch, c), "6109100010")
  assert any("Arancel variable vigente: 33 %" in i.value for i in at.info)
  assert next(n for n in at.number_input if n.label == "Arancel (%)").value == 33.0
  sel = next(s for s in at.selectbox if s.label.startswith("País de origen"))
  sel.select_index(1).run()
  assert next(n for n in at.number_input if n.label == "Arancel (%)").value == 0.0
  assert any("certificado de origen" in x.value for x in at.caption)


def test_iva_condicional_propone_el_mas_alto(nueva_app, monkeypatch):
  c = _consulta(iva=(d.OpcionIva("Portátiles hasta 50 UVT", 0.0, "EXCLUIDO", None, None),
                     d.OpcionIva("Los demás", 19.0, "", None, None)))
  at = _escribir(_app(monkeypatch, c), "6109100010")
  assert next(n for n in at.number_input if n.label == "IVA (%)").value == 19.0
  assert any(s.label.startswith("IVA según") for s in at.selectbox)


def test_si_la_dian_falla_se_puede_ingresar_a_mano(nueva_app, monkeypatch):
  at = _escribir(_app(monkeypatch, None, d.DianNoDisponible("caída")), "6109100010")
  assert not at.exception
  assert any("No pude consultar la DIAN" in w.value for w in at.warning)
  assert next(n for n in at.number_input if n.label == "Arancel (%)").value == 10.0


def test_codigo_invalido_y_subpartida_inexistente(nueva_app, monkeypatch):
  at = _escribir(_app(monkeypatch, None), "123")
  assert any("6, 8 o 10 dígitos" in e.value for e in at.error)
  at = _escribir(_app(monkeypatch, None), "6109100010")
  assert any("6109.10.00.10 no existe" in e.value and "6 u 8 dígitos" in e.value for e in at.error)


def test_con_una_sola_subdivision_no_se_pide_elegir(monkeypatch):
  monkeypatch.setattr(d.ClienteDian, "subdivisiones", lambda self, p: [("6109100000", "Camisetas")])
  at = _app(monkeypatch, _consulta(codigo="6109100000"))
  at = _escribir(at, "610910")
  assert not any(s.label == "Subdivisión" for s in at.selectbox)
  assert any("6109.10.00.00" in c.value for c in at.caption)
