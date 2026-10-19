# Medición de uso anónima

Responde tres preguntas: ¿cuánta gente llega?, ¿cuántos calculan?, ¿cuántos descargan o miran lo Pro?

## Qué se registra
Un evento de una lista cerrada (`analitica.EVENTOS`) y un identificador de sesión aleatorio
que se crea al abrir la app. Una vez por sesión y evento.

| Evento | Cuándo |
| --- | --- |
| `landing_vista` | Se abre la página de inicio |
| `calculadora_vista` | Se abre la calculadora |
| `partida_elegida` | Se elige una partida de la tabla (dato: subpartida) |
| `descarga_pdf`, `descarga_csv`, `descarga_csv_embarque` | Se pulsa el botón de descarga |
| `multimercancia_vista` / `multimercancia_teaser` | Un usuario Pro / gratis llega a la sección multimercancía |
| `licencia_pro_activada` | Una licencia Pro válida se activa |

**No se registra:** nombre, correo, IP, montos, productos escritos por el usuario ni la clave de licencia.
Actualiza la política de privacidad para mencionar esta medición.

## Activarla
1. Aplicar `supabase/migrations/20261019000000_eventos.sql` (SQL Editor de Supabase).
2. Usa los mismos secrets `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` de las licencias. Sin ellos no hace nada.

## Consultarla (SQL Editor)
```sql
select * from resumen_uso(30);   -- sesiones únicas por día y evento
select purgar_eventos(180);      -- borra eventos de más de 180 días
```
Embudo básico: `landing_vista` → `calculadora_vista` → `descarga_csv`/`descarga_pdf`.
Si `multimercancia_teaser` es alto y nadie pasa a pagar, la función despierta interés pero el plan no convence.
