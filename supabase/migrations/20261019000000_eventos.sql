-- Medición de uso anónima. Sin datos personales: evento de lista cerrada + sesión aleatoria.
-- Seguridad: RLS activado SIN políticas y funciones solo para service_role (igual que licencias).

create table public.eventos (
  id        bigint generated always as identity primary key,
  creado_el timestamptz not null default now(),
  sesion    text not null check (char_length(sesion) between 8 and 64),
  evento    text not null check (evento in (
              'landing_vista', 'calculadora_vista', 'partida_elegida',
              'descarga_pdf', 'descarga_csv', 'descarga_csv_embarque',
              'multimercancia_vista', 'multimercancia_teaser', 'licencia_pro_activada')),
  dato      text check (char_length(dato) <= 40)
);
create index eventos_creado_idx on public.eventos (creado_el);
alter table public.eventos enable row level security;

create or replace function public.registrar_evento(p_sesion text, p_evento text, p_dato text default null)
returns void
language sql
security definer
set search_path = public
as $$
  insert into public.eventos (sesion, evento, dato) values (p_sesion, p_evento, p_dato);
$$;

-- Sesiones únicas por día y evento (últimos p_dias días), en hora de Colombia.
create or replace function public.resumen_uso(p_dias int default 30)
returns table (dia date, evento text, sesiones bigint, eventos bigint)
language sql
security definer
set search_path = public
as $$
  select (creado_el at time zone 'America/Bogota')::date, evento,
         count(distinct sesion), count(*)
    from public.eventos
   where creado_el >= now() - make_interval(days => p_dias)
   group by 1, 2
   order by 1 desc, 2;
$$;

-- Retención: borra eventos de más de p_dias días (ejecutar de vez en cuando).
create or replace function public.purgar_eventos(p_dias int default 180)
returns bigint
language sql
security definer
set search_path = public
as $$
  with borrados as (
    delete from public.eventos where creado_el < now() - make_interval(days => p_dias) returning 1
  ) select count(*) from borrados;
$$;

revoke all on function public.registrar_evento(text, text, text) from public, anon, authenticated;
revoke all on function public.resumen_uso(int)                   from public, anon, authenticated;
revoke all on function public.purgar_eventos(int)                from public, anon, authenticated;
grant execute on function public.registrar_evento(text, text, text) to service_role;
grant execute on function public.resumen_uso(int)                   to service_role;
grant execute on function public.purgar_eventos(int)                to service_role;
