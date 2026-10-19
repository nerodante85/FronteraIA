from dian_verificador import comparar, porcentajes_gravamen, porcentajes_iva

GRAVAMEN = ("<html><body><table><tr><td>GRAVAMEN ARANCELARIO</td><td>40 %</td><td>08-ene-2023</td>"
            "<td>...</td></tr></table><script>var x = '99 %';</script></body></html>")
GRAVAMEN_VARIABLE = ("GRAVAMEN ARANCELARIO 15% 01-ene-2017 ... ARANCEL VARIABLE 33 % 16-oct-2026 31-oct-2026")
IVA_CONDICIONAL = ("<td>Excepto portátiles ≤ 50 UVT</td><td>19.0 %</td><td>Portátiles</td><td>0.0 % - EXCLUIDO</td>")


def test_lee_el_gravamen_arancelario_e_ignora_scripts_y_arancel_variable():
  assert porcentajes_gravamen(GRAVAMEN) == [40.0]
  assert porcentajes_gravamen(GRAVAMEN_VARIABLE) == [15.0]


def test_lee_todas_las_tarifas_de_iva_con_decimales():
  assert porcentajes_iva(IVA_CONDICIONAL) == [19.0, 0.0]


def _v(arancel, iva):
  return {"A.0": {"producto": "A", "arancel": arancel, "iva": iva}}


def test_sin_diferencias_cuando_coincide():
  assert comparar(_v(40.0, 19.0), lambda c: {"gravamen": [40.0], "iva": [19.0]}) == []


def test_iva_condicional_coincide_con_cualquiera_de_sus_tarifas():
  assert comparar(_v(0.0, 0.0), lambda c: {"gravamen": [0.0], "iva": [19.0, 0.0]}) == []


def test_reporta_arancel_distinto():
  d = comparar(_v(35.0, 19.0), lambda c: {"gravamen": [15.0], "iva": [19.0]})
  assert len(d) == 1 and "arancel 35 %" in d[0]


def test_reporta_subpartida_inexistente_y_lectura_vacia():
  assert "ya no existe" in comparar(_v(1.0, 1.0), lambda c: None)[0]
  d = comparar(_v(1.0, 1.0), lambda c: {"gravamen": [], "iva": []})
  assert len(d) == 2


def test_un_csv_sin_partidas_validadas_no_da_exito(tmp_path, capsys):
  from dian_verificador import main
  csv = tmp_path / "v.csv"
  csv.write_text("producto,subpartida,arancel_app_pct,iva_app_pct,arancel_validado_pct,iva_validado_pct,"
                 "condiciones_especiales,fuente_normativa,fecha_vigencia,validado_por,observaciones\n"
                 "A,6109.10.00.00,40,19,,,,,,,\n", encoding="utf-8")
  assert main(str(csv)) == 2
