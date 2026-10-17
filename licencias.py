"""Licencias por cliente de FronteraIQ Pro.

Este módulo no depende de Streamlit para poder probarse de forma aislada.
La clave nunca viaja ni se guarda en claro en la base de datos: se normaliza
(mayúsculas, sin espacios) y solo se envía/almacena su hash SHA-256.
"""
import hashlib
import secrets

import requests

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O/1/I para evitar confusiones
TIEMPO_ESPERA_S = 8


def normalizar_clave(clave):
  """Mayúsculas y sin espacios, igual que la función del webhook."""
  return "".join(str(clave).split()).upper()


def hash_clave(clave):
  return hashlib.sha256(normalizar_clave(clave).encode("utf-8")).hexdigest()


def generar_clave():
  """Clave aleatoria con formato FIQ-XXXX-XXXX-XXXX."""
  grupos = ["".join(secrets.choice(ALFABETO) for _ in range(4)) for _ in range(3)]
  return "FIQ-" + "-".join(grupos)


def validar_licencia(clave, sesion, url, service_key):
  """Consulta la función `validar_licencia` de Supabase.

  Devuelve un dict con `valida` (bool) y, según el caso, `motivo`, `nivel`,
  `vence_el` y `cliente`. Si el servicio falla, LANZA la excepción: quien llama
  decide mostrar un aviso y no activar Pro (falla cerrada) sin cachear el error.
  """
  respuesta = requests.post(
      url.rstrip("/") + "/rest/v1/rpc/validar_licencia",
      headers={
          "apikey": service_key,
          "Authorization": "Bearer " + service_key,
          "Content-Type": "application/json",
      },
      json={"p_hash": hash_clave(clave), "p_sesion": sesion},
      timeout=TIEMPO_ESPERA_S,
  )
  respuesta.raise_for_status()
  datos = respuesta.json()
  if not isinstance(datos, dict) or "valida" not in datos:
    raise ValueError("Respuesta inesperada del servicio de licencias")
  return datos


MENSAJES = {
    "no_encontrada": "⚠️ Clave de licencia no válida.",
    "revocada": "⚠️ Esta licencia fue revocada. Escríbenos por WhatsApp para resolverlo.",
    "vencida": "⚠️ Tu licencia venció. Renueva tu plan para seguir usando Pro.",
    "sin_puestos": "⚠️ Esta licencia ya está en uso por el máximo de usuarios simultáneos.",
    "servicio_no_disponible": "No pudimos verificar tu licencia ahora. Intenta de nuevo en unos minutos.",
}


def mensaje_de_rechazo(motivo):
  return MENSAJES.get(motivo, MENSAJES["no_encontrada"])
