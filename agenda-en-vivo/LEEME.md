# Agenda en vivo — Reuniones con el closer

App independiente (`index.html`) donde cada **oficina** (director) agenda los espacios de
reunión del día con el **closer**, y el closer los ve **en vivo** y registra el resultado.

## Qué hace

- **Cada oficina entra con su propia clave** (NXPrime, NXElite, NXApex, NXLegendary, NXBots).
  Según la clave, la app ya sabe de qué oficina es; la oficina se pone sola en cada reunión.
- **Vista tipo calendario**: se navega por días/meses. Puedes agendar en el día que elijas
  (mañana, pasado…) y ver las reuniones de días anteriores. Cada día del calendario muestra
  cuántas reuniones tiene y un punto verde si ya hay alguna marcada como hecha.
- El director agenda: **hora + cliente + para qué es (Membresía / Bot) + ficha del cliente**
  (nota/para qué agendó, si **ha comprado algo**, **cómo va**, **experiencia en la comunidad**,
  **cuánto lleva en la comunidad**). La hora se pone con el **reloj** o **escribiéndola** (`5:30 PM`, `17:30`, `9 am`).
- El **closer** ve la agenda en tiempo real, le suena/aparece una **notificación** por cada reunión nueva,
  hace **clic en una reunión para ver la ficha técnica completa** del cliente antes de presentarle,
  y al terminar registra el **resultado**: resumen + si el cliente **agendó fecha de pago** (con fecha).
- Una **hora tomada queda bloqueada** ese día: ninguna otra oficina puede agendar a esa misma hora.
- **Solo la oficina que agendó puede quitar** su propia reunión (mientras esté pendiente).

Usa el **mismo Supabase** de la app de seguimiento.

---

## Paso 1 — Base de datos (Supabase → SQL Editor → New query → Run)

### 1a. Si es la PRIMERA vez (la tabla no existe):

```sql
create table if not exists agenda_vivo (
  id          uuid primary key default gen_random_uuid(),
  dia         date not null,
  hora        text not null,
  director    text not null,             -- nombre del cliente que se muestra
  oficina     text default '',           -- NXPrime / NXElite / ...
  creado_por  text default '',           -- oficina dueña (solo ella puede borrar)
  tipo        text default '',           -- 'membresia' | 'bot'
  contexto    text default '',           -- contexto del cliente
  resumen     text default '',           -- resumen del closer al terminar
  agendo_pago boolean default false,
  fecha_pago  date,
  estado      text default 'pendiente',  -- 'pendiente' | 'hecha'
  ha_comprado      text default '',       -- ficha: ¿ha comprado algo?
  como_va          text default '',       -- ficha: ¿cómo va?
  experiencia      text default '',       -- ficha: experiencia en la comunidad
  tiempo_comunidad text default '',       -- ficha: cuánto lleva en la comunidad
  creado      timestamptz default now(),
  unique (dia, hora)                     -- bloquea repetir la misma hora el mismo día
);

alter table agenda_vivo enable row level security;
create policy "av_select" on agenda_vivo for select using (true);
create policy "av_insert" on agenda_vivo for insert with check (true);
create policy "av_update" on agenda_vivo for update using (true) with check (true);
create policy "av_delete" on agenda_vivo for delete using (true);
```

### 1b. Si YA habías creado la tabla antes (solo agrega las columnas nuevas):

```sql
alter table agenda_vivo
  add column if not exists tipo             text default '',
  add column if not exists contexto         text default '',
  add column if not exists resumen          text default '',
  add column if not exists agendo_pago      boolean default false,
  add column if not exists fecha_pago       date,
  add column if not exists estado           text default 'pendiente',
  add column if not exists ha_comprado      text default '',
  add column if not exists como_va          text default '',
  add column if not exists experiencia      text default '',
  add column if not exists tiempo_comunidad text default '';
```

> Corre **1b** si ya tenías la tabla. Es seguro: `add column if not exists` no borra nada.
> (Las 4 últimas columnas —ficha del cliente— ya fueron aplicadas en tu proyecto.)

---

## Paso 2 — Claves (dentro de `index.html`, al inicio del `<script>`)

```js
const OFICINAS={
 "Prime2026":"NXPrime",
 "Elite2026":"NXElite",
 "Apex2026":"NXApex",
 "Legendary2026":"NXLegendary",
 "Bots2026":"NXBots"
};
const CLOSER_PASS="Closer2026";
```

Cambia las claves (lo que va entre comillas antes de los dos puntos) por las que tú quieras.
El nombre de la oficina (a la derecha) es lo que se muestra en el tablero. Para **agregar o quitar
oficinas**, solo agrega/quita líneas en `OFICINAS`.

**Claves actuales:**

| Oficina | Clave |
|---|---|
| NXPrime | `Prime2026` |
| NXElite | `Elite2026` |
| NXApex | `Apex2026` |
| NXLegendary | `Legendary2026` |
| NXBots | `Bots2026` |
| **Closer** | `Closer2026` |

---

## Paso 3 — Publicar

Al hacer merge a `main`, el sitio (Cloudflare Worker "nexus") se redespliega y la página queda en:

```
https://nexus.nexustrading.workers.dev/agenda-en-vivo/
```

- Los **directores** entran con "Soy director" → la clave de su oficina.
- El **closer** entra con "Soy el closer" → clave de closer.

---

## Notas

- La clave de Supabase incluida es la `anon public`, segura para el frontend.
- El tablero se refresca solo cada 8 s (y al volver a la pestaña).
- El sonido de notificación puede requerir que el closer toque la pantalla una vez (los navegadores móviles bloquean el audio hasta la primera interacción).
- Opcional, limpiar días viejos en Supabase: `delete from agenda_vivo where dia < current_date;`
