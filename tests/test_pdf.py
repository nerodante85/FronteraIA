"""El PDF Pro no debe romper la página con texto libre."""
import pytest

from conftest import numero


@pytest.mark.parametrize(
    "nombre",
    ["Camisetas de algodón", "Camisetas – verano", "Perfume €50", "Camisetas 👕", "Niño ñandú", "../../etc/passwd"],
)
def test_pdf_pro_con_nombres_especiales(app_pro, nombre):
  app_pro.selectbox[0].set_value("Personalizado / Otra partida").run()
  campo = next(t for t in app_pro.text_input if t.label == "Nombre / Referencia")
  campo.set_value(nombre).run()
  assert not app_pro.exception
  assert len(app_pro.get("download_button")) == 2


def test_pdf_pro_con_partida_de_la_tabla(app_pro):
  app_pro.selectbox[0].set_value("Calzado con Suela de Caucho / Cuero").run()
  assert not app_pro.exception
  assert len(app_pro.get("download_button")) == 2


def test_plan_gratuito_solo_tiene_csv(nueva_app):
  at = nueva_app()
  assert len(at.get("download_button")) == 1


def test_datos_extremos_no_rompen(app_pro):
  numero(app_pro, "Cantidad de Unidades").set_value(1).run()
  assert not app_pro.exception
