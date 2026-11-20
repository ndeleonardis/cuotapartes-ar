-- Esquema de la base `mercado` (Postgres 17 en Docker, en la VM), tal como está
-- aplicado desde el 2026-10-19, con la columna `anotaciones` incluida. Lo crea y
-- lo llena la ingesta de n8n. Este servicio solo lo lee.
-- Los tests lo aplican tal cual sobre una base vacía. Los roles van en roles.sql.

create schema cafci;
create schema calendario;

-- El xlsx original, una sola vez por contenido distinto (clave: sha256).
create table cafci.planilla_archivo (
  sha256    text primary key,
  bytes     integer not null,
  contenido bytea not null
);

-- Una fila por descarga, aunque el archivo sea idéntico al anterior.
create table cafci.captura (
  id             bigserial primary key,
  capturada_en   timestamptz not null default now(),
  fuente         text not null,
  http_status    smallint not null,
  sha256         text references cafci.planilla_archivo(sha256),
  fecha_planilla date,
  filas_datos    integer,
  filas_con_fecha_planilla integer,
  nota           text
);

-- Una fila por versión de cada clase. Se inserta solo si cambió el hash del contenido.
-- Las 47 columnas de la planilla (A a AU) en su orden, más las fechas de referencia
-- de los subtítulos. `fecha` es la de la fila, no la de la descarga.
-- `valor_mil_cuotapartes` es el valor cada 1.000 cuotapartes. Si la planilla trae
-- un marcador de texto en vez de un número, la columna queda nula y el texto va en
-- `anotaciones`.
create table cafci.cuotaparte_version (
  id             bigserial primary key,
  captura_id     bigint not null references cafci.captura(id),
  fuente         text not null,
  capturada_en   timestamptz not null,
  fila_excel     integer not null,
  hash_contenido text not null,
  fondo text, moneda text, region text, horizonte text,
  fecha date,
  valor_mil_cuotapartes numeric,
  valor_mil_cuotapartes_anterior numeric,
  fecha_ref_valor_anterior date,
  variacion_valor_pct numeric,
  valor_reexpresado_pesos numeric,
  variacion_pct_ref1 numeric, variacion_pct_ref2 numeric, variacion_pct_ref3 numeric,
  fecha_ref_variacion_1 date, fecha_ref_variacion_2 date, fecha_ref_variacion_3 date,
  cantidad_cuotapartes numeric,
  cantidad_cuotapartes_anterior numeric,
  fecha_ref_cantidad_anterior date,
  patrimonio numeric,
  patrimonio_anterior numeric,
  fecha_ref_patrimonio_anterior date,
  market_share numeric,
  sociedad_depositaria text,
  codigo_cnv integer,
  calificacion text,
  codigo_cafci integer not null,
  codigo_soc_gerente integer, codigo_soc_depositaria integer,
  sociedad_gerente text,
  codigo_clasificacion integer, codigo_moneda integer,
  codigo_region integer, codigo_horizonte integer,
  indice_mm text,
  comision_ingreso numeric, honorarios_adm_sg numeric,
  honorarios_adm_sd numeric, gastos_ord_gestion numeric,
  comision_rescate numeric, comision_transferencia numeric,
  honorarios_exito text,
  moneda_fondo text, plazo_liq integer, decreto_596 text,
  id_fondo_cafci_padre text, id_fondo_cnv_padre text,
  tipo_escision text, repatriacion text,
  minimo_inversion numeric, regularizacion_ley_27743 text,
  tipo_dinero text, calificado text,
  anotaciones jsonb
);
create index on cafci.cuotaparte_version (codigo_cafci, id desc);
create index on cafci.cuotaparte_version (codigo_cafci, fecha);
create index on cafci.cuotaparte_version (captura_id);

create view cafci.cuotaparte_actual as
  select distinct on (codigo_cafci) * from cafci.cuotaparte_version
  order by codigo_cafci, id desc;

create table calendario.feriado (
  fecha        date primary key,
  nombre       text not null,
  tipo         text,
  fuente       text not null,
  capturada_en timestamptz not null default now()
);
