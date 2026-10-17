-- Licencias por cliente para FronteraIQ Pro.
-- Seguridad: RLS activado SIN políticas (nadie accede con las claves públicas)
-- y las funciones solo se pueden ejecutar con la clave de servicio (service_role).

create table public.planes (
  codigo          text primary key,
  nombre          text    not null,
  precio_centavos bigint  not null unique check (precio_centavos > 0),
  dias            int     not null check (dias > 0),
  puestos         int     not null check (puestos > 0),
  nivel           text    not null check (nivel in ('pro', 'agencia'))
);

-- Precios en centavos de peso, como los envía Wompi (amount_in_cents).
insert into public.planes (codigo, nombre, precio_centavos, dias, puestos, nivel) values
  ('pro_mensual',     'Pro Fronterizo mensual', 3900000,   30, 1, 'pro'),
  ('pro_anual',       'Pro Fronterizo anual',   39000000, 365, 1, 'pro'),
  ('agencia_mensual', 'Agencia / Corporativo',  14900000,  30, 5, 'agencia');

create table public.licencias (
  id                uuid primary key default gen_random_uuid(),
  cliente           text,
  contacto_email    text not null,
  plan              text not null references public.planes (codigo),
  nivel             text not null check (nivel in ('pro', 'agencia')),
  puestos           int  not null check (puestos > 0),
  clave_hash        text not null unique,   -- SHA-256 de la clave normalizada; nunca la clave
  estado            text not null default 'activa' check (estado in ('activa', 'revocada')),
  vence_el          timestamptz not null,
  entrega_pendiente boolean not null default false,
  creada_el         timestamptz not null default now(),
  actualizada_el    timestamptz not null default now()
);
create unique index licencias_email_unico on public.licencias (lower(contacto_email));

create table public.pagos (
  transaccion_id text primary key,          -- id de Wompi: evita procesar dos veces
  licencia_id    uuid not null references public.licencias (id),
  monto_centavos bigint not null,
  recibido_el    timestamptz not null default now()
);

create table public.sesiones (
  licencia_id      uuid not null references public.licencias (id) on delete cascade,
  sesion           text not null,
  ultima_actividad timestamptz not null default now(),
  primary key (licencia_id, sesion)
);

alter table public.planes    enable row level security;
alter table public.licencias enable row level security;
alter table public.pagos     enable row level security;
alter table public.sesiones  enable row level security;

-- Valida una clave (por su hash) y reserva un puesto de uso simultáneo.
create or replace function public.validar_licencia(p_hash text, p_sesion text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  l       public.licencias%rowtype;
  activas int;
begin
  select * into l from public.licencias where clave_hash = p_hash;
  if not found then
    return jsonb_build_object('valida', false, 'motivo', 'no_encontrada');
  end if;
  if l.estado <> 'activa' then
    return jsonb_build_object('valida', false, 'motivo', 'revocada');
  end if;
  if l.vence_el < now() then
    return jsonb_build_object('valida', false, 'motivo', 'vencida', 'vence_el', l.vence_el);
  end if;

  delete from public.sesiones
   where licencia_id = l.id and ultima_actividad < now() - interval '30 minutes';

  select count(*) into activas
    from public.sesiones
   where licencia_id = l.id and sesion <> p_sesion;
  if activas >= l.puestos then
    return jsonb_build_object('valida', false, 'motivo', 'sin_puestos');
  end if;

  insert into public.sesiones (licencia_id, sesion, ultima_actividad)
  values (l.id, p_sesion, now())
  on conflict (licencia_id, sesion) do update set ultima_actividad = now();

  return jsonb_build_object(
    'valida', true, 'nivel', l.nivel, 'vence_el', l.vence_el, 'cliente', l.cliente
  );
end;
$$;

-- Registra un pago aprobado: crea la licencia o extiende la existente.
-- Es idempotente por transacción: si Wompi repite el evento no duplica nada.
create or replace function public.registrar_pago(
  p_transaccion text,
  p_email       text,
  p_cliente     text,
  p_monto       bigint,
  p_clave_hash  text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  p     public.planes%rowtype;
  l     public.licencias%rowtype;
  nueva boolean := false;
begin
  select * into p from public.planes where precio_centavos = p_monto;
  if not found then
    return jsonb_build_object('ok', false, 'motivo', 'monto_desconocido');
  end if;

  if exists (select 1 from public.pagos where transaccion_id = p_transaccion) then
    return jsonb_build_object('ok', true, 'duplicado', true);
  end if;

  select * into l from public.licencias where lower(contacto_email) = lower(p_email) for update;
  if found then
    -- Renovación: suma los días desde el vencimiento (o desde hoy si ya venció).
    -- El estado no cambia: una licencia revocada sigue revocada.
    update public.licencias
       set vence_el = greatest(vence_el, now()) + make_interval(days => p.dias),
           plan = p.codigo, nivel = p.nivel, puestos = p.puestos,
           actualizada_el = now()
     where id = l.id
     returning * into l;
  else
    insert into public.licencias (cliente, contacto_email, plan, nivel, puestos, clave_hash, vence_el, entrega_pendiente)
    values (p_cliente, p_email, p.codigo, p.nivel, p.puestos, p_clave_hash,
            now() + make_interval(days => p.dias), true)
    returning * into l;
    nueva := true;
  end if;

  insert into public.pagos (transaccion_id, licencia_id, monto_centavos)
  values (p_transaccion, l.id, p_monto);

  return jsonb_build_object(
    'ok', true, 'duplicado', false, 'nueva', nueva, 'licencia_id', l.id,
    'vence_el', l.vence_el, 'nivel', l.nivel, 'estado', l.estado
  );
end;
$$;

-- Marca que la clave ya se entregó al cliente.
create or replace function public.marcar_entregada(p_licencia uuid)
returns void
language sql
security definer
set search_path = public
as $$
  update public.licencias set entrega_pendiente = false, actualizada_el = now() where id = p_licencia;
$$;

-- Uso manual (SQL Editor): cambia la clave de un cliente. Genera la clave con el
-- módulo licencias.py (hash_clave) y pega aquí solo el hash.
create or replace function public.regenerar_clave(p_email text, p_clave_hash text)
returns void
language sql
security definer
set search_path = public
as $$
  update public.licencias
     set clave_hash = p_clave_hash, entrega_pendiente = true, actualizada_el = now()
   where lower(contacto_email) = lower(p_email);
$$;

revoke all on function public.validar_licencia(text, text)                       from public, anon, authenticated;
revoke all on function public.registrar_pago(text, text, text, bigint, text)     from public, anon, authenticated;
revoke all on function public.marcar_entregada(uuid)                             from public, anon, authenticated;
revoke all on function public.regenerar_clave(text, text)                        from public, anon, authenticated;
grant execute on function public.validar_licencia(text, text)                    to service_role;
grant execute on function public.registrar_pago(text, text, text, bigint, text) to service_role;
grant execute on function public.marcar_entregada(uuid)                          to service_role;
grant execute on function public.regenerar_clave(text, text)                     to service_role;
