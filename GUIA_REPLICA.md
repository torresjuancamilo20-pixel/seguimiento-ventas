# Guía de réplica — App de Seguimiento de Membresía (para Claude)

Este documento describe **todo** lo que se construyó en la app original, para que **Claude** lo reproduzca en **otra oficina** (con su propio GoHighLevel, Supabase, Cloudflare y Resend).

> ⚠️ **Claves/secretos:** este documento usa marcadores `<ASI>`. Cada oficina usa **sus propias** cuentas y claves. No reutilices las de otra oficina.

---

## 0) Prompt sugerido para pegarle a Claude

> "Quiero replicar esta app de seguimiento de membresía para mi oficina. Sigue la `GUIA_REPLICA.md` paso a paso. Yo tengo (o crearé) cuentas de GitHub, Cloudflare, Supabase, Resend y un GoHighLevel con pipelines que terminan en FTD. Guíame en español, pídeme una cosa a la vez, y ayúdame a encontrar los IDs de mi GHL. No pongas secretos en el código público."

---

## 1) Qué es la app

App web de **una sola página** (`index.html`, sin build) para que un equipo comercial haga seguimiento del embudo de membresía:

**Embudo:** FTD (primer depósito) → Clases (1–6) → Presentación de membresía → **Zoom 1 a 1** → Agendó pago.

- **Agentes** entran con su **correo** (el mismo de GHL) y ven/gestionan **sus** leads.
- **Director** entra con una clave y ve **todo** el equipo (solo lectura), con resumen por agente.
- Los leads que **hicieron FTD en GoHighLevel** entran **solos** a la app (sincronización automática cada 15 min).
- Se avisa por **correo** si la sincronización falla.
- Alerta visual de leads **+48h sin mover**, filtros, fechas, paginación, rediseño tipo dashboard.

## 2) Arquitectura

```
GoHighLevel (pipelines que terminan en FTD)
      │  (cada 15 min, lee vía API)
      ▼
Supabase Edge Function "sync-ghl"  ──►  tabla "leads"
      │                                     ▲
      │ (pg_cron dispara cada 15 min)       │ (lee/escribe)
      ▼                                     │
Resend (correo de alerta si falla)     index.html (frontend)
                                            │
                                       Cloudflare (publica el sitio por HTTPS)
```

- **Frontend:** `index.html` estático. Habla con Supabase por su **API REST** usando la clave **anon** (segura para frontend).
- **Backend:** una **Edge Function** de Supabase (Deno/TypeScript) que lee GHL y hace *upsert* en la tabla `leads`. Programada con **pg_cron** + **pg_net**.
- **Secretos:** viven en una tabla `app_config` con RLS activo **sin políticas** → solo el `service_role` del backend la lee. Nunca en el repo ni en el frontend.

## 3) Cuentas necesarias (que debe tener la otra oficina)

1. **GitHub** — repo para el `index.html`.
2. **Cloudflare** — publica el sitio (Pages o Workers) conectado al repo.
3. **Supabase** — base de datos + Edge Function + cron.
4. **Resend** — envío de correos de alerta (plan gratis; en gratis solo envía al correo de la propia cuenta).
5. **GoHighLevel** — con pipelines cuyo final sea "FTD hecho/verificado/depositado" y un **Private Integration Token** con permisos de solo lectura: `opportunities.readonly`, `contacts.readonly`, `users.readonly`.

## 4) Datos que Claude debe pedirle a la otra oficina

- `<GHL_TOKEN>` — Private Integration Token de GHL (empieza por `pit-`).
- `<GHL_LOCATION_ID>` — ID de la sub-cuenta (location) de GHL.
- `<GHL_COMPANY_ID>` — ID de la empresa (para listar usuarios; se obtiene de `GET /locations/{locationId}`).
- `<GHL_FTD_STAGES>` — lista de `{pipelineId, stageId}` de las etapas de "FTD hecho" (ver paso 6).
- `<SUPABASE_URL>` y `<SUPABASE_ANON_KEY>` — de su proyecto Supabase.
- `<RESEND_API_KEY>` (empieza por `re_`) y `<ALERT_EMAIL>` (el correo de la cuenta de Resend).
- `<DIRECTOR_PASS>` — clave que ella elija para el director.
- `<SYNC_SECRET>` — cualquier texto secreto para proteger la Edge Function (ej. `mi-sync-1a2b3c`).

## 5) Base de datos (Supabase) — SQL

