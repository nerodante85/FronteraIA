"""Asistente de INCOTERM del módulo DFI (puro, sin Streamlit)."""
import itertools

import pytest

import dfi


def test_todo_si_sugiere_ddp():
  assert dfi.sugerir_incoterm(True, True, True, True) == ("DDP",)


def test_si_no_puede_tramitar_la_importacion_sugiere_dap_o_dpu():
  assert dfi.sugerir_incoterm(True, True, True, False) == ("DAP", "DPU")


@pytest.mark.parametrize("respuestas", list(itertools.product([True, False], repeat=4)))
def test_toda_combinacion_tiene_sugerencia_conocida(respuestas):
  codigos = dfi.sugerir_incoterm(*respuestas)
  assert codigos and all(c in dfi.DESCRIPCION_INCOTERM for c in codigos)


def test_solo_ddp_exige_asumir_todo_hasta_el_comprador():
  # Con "No" a la primera pregunta nunca se sugiere un término de la familia D.
  for resto in itertools.product([True, False], repeat=3):
    assert not {"DAP", "DPU", "DDP"} & set(dfi.sugerir_incoterm(False, *resto))


def test_los_once_incoterms_2020_tienen_descripcion():
  assert set(dfi.DESCRIPCION_INCOTERM) == {
      "EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"}
