# Contexto del proyecto — App de Seguimiento de Membresía (equipo comercial de trading)

Hola Claude Code. Vas a continuar un proyecto que ya está construido y funcionando. Este documento te da TODO el contexto para que lo termines de publicar. Lee completo antes de actuar.

## Qué es este proyecto

Una app web de una sola página (`index.html`) para el equipo comercial de una empresa que vende servicios de trading. Los agentes hacen seguimiento a sus leads a lo largo de un embudo de membresía. Hay dos roles:

- **Agente**: entra con su nombre (sin contraseña), registra y edita SOLO sus propios leads.
- **Director**: entra con una clave, ve en modo lectura TODOS los leads de TODOS los agentes, con un resumen por agente.

Por cada lead se registra: nombre, si hizo **FTD** (primer depósito), a qué **clases** ingresó (números 1–6), si entró a la **presentación de membresía**, si **agendó pago** (con fecha) y **notas**.

La app ya está construida en un solo archivo `index.html` (HTML + CSS + JS puro, sin frameworks ni build). Usa **Supabase** como base de datos vía su API REST. Ya funciona: fue probada y guarda/lee datos correctamente cuando se sirve por HTTPS.

## Estado actual / qué falta

- [HECHO] App construida y funcionando (`index.html`).
- [HECHO] Base de datos Supabase creada, con tabla `leads` y políticas de acceso.
- [HECHO] Cuenta de GitHub creada y repositorio vacío creado.
- [PENDIENTE — TU TAREA] Subir `index.html` (y estos archivos) al repositorio de GitHub.
- [PENDIENTE — DESPUÉS] Conectar el repo a Cloudflare Pages para publicarlo (el usuario lo hará con tu guía).

### El repositorio de GitHub (ya creado, está vacío)
```
https://github.com/torresjuancamilo20-pixel/seguimiento-ventas.git
```

## Tu primera tarea concreta

Ayuda al usuario a **subir estos archivos al repositorio** de arriba usando Git. El usuario NO tiene experiencia técnica, así que:
1. Explícale cada comando en español, simple, antes de ejecutarlo.
2. Verifica si `git` está instalado y si tiene credenciales de GitHub configuradas; si no, guíalo (probablemente necesite un Personal Access Token o `gh auth login`).
3. Haz el flujo estándar: `git init` (si aplica), agregar el remoto, `git add`, `git commit`, `git push` a la rama `main`.
4. Confirma con él que los archivos aparecen en GitHub al terminar.

Archivos que van al repo: `index.html` (la app) y opcionalmente este `CONTEXTO.md`.

## Segunda tarea (después de que el repo tenga el código)

Guía al usuario para publicar en **Cloudflare Pages** conectando el repo de GitHub:
- dash.cloudflare.com → Workers & Pages → Create → Pages → "Connect to Git" → elegir el repo `seguimiento-ventas`.
- Build settings: NO hay build. Framework preset = "None". Build command = vacío. Output directory = `/` (raíz).
- Deploy. Resultado: un link tipo `https://seguimiento-ventas.pages.dev`.
- La ventaja de conectarlo por Git: cada vez que se actualice `index.html` en GitHub, Cloudflare re-despliega solo.

IMPORTANTE: la app hace peticiones a Supabase (dominio `*.supabase.co`). Debe servirse por HTTPS (Cloudflare lo hace automático). NO abrir el archivo como `file://` local porque el navegador bloquea las peticiones ("Failed to fetch"). Este fue justamente el problema que hizo que abandonáramos las pruebas locales.

## Detalles técnicos de la app (para que no rompas nada)

### Supabase — credenciales (ya integradas en index.html)
- URL del proyecto: `https://fhixjvxztmuifrioevze.supabase.co`
- Endpoint REST usado: `https://fhixjvxztmuifrioevze.supabase.co/rest/v1/leads`
- Se usa la clave **anon public** (JWT que empieza por `eyJ...`), incrustada en las constantes `SUPABASE_URL` y `SUPABASE_KEY` dentro del `<script>` de `index.html`.
- La clave anon es segura de exponer en el frontend (así se diseñó Supabase). NO hay ninguna clave secreta (service_role) en el archivo, y NO debe agregarse.

### Esquema de la tabla `leads` en Supabase (ya creada)
```sql
create table leads (
  id uuid primary key default gen_random_uuid(),
  agente text not null,
  nombre text default '',
  ftd boolean default false,
  clases int[] default '{}',
  membresia boolean default false,
  zoom_1a1 boolean default false,
  agendo_pago boolean default false,
  fecha_pago date,
  notas text default '',
  creado timestamptz default now(),
  actualizado timestamptz default now()
);
alter table leads enable row level security;
create policy "acceso_lectura" on leads for select using (true);
create policy "acceso_insertar" on leads for insert with check (true);
create policy "acceso_actualizar" on leads for update using (true) with check (true);
create policy "acceso_eliminar" on leads for delete using (true);
create index idx_leads_agente on leads(agente);
```

### Clave del director
- Está en el JS como constante `DIRECTOR_PASS`. Valor actual: `Director2026`.
- Sugerencia: recomiéndale al usuario cambiarla por una propia (una sola línea en el archivo).

### Cómo funciona el JS (resumen)
- Login: guarda rol y nombre en `localStorage` (`segcloud_role`, `segcloud_me`) para auto-login.
- Agente: `apiGet` filtra `?agente=eq.<nombre>`. `apiPost` crea, `apiPatch` actualiza, `apiDelete` borra. Cada cambio se guarda al instante contra Supabase.
- Director: `apiGet` trae todo (`?select=*&order=agente.asc,creado.desc`), renderiza tabla resumen por agente + tarjetas en modo solo-lectura.
- Headers de las peticiones: `apikey`, `Authorization: Bearer <anon key>`, `Content-Type: application/json`.

## Limitaciones conocidas / mejoras futuras (NO son la tarea de hoy, solo contexto)
- La seguridad es básica: la clave del director está en el frontend y las políticas RLS permiten todo. Es aceptable para una herramienta interna de gestión, pero NO para datos sensibles de clientes. Mejora futura: auth real de Supabase con roles.
- No hay realtime automático; el director actualiza con el botón "↻ Actualizar" o al entrar. Mejora futura: suscripción realtime de Supabase.
- Las "clases" son fijas 1–6. Si quieren nombres de clases personalizados, habría que ajustar el JS y quizá el esquema.

## Contexto de negocio (por si ayuda a futuras mejoras)
La empresa recibe leads de pauta a diario, los reparte entre ~12 agentes vía GoHighLevel (GHL). El embudo real es: lead → contacto → FTD (primer depósito) → clases → presentación de membresía → pago de membresía. Los datos de leads/actividad viven en GHL; los registros y FTD "oficiales" vienen de la plataforma del broker. Esta app cubre específicamente el seguimiento manual del embudo de membresía que hacen los agentes.

## Resumen de lo que el usuario espera de ti ahora
1. Subir el código a GitHub (repo de arriba), guiándolo en español paso a paso.
2. Luego, ayudarlo a conectar ese repo con Cloudflare Pages para tener el link final.
Sé paciente y explica todo de forma sencilla; no asumas conocimientos técnicos.
