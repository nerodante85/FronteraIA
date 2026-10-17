# Licencias por cliente y cobro con Wompi

Reemplaza la clave única `PRO_LICENSE_KEY` por una licencia individual por cliente, con vencimiento, revocación y límite de usuarios simultáneos. **Es opcional**: si no se configuran `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`, la app sigue usando `PRO_LICENSE_KEY` como hasta ahora.

## Piezas

| Archivo | Qué hace |
|---|---|
| `supabase/migrations/20261017000000_licencias.sql` | Tablas `planes`, `licencias`, `pagos`, `sesiones` y funciones `validar_licencia`, `registrar_pago`, `marcar_entregada`, `regenerar_clave`. RLS activado sin políticas: solo la clave de servicio puede ejecutarlas. |
| `supabase/functions/wompi-webhook/index.ts` | Recibe el evento de Wompi, verifica la firma, registra el pago y entrega la clave por correo. |
| `licencias.py` | Genera claves, calcula su hash y valida contra Supabase desde la app. |
| `app.py` | Usa Supabase si está configurado; si el servicio falla, **no activa Pro** (falla cerrada). |

## Puesta en marcha (en este orden)

1. Crear el proyecto en Supabase. Verificar si el plan elegido se pausa por inactividad: si Pro depende de él, usar un plan que no se pause.
2. Ejecutar la migración SQL en el editor de SQL de Supabase.
3. Revisar en la tabla `planes` que los precios en centavos coincidan con los links de Wompi (39.000 COP = 3.900.000).
4. Publicar la función: `supabase functions deploy wompi-webhook --no-verify-jwt` (Wompi no envía el token de Supabase; la seguridad es la firma del evento).
5. Cargar los secretos: `WOMPI_EVENTS_SECRET`, `RESEND_API_KEY`, `MAIL_FROM`, `ADMIN_EMAIL`.
6. En el panel de Wompi, registrar la URL de eventos de la función.
7. En Streamlit Cloud (Secrets) agregar `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`. Esta última no se comparte ni se sube al repositorio.
8. Probar con una transacción de prueba de Wompi antes de vender.

## Operación

- **Alta o renovación:** automática al aprobarse el pago. El plan se identifica por el monto; un monto desconocido no crea licencia y te avisa por correo.
- **Revocar:** `update licencias set estado = 'revocada' where lower(contacto_email) = '...';`
- **Clave perdida o no entregada** (`entrega_pendiente = true`): generar una con `python -c "import licencias as l; k=l.generar_clave(); print(k, l.hash_clave(k))"` y ejecutar `select regenerar_clave('correo', '<hash>');`
- **Caché:** la app consulta Supabase cada 5 minutos por sesión; una revocación puede tardar ese tiempo en notarse.

## Pendiente antes de producción

- Confirmar con la documentación vigente de Wompi el formato de firma de eventos y el campo del correo del cliente.
- Política de privacidad y términos (Ley 1581 de 2012: se guardan nombre y correo).
- Confirmar con el contador la facturación electrónica de las suscripciones.
- Si un pago llega de una licencia revocada, la licencia sigue revocada: revisar manualmente.