Ejecutar en el proyecto Supabase de la otra oficina (SQL Editor o migraciones):

```sql
-- Tabla principal de leads
create table if not exists public.leads (
  id uuid primary key default gen_random_uuid(),
  agente text not null,
  nombre text default '',
  ftd boolean default false,
  clases int[] default '{}',
  membresia boolean default false,
  zoom_1a1 boolean default false,
  agendo_pago boolean default false,
  fecha_pago date,
  fecha_ftd date,
  notas text default '',
  ghl_opportunity_id text,
  ghl_contact_id text,
  origen text default 'manual',
  creado timestamptz default now(),
  actualizado timestamptz default now()
);
alter table public.leads enable row level security;
create policy "acceso_lectura"    on public.leads for select using (true);
create policy "acceso_insertar"   on public.leads for insert with check (true);
create policy "acceso_actualizar" on public.leads for update using (true) with check (true);
create policy "acceso_eliminar"   on public.leads for delete using (true);
create index if not exists idx_leads_agente on public.leads(agente);
alter table public.leads add constraint leads_ghl_opportunity_id_key unique (ghl_opportunity_id);

-- Roster de agentes (correo -> nombre) para el login por correo
create table if not exists public.agentes (
  email text primary key,
  nombre text not null,
  actualizado timestamptz default now()
);
alter table public.agentes enable row level security;
create policy "lectura_agentes" on public.agentes for select using (true);

-- Config y secretos (RLS activo SIN políticas: solo service_role la lee)
create table if not exists public.app_config (
  key text primary key,
  value text not null,
  updated_at timestamptz default now()
);
alter table public.app_config enable row level security;

-- Log de cada corrida del sync
create table if not exists public.sync_log (
  id bigint generated always as identity primary key,
  at timestamptz default now(),
  ok boolean not null,
  leads integer,
  message text
);
alter table public.sync_log enable row level security;
create index if not exists idx_sync_log_at on public.sync_log(at desc);
```

### Config (reemplazar los marcadores con los valores reales de la otra oficina)

```sql
insert into public.app_config (key, value) values
('ghl_token',        '<GHL_TOKEN>'),
('ghl_location_id',  '<GHL_LOCATION_ID>'),
('ghl_company_id',   '<GHL_COMPANY_ID>'),
('ghl_ftd_stages',   '<GHL_FTD_STAGES_JSON>'),  -- ej: [{"pipelineId":"...","stageId":"..."}]
('sync_secret',      '<SYNC_SECRET>'),
('resend_api_key',   '<RESEND_API_KEY>'),
('alert_email',      '<ALERT_EMAIL>'),
('sync_state',       'ok'),
('fail_count',       '0'),
('last_alert_at',    '')
on conflict (key) do update set value=excluded.value, updated_at=now();
```

## 6) Encontrar los IDs de GoHighLevel

Con el token, Claude puede llamar la API de GHL (o usar el conector de GHL):

- **Pipelines y etapas:** `GET https://services.leadconnectorhq.com/opportunities/pipelines`
  Headers: `Authorization: Bearer <GHL_TOKEN>`, `Version: 2021-07-28`.
  → De ahí saca los `{pipelineId, stageId}` de cada etapa que signifique **FTD hecho** (nombres tipo "FTD Efectuado", "FTD Verificado", "Depositado", "FTD Realizado"). Esa lista va en `ghl_ftd_stages`.
- **companyId:** `GET https://services.leadconnectorhq.com/locations/{locationId}` → campo `companyId`.
- **Usuarios/agentes:** el sync los trae solo con `GET /users/?locationId=...`.

## 7) Edge Function `sync-ghl` (Supabase)

Función en Deno/TypeScript. **No tiene secretos hardcodeados**: lee todo de `app_config`. Desplegar con `verify_jwt = false` (usa su propio secreto). Cada corrida:
1. Lee config.
2. Trae usuarios de GHL → arma mapa `userId→nombre` y actualiza `agentes` (correo→nombre).
3. Recorre las etapas FTD y pagina las oportunidades.
4. Hace *upsert* en `leads` por `ghl_opportunity_id` (solo toca `nombre/agente/ftd/fecha_ftd`; **nunca** pisa clases/membresía/zoom/pago).
5. Registra la corrida en `sync_log`. Si falla 2 veces seguidas → correo de alerta (Resend). Si se recupera → correo de recuperación. Anti-spam 3 h.

