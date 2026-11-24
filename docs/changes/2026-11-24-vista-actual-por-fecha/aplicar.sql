-- T3 del cambio vista-actual-por-fecha. Se corre una sola vez en la VM, de día.
-- Si una verificación falla, psql corta y la transacción vuelve atrás sola.
--
-- Desde la VM:
--   cd ~/stack && docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d mercado' \
--     < ~/cuotapartes-ar/docs/changes/2026-11-24-vista-actual-por-fecha/aplicar.sql
\set ON_ERROR_STOP on
begin;

create temp table antes on commit drop as
  select count(*) as filas from cafci.cuotaparte_actual;

create or replace view cafci.cuotaparte_actual as
  select distinct on (codigo_cafci) * from cafci.cuotaparte_version
  order by codigo_cafci, fecha desc nulls last, id desc;

do $$
declare
  filas_antes bigint;
  filas_despues bigint;
  desactualizadas bigint;
begin
  select filas into filas_antes from antes;
  select count(*) into filas_despues from cafci.cuotaparte_actual;
  if filas_antes <> filas_despues then
    raise exception 'Cambió la cantidad de clases: % antes y % después', filas_antes, filas_despues;
  end if;

  -- C16 y C18: ninguna clase puede tener una versión con fecha más nueva que la que muestra la vista.
  select count(*) into desactualizadas
  from cafci.cuotaparte_actual a
  where exists (
    select 1 from cafci.cuotaparte_version v
    where v.codigo_cafci = a.codigo_cafci
      and v.fecha is not null
      and (a.fecha is null or v.fecha > a.fecha)
  );
  if desactualizadas > 0 then
    raise exception '% clases siguen mostrando una fecha vieja', desactualizadas;
  end if;

  -- C19: los dos roles siguen pudiendo leer la vista.
  if not has_table_privilege('ingesta', 'cafci.cuotaparte_actual', 'select') then
    raise exception 'ingesta perdió el permiso de leer la vista';
  end if;
  if not has_table_privilege('api_lectura', 'cafci.cuotaparte_actual', 'select') then
    raise exception 'api_lectura perdió el permiso de leer la vista';
  end if;

  raise notice 'OK: % clases, ninguna con fecha vieja, permisos intactos', filas_despues;
end $$;

commit;

-- Para comparar con db/esquema.sql del repo.
select pg_get_viewdef('cafci.cuotaparte_actual');
