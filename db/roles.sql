-- Permisos de los roles de la base `mercado`, tal como están aplicados en la VM.
-- Los roles se crean aparte con su contraseña, que nunca entra al repo (en la VM
-- viven en /home/ubuntu/stack/.env.roles). Los tests los crean con una de prueba.

grant usage on schema cafci, calendario to ingesta, api_lectura;

-- ingesta (n8n): solo select e insert, sin update ni delete.
grant select, insert on cafci.planilla_archivo, cafci.captura,
      cafci.cuotaparte_version, calendario.feriado to ingesta;
grant select on cafci.cuotaparte_actual to ingesta;
grant usage on all sequences in schema cafci to ingesta;

-- api_lectura (este servicio): solo select, y sin acceso a planilla_archivo.
grant select on cafci.cuotaparte_version, cafci.cuotaparte_actual,
      cafci.captura, calendario.feriado to api_lectura;