```typescript
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const GHL = "https://services.leadconnectorhq.com";
const COOLDOWN_MS = 3 * 60 * 60 * 1000; // 3 h entre correos
const ALERT_AFTER = 2;                  // alertar tras 2 fallas seguidas

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
async function fetchRetry(u: string, opts: any, tries = 3): Promise<Response> {
  let lastErr = "";
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(u, opts);
      if (r.ok) return r;
      lastErr = r.status + " " + (await r.text()).slice(0, 200);
    } catch (e) { lastErr = String((e as Error).message || e); }
    if (i < tries - 1) await sleep(1500 * (i + 1));
  }
  throw new Error(lastErr);
}

Deno.serve(async (req: Request) => {
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: cfgRows } = await sb.from("app_config").select("key,value");
  const cfg: Record<string, string> = {};
  (cfgRows || []).forEach((r: any) => (cfg[r.key] = r.value));
  const setCfg = (k: string, v: string) => sb.from("app_config").upsert({ key: k, value: v }, { onConflict: "key" });

  async function sendEmail(subject: string, html: string) {
    if (!cfg.resend_api_key || !cfg.alert_email) return;
    try {
      await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: { Authorization: `Bearer ${cfg.resend_api_key}`, "Content-Type": "application/json" },
        body: JSON.stringify({ from: "Alertas Seguimiento <onboarding@resend.dev>", to: [cfg.alert_email], subject, html }),
      });
    } catch (_) { /* ignore */ }
  }

  const url = new URL(req.url);
  const secret = req.headers.get("x-sync-secret") || url.searchParams.get("secret");
  if (!cfg.sync_secret || secret !== cfg.sync_secret) return json({ error: "no autorizado" }, 401);

  if (url.searchParams.get("test") === "email") {
    await sendEmail("✅ Prueba de alertas", `<p>Las alertas funcionan.</p>`);
    return json({ ok: true, test: "email enviado" });
  }

  try {
    const token = cfg.ghl_token, loc = cfg.ghl_location_id;
    const stages = JSON.parse(cfg.ghl_ftd_stages || "[]");
    const H = { Authorization: `Bearer ${token}`, Version: "2021-07-28", Accept: "application/json" };

    const uRes = await fetchRetry(`${GHL}/users/?locationId=${loc}`, { headers: H });
    const users = (await uRes.json()).users || [];
    const id2name: Record<string, string> = {};
    const roster: any[] = [];
    users.forEach((u: any) => {
      const nombre = (u.name || "").replace(/\s+/g, " ").trim();
      id2name[u.id] = nombre;
      if (u.email && nombre) roster.push({ email: String(u.email).toLowerCase().trim(), nombre });
    });
    if (roster.length) {
      const { error: rErr } = await sb.from("agentes").upsert(roster, { onConflict: "email" });
      if (rErr) throw new Error("agentes: " + rErr.message);
    }

    const rows: any[] = [];
    for (const st of stages) {
      for (let page = 1; page < 200; page++) {
        const u = `${GHL}/opportunities/search?location_id=${loc}&pipeline_id=${st.pipelineId}&pipeline_stage_id=${st.stageId}&limit=100&page=${page}`;
        const r = await fetchRetry(u, { headers: H });
        const j = await r.json();
        const opps = j.opportunities || [];
        for (const o of opps) {
          const nm = (((o.contact && o.contact.name) || o.name || "").replace(/\s+/g, " ").trim()) || "Sin nombre";
          const fechaRaw = o.lastStageChangeAt || o.updatedAt || o.createdAt || null;
          rows.push({ agente: id2name[o.assignedTo] || "sin asignar", nombre: nm, ftd: true,
            fecha_ftd: fechaRaw ? String(fechaRaw).slice(0, 10) : null,
            ghl_opportunity_id: o.id, ghl_contact_id: o.contactId, origen: "ghl" });
        }
        if (opps.length < 100) break;
      }
    }

    let saved = 0;
    for (let i = 0; i < rows.length; i += 200) {
      const chunk = rows.slice(i, i + 200);
      const { error } = await sb.from("leads").upsert(chunk, { onConflict: "ghl_opportunity_id" });
      if (error) throw new Error("upsert: " + error.message);
      saved += chunk.length;
    }

    await sb.from("sync_log").insert({ ok: true, leads: saved, message: null });
    if (cfg.sync_state === "fail") await sendEmail("✅ Sincronización RECUPERADA", `<p>Volvió a la normalidad (${saved} leads).</p>`);
    await setCfg("sync_state", "ok"); await setCfg("fail_count", "0");
    return json({ ok: true, agentes: roster.length, leads_procesados: rows.length, guardados: saved });
  } catch (e) {
    const msg = String((e && (e as Error).message) || e).slice(0, 500);
    await sb.from("sync_log").insert({ ok: false, leads: null, message: msg });
    const failCount = (parseInt(cfg.fail_count || "0") || 0) + 1;
    const lastAlert = cfg.last_alert_at ? Date.parse(cfg.last_alert_at) : 0;
    const cooldownOver = !lastAlert || (Date.now() - lastAlert) > COOLDOWN_MS;
    if (failCount >= ALERT_AFTER && (cfg.sync_state !== "fail" || cooldownOver)) {
      await sendEmail("⚠️ FALLA en la sincronización con GoHighLevel",
        `<p>Falló ${failCount} veces seguidas.</p><pre>${msg.replace(/</g, "&lt;")}</pre><p>Revisa el token de GHL.</p>`);
      await setCfg("last_alert_at", new Date().toISOString());
      await setCfg("sync_state", "fail");
    }
    await setCfg("fail_count", String(failCount));
    return json({ ok: false, error: msg, fail_count: failCount }, 500);
  }
});

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
```

