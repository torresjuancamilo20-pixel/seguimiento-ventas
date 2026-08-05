# Agenda en vivo — Reuniones con el closer

App independiente (una sola página, `index.html`) donde los **directores** ponen los
espacios de reunión del día con el **closer**, y el closer los ve **en vivo**.

- Los directores agendan: **hora + nombre + oficina** (ej. `5:30 — Daniel (oficina legendary)`).
- El closer ve el tablero en tiempo real; le suena y aparece una **notificación** por cada espacio nuevo.
- Una **hora tomada queda bloqueada**: ningún otro director puede poner algo a esa misma hora.
- **Se reinicia solo cada día** (a la medianoche, hora Colombia). Cada día arranca limpio.

Usa el **mismo Supabase** de la app de seguimiento. Solo hay que crear **una tabla nueva** (paso 1).

---

## Paso 1 — Crear la tabla en Supabase (se hace UNA sola vez)

1. Entra a tu proyecto en https://supabase.com → menú izquierdo **SQL Editor** → **New query**.
2. Copia y pega TODO este bloque y dale **Run**:

```sql
create table if not exists agenda_vivo (
  id       uuid primary key default gen_random_uuid(),
  dia      date not null,
  hora     text not null,
  director text not null,
  oficina  text default '',
  creado   timestamptz default now(),
  unique (dia, hora)        -- <- bloquea repetir la misma hora el mismo día
);

alter table agenda_vivo enable row level security;

create policy "av_select" on agenda_vivo for select using (true);
create policy "av_insert" on agenda_vivo for insert with check (true);
create policy "av_update" on agenda_vivo for update using (true) with check (true);
create policy "av_delete" on agenda_vivo for delete using (true);
```

Listo. La restricción `unique (dia, hora)` es la que hace que, si un horario ya está
tomado, ningún otro director pueda repetirlo (el sistema lo rechaza y muestra el aviso).

> El "reinicio cada 24 h" es automático porque la app solo muestra los espacios del día
> de hoy. Los de días anteriores dejan de mostrarse solos. (Opcional: si quieres borrar
> los viejos de la base, puedes correr de vez en cuando
> `delete from agenda_vivo where dia < current_date;`)

---

## Paso 2 — Claves de acceso

Dentro de `index.html`, cerca del inicio del `<script>`, hay dos líneas:

```js
const DIRECTOR_PASS="Director2026";
const CLOSER_PASS="Closer2026";
```

Cámbialas por las que tú quieras y guarda. Los directores entran con la clave de director
(y su nombre); el closer entra con la clave de closer.

---

## Paso 3 — Publicar

Al estar en el mismo repositorio, Cloudflare Pages la despliega sola. La página quedará en:

```
https://<tu-sitio>.pages.dev/agenda-en-vivo/
```

Compártele ese link a los directores y al closer. Que la guarden en favoritos.

---

## Notas

- La clave de Supabase incluida es la `anon public`, segura para el frontend (igual que la app de seguimiento).
- El tablero se refresca solo cada 8 segundos. También se refresca al volver a la pestaña.
- El sonidito de notificación puede requerir que el closer toque la pantalla una vez (los navegadores móviles bloquean el audio hasta la primera interacción).
