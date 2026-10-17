// Webhook de Wompi: recibe pagos aprobados y crea o renueva la licencia.
//
// Secretos requeridos (supabase secrets set ...):
//   WOMPI_EVENTS_SECRET  secreto de eventos de Wompi (panel de Wompi > Desarrolladores)
//   RESEND_API_KEY       clave de Resend para enviar correos (opcional al inicio)
//   MAIL_FROM            remitente verificado en Resend
//   ADMIN_EMAIL          correo donde recibes el aviso de cada pago
// SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY ya existen dentro de las Edge Functions.
//
// IMPORTANTE: verifica el formato del checksum contra la documentación vigente de
// Wompi antes de publicar (https://docs.wompi.co/docs/colombia/eventos/).
import { createClient } from "npm:@supabase/supabase-js@2";

const ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

async function sha256(texto: string): Promise<string> {
  const datos = new TextEncoder().encode(texto);
  const hash = await crypto.subtle.digest("SHA-256", datos);
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Misma normalización que licencias.py: sin espacios y en mayúsculas.
function normalizarClave(clave: string): string {
  return clave.replace(/\s+/g, "").toUpperCase();
}

function generarClave(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(12));
  const letras = Array.from(bytes).map((b) => ALFABETO[b % ALFABETO.length]);
  return "FIQ-" + [0, 4, 8].map((i) => letras.slice(i, i + 4).join("")).join("-");
}

function valorEn(obj: any, ruta: string): unknown {
  return ruta.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

function igualesEnTiempoConstante(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diferencia = 0;
  for (let i = 0; i < a.length; i++) diferencia |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diferencia === 0;
}

async function enviarCorreo(para: string, asunto: string, texto: string): Promise<boolean> {
  const apiKey = Deno.env.get("RESEND_API_KEY");
  const de = Deno.env.get("MAIL_FROM");
  if (!apiKey || !de) return false;
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: de, to: [para], subject: asunto, text: texto }),
  });
  return r.ok;
}

const respuesta = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } });

Deno.serve(async (req) => {
  if (req.method !== "POST") return respuesta({ error: "Método no permitido" }, 405);

  const secreto = Deno.env.get("WOMPI_EVENTS_SECRET");
  if (!secreto) return respuesta({ error: "Webhook sin configurar" }, 500);

  let evento: any;
  try {
    evento = await req.json();
  } catch {
    return respuesta({ error: "JSON inválido" }, 400);
  }

  // 1) Firma: SHA-256(valores de las propiedades + timestamp + secreto de eventos).
  const propiedades: string[] = evento?.signature?.properties ?? [];
  const concatenado = propiedades.map((p) => String(valorEn(evento.data, p) ?? "")).join("");
  const esperado = await sha256(concatenado + String(evento?.timestamp ?? "") + secreto);
  const recibido = String(evento?.signature?.checksum ?? "").toLowerCase();
  if (!propiedades.length || !igualesEnTiempoConstante(esperado, recibido)) {
    return respuesta({ error: "Firma inválida" }, 401);
  }

  // 2) Solo transacciones aprobadas; el resto se confirma sin hacer nada.
  const tx = evento?.data?.transaction;
  if (evento.event !== "transaction.updated" || tx?.status !== "APPROVED") {
    return respuesta({ ignorado: true });
  }

  const correo = String(tx.customer_email ?? "").trim().toLowerCase();
  if (!correo) return respuesta({ error: "El pago no trae correo del cliente" }, 422);

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  // 3) Registrar el pago. La base valida el monto contra la tabla de planes.
  const clave = generarClave();
  const { data, error } = await supabase.rpc("registrar_pago", {
    p_transaccion: String(tx.id),
    p_email: correo,
    p_cliente: tx.customer_data?.full_name ?? null,
    p_monto: Number(tx.amount_in_cents),
    p_clave_hash: await sha256(normalizarClave(clave)),
  });
  // Un error de base devuelve 500 para que Wompi reintente (la operación es idempotente).
  if (error) return respuesta({ error: error.message }, 500);

  const admin = Deno.env.get("ADMIN_EMAIL");
  if (!data.ok) {
    if (admin) {
      await enviarCorreo(admin, "FronteraIQ: pago sin plan reconocido",
        `Transacción ${tx.id} por ${tx.amount_in_cents} centavos de ${correo}. Motivo: ${data.motivo}. Revísalo a mano.`);
    }
    return respuesta({ ok: false, motivo: data.motivo });
  }
  if (data.duplicado) return respuesta({ ok: true, duplicado: true });

  // 4) Entrega: clave nueva o aviso de renovación.
  const vence = String(data.vence_el).slice(0, 10);
  let entregada = true;
  if (data.nueva) {
    entregada = await enviarCorreo(
      correo,
      "Tu licencia de FronteraIQ Pro",
      `Hola,\n\nRecibimos tu pago. Tu clave de licencia es: ${clave}\n\n` +
        `Entra a la app, elige "Pro / Premium" en la barra lateral e ingresa la clave.\n` +
        `Tu plan está activo hasta el ${vence}.\n\nCualquier duda, responde este correo.`,
    );
    if (admin) {
      // El aviso al administrador incluye la clave para poder reenviarla por WhatsApp.
      await enviarCorreo(admin, `FronteraIQ: nuevo cliente ${correo}`,
        `Plan ${data.nivel}, vence ${vence}. Clave: ${clave}. Correo al cliente: ${entregada ? "enviado" : "NO enviado"}.`);
    }
  } else {
    entregada = await enviarCorreo(
      correo,
      "Renovamos tu licencia de FronteraIQ Pro",
      `Recibimos tu pago. Tu licencia sigue siendo la misma y ahora está activa hasta el ${vence}.`,
    );
    if (admin) await enviarCorreo(admin, `FronteraIQ: renovación de ${correo}`, `Vence ${vence}.`);
  }
  if (entregada || !data.nueva) {
    await supabase.rpc("marcar_entregada", { p_licencia: data.licencia_id });
  }
  return respuesta({ ok: true, nueva: data.nueva });
});