> Nota: Supabase inyecta `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` a las Edge Functions automáticamente; no hay que configurarlas.

## 8) Programar la sincronización (pg_cron + pg_net)

```sql
create extension if not exists pg_net  with schema extensions;
create extension if not exists pg_cron;
create extension if not exists http    with schema extensions; -- opcional, para pruebas manuales

select cron.schedule(
  'sync-ghl-cada-15min',
  '*/15 * * * *',
  $$ select net.http_get(
       url := '<SUPABASE_URL>/functions/v1/sync-ghl?secret=<SYNC_SECRET>',
       timeout_milliseconds := 150000
     ); $$
);
```

Primera corrida manual (backfill) y prueba de correo (con la extensión `http`):
```sql
select extensions.http_set_curlopt('CURLOPT_TIMEOUT_MS','120000');
-- backfill:
select status, content::text from extensions.http_get('<SUPABASE_URL>/functions/v1/sync-ghl?secret=<SYNC_SECRET>');
-- prueba de correo:
select status, content::text from extensions.http_get('<SUPABASE_URL>/functions/v1/sync-ghl?secret=<SYNC_SECRET>&test=email');
```

## 9) Frontend (`index.html`)

Copiar el `index.html` del repo original y cambiar **3 constantes** al inicio del `<script>`:

```js
const SUPABASE_URL="<SUPABASE_URL>";
const SUPABASE_KEY="<SUPABASE_ANON_KEY>";   // clave anon (pública, segura en frontend)
const DIRECTOR_PASS="<DIRECTOR_PASS>";      // clave del director
```

El resto funciona igual: login por correo (lee `agentes`), KPIs, filtros, fecha, alerta +48h, paginación, vista de director a dos columnas.

## 10) Publicar (Cloudflare)

- Cloudflare → Workers & Pages → **Create** → **Pages** → **Connect to Git** → elegir el repo.
- Build: **Framework preset = None**, **Build command = vacío**, **Output directory = `/`**, **Production branch = main**.
- Deploy. Da un link `https://<algo>.pages.dev`. Cada push a `main` re-despliega solo.

## 11) Checklist de puesta en marcha

1. [ ] Crear proyecto Supabase → correr SQL del paso 5 (tablas).
2. [ ] Crear token GHL (Private Integration, solo lectura) → obtener IDs (paso 6).
3. [ ] Insertar config del paso 5 con los valores reales.
4. [ ] Desplegar Edge Function `sync-ghl` (verify_jwt=false).
5. [ ] Backfill + prueba de correo (paso 8).
6. [ ] Programar el cron (paso 8).
7. [ ] Subir `index.html` a GitHub con las 3 constantes ajustadas.
8. [ ] Conectar el repo a Cloudflare y publicar (paso 10).
9. [ ] Repartir a los agentes el link + su correo de acceso.

---

**Resumen para tu colega:** todo está pensado para que cada oficina sea independiente (su GHL, su Supabase, su Resend, su Cloudflare). Ninguna clave se comparte entre oficinas. Con este documento + el `index.html` del repo, Claude puede montarlo de principio a fin.
