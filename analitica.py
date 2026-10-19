"""Medición de uso anónima de FronteraIQ.

Solo registra QUÉ ocurrió (un evento de una lista cerrada) y un identificador de sesión
aleatorio que se genera al abrir la app. No guarda nombres, correos, montos ni datos de la
cotización. Nunca interrumpe ni retrasa la app: corre en segundo plano y los errores se
ignoran. Sin configuración de Supabase no hace nada.
"""
import threading

import requests

TIEMPO_ESPERA_S = 3

EVENTOS = frozenset({
    "landing_vista", "calculadora_vista", "partida_elegida",
    "descarga_pdf", "descarga_csv", "descarga_csv_embarque",
    "multimercancia_vista", "multimercancia_teaser", "licencia_pro_activada",
})


def _enviar(evento, sesion, url, llave, dato):
  encabezados = {"apikey": llave, "Content-Type": "application/json"}
  if not llave.startswith("sb_"):
    encabezados["Authorization"] = "Bearer " + llave
  try:
    requests.post(
        url.rstrip("/") + "/rest/v1/rpc/registrar_evento",
        headers=encabezados,
        json={"p_sesion": sesion, "p_evento": evento, "p_dato": dato},
        timeout=TIEMPO_ESPERA_S,
    )
  except Exception:
    pass  # la medición jamás debe afectar al usuario


def registrar(evento, sesion, config, dato=None, en_segundo_plano=True):
  """Registra un evento. `config` es (url, llave) o None. Devuelve True si lo envió."""
  if not config or evento not in EVENTOS or not sesion:
    return False
  url, llave = config
  dato = None if dato is None else str(dato)[:40]
  if en_segundo_plano:
    threading.Thread(target=_enviar, args=(evento, sesion, url, llave, dato), daemon=True).start()
  else:
    _enviar(evento, sesion, url, llave, dato)
  return True
