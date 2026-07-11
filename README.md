# Seguimiento de Ventas — Membresía

App web de una sola página para el seguimiento del embudo de membresía del equipo comercial.

- **Agentes** registran sus leads (FTD, clases, presentación de membresía, agenda de pago).
- **Director** ve todo el equipo consolidado (modo lectura).

## Tecnología
- `index.html` — todo en un solo archivo (HTML + CSS + JS, sin build).
- Base de datos: **Supabase** (API REST).
- Publicación: **Cloudflare Pages** (conectado a este repo).

## Uso
Se sirve por HTTPS (Cloudflare Pages). No abrir como archivo local (`file://`), el navegador bloquea las peticiones a Supabase.

## Notas
- La clave del director está en el JS (`DIRECTOR_PASS`). Cambiar por una propia.
- La clave de Supabase incluida es la `anon public` (segura para frontend).

Ver `CONTEXTO.md` para el detalle completo del proyecto.
