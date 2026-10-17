"""Licencia Pro: la clave no vive en el código y se valida contra la configuración."""
from pathlib import Path

from conftest import APP_PATH


def _abrir_pro(at, clave):
  at.sidebar.radio[0].set_value("Pro / Premium").run()
  at.sidebar.text_input[0].set_value(clave).run()
  return at


def test_sin_clave_configurada_pro_no_se_activa(nueva_app):
  at = _abrir_pro(nueva_app(), "cualquier-cosa")
  assert not at.sidebar.success
  assert any("no están configuradas" in e.value for e in at.sidebar.error)


def test_clave_incorrecta_no_activa(monkeypatch, nueva_app):
  monkeypatch.setenv("PRO_LICENSE_KEY", "clave-de-prueba")
  at = _abrir_pro(nueva_app(), "otra-clave")
  assert not at.sidebar.success
  assert any("no válida" in w.value for w in at.sidebar.warning)


def test_clave_correcta_activa_pro(app_pro):
  assert app_pro.sidebar.success
  assert len(app_pro.get("download_button")) == 2  # PDF y CSV


def test_la_clave_antigua_ya_no_existe(nueva_app):
  assert "PRO2026" not in Path(APP_PATH).read_text(encoding="utf-8")
  at = _abrir_pro(nueva_app(), "PRO2026")
  assert not at.sidebar.success
