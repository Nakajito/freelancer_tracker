# Plan: Fixes de estilo + rediseño editorial (DESIGN.md)

## Context

PropoTrack (Django 6 + Tailwind v4) tiene 3 problemas de UI/diseño:

1. **Signup icons solapados.** En `accounts/signup/` los iconos dentro de los inputs se montan sobre el texto. Root cause confirmado: [static/css/forms.css:18](static/css/forms.css#L18) aplica una regla global `input[type=email], input[type=password] { padding: .75rem 1rem }`. El selector por atributo (especificidad 0,0,1,1) gana a la clase utilitaria Tailwind `.pl-11` (0,0,1,0), anulando el padding-left que deja espacio al icono → el texto arranca debajo del icono. Login no usa iconos internos, por eso no se ve afectado.
2. **Home sin controles tema/idioma + idioma no cambia.** [templates/dashboard/landing.html:24-34](templates/dashboard/landing.html#L24-L34) solo tiene botones Login/Get Started; no incluye switcher ni form `set_language`. El i18n está bien configurado (`LocaleMiddleware`, URL `set_language`, catálogo `es` compilado, strings ya envueltos en `{% trans %}`), pero sin form el idioma no se puede cambiar desde el home.
3. **Paleta y tipografía no siguen DESIGN.md.** Hoy: teal `#00685f` + Geist/Inter. Debe ser paleta editorial (snow/sand/taupe/negro) + Libre Baskerville (títulos) y Roboto (cuerpo/UI).

**Decisiones del usuario (locked):**
- Tema: **solo claro editorial** → se elimina dark/system y el toggle de tema en toda la app. (El item 2 "opciones de tema" se cumple removiendo el switcher de tema; el home recibe el switcher de **idioma**.)
- Fuentes: **self-host woff2** (mismo patrón que Geist/Inter hoy).
- Semánticos: **rojo de error funcional** (excepción WCAG) + badges de estado en escala neutra negro/taupe/sand.

Resultado esperado: signup legible, home con cambio de idioma funcional, identidad visual alineada a DESIGN.md, sin dark mode.

---

## Paleta → tokens (mapeo en `src/css/app.css` `@theme`)

| Token | Nuevo valor | Notas |
|---|---|---|
| `--color-background`, `--color-surface`, `--color-surface-bright` | `#F2F2F2` | Nieve base (60%) |
| `--color-surface-container-lowest` | `#FFFFFF` | Cards limpias |
| `--color-surface-container-low` | `#F2F2F2` | |
| `--color-surface-container`, `-high`, `-highest`, `-dim` | `#EAE4D5` (graduar ligeramente más oscuro en -high/-highest) | Arena caliza (superficie secundaria) |
| `--color-on-background`, `--color-on-surface` | `#000000` | Texto cuerpo/títulos |
| `--color-on-surface-variant` | `#000000` (texto largo) / soporte corto en taupe | WCAG: texto largo solo negro |
| `--color-outline`, `--color-outline-variant` | `#B6B09F` | Bordes/divisores (acento 10%) |
| `--color-primary`, `--color-surface-tint` | `#000000` | CTAs sólidos negros |
| `--color-on-primary` | `#F2F2F2` | Texto sobre negro |
| `--color-primary-container` | `#B6B09F` | Estado hover de CTA (DESIGN 4.1) |
| `--color-on-primary-container` | `#000000` | |
| `--color-secondary` / `-container` | negro / `#EAE4D5` | Colapsar a neutros (sin azul) |
| `--color-tertiary` / `-container` | negro / `#EAE4D5` | Colapsar a neutros (sin rust) |
| `--color-inverse-surface` / `-on-surface` / `-primary` | `#000000` / `#F2F2F2` / `#EAE4D5` | Tira "Creative Pitch" del landing |
| `--color-error` y familia | mantener rojo discreto (`#ba1a1a` / `#ffdad6`) | Excepción funcional |

- Eliminar TODO el bloque dark: `:root[data-theme="dark"]`, `:root[data-theme-resolved="dark"]` y el `@media (prefers-color-scheme: dark)` ([app.css:118-184](src/css/app.css#L118)). Conservar la regla de `border-color` por defecto.
- `--radius`/`--radius-lg`: mantener (DESIGN no especifica; estética plana ya se respeta sin sombras pesadas).

## Tipografía (tokens `--font-*` en `app.css` + `fonts.css`)

- `--font-display`, `--font-h1`, `--font-h2`, `--font-h3` → `"Libre Baskerville", serif`. Ajustar `--text-*--line-height` de títulos a ~1.2-1.3 (DESIGN 3.1) y `--text-h3--font-weight: 400` con itálica donde aplique (subsecciones).
- `--font-body-lg/md/sm`, `--font-label-md/sm` → `"Roboto", sans-serif`.
- `src/css/fonts.css`: reemplazar `@font-face` de Geist e Inter por Libre Baskerville (400/700, normal+italic) y Roboto (300/400/500/700). Mantener Material Symbols intacto.

## Fuentes self-host

- Descargar woff2 latin (google-webfonts-helper) a `static/fonts/libre-baskerville/` y `static/fonts/roboto/`.
- Borrar `static/fonts/geist/` y `static/fonts/inter/`.
- `templates/base.html:15-16`: actualizar `<link rel="preload">` a los woff2 nuevos (preload Libre Baskerville 400 + Roboto 400).

---

## Cambios por archivo

### Problema 1 — signup icons ([static/css/forms.css](static/css/forms.css), [templates/account/signup.html](templates/account/signup.html))
- Root-cause fix: los selectores por elemento en forms.css no deben pisar inputs ya estilizados a mano en auth.
  - Añadir clase marcadora `auth-field` a los 3 `<input>` de signup ([signup.html:28,38,48](templates/account/signup.html#L28)) y a los inputs de `templates/account/login.html` por consistencia.
  - En forms.css cambiar los selectores globales a excluir el marcador: `input[type=email]:not(.auth-field)`, `input[type=password]:not(.auth-field)`, etc. (aplicar a la lista de selectores de [forms.css:5-13](static/css/forms.css#L5)).
- forms.css hardcodes a actualizar dentro del mismo cambio:
  - `font-family: 'Inter'` → `'Roboto'` ([forms.css:19](static/css/forms.css#L19)).
  - focus `box-shadow: rgba(0,104,95,.2)` → `rgba(0,0,0,.2)` ([forms.css:32](static/css/forms.css#L32)).
  - select icon `fill='%233d4947'` → `fill='%23000000'` ([forms.css:49](static/css/forms.css#L49)).

### Problema 2 — home idioma ([templates/dashboard/landing.html](templates/dashboard/landing.html))
- En el bloque de la derecha del navbar ([landing.html:24-34](templates/dashboard/landing.html#L24)) añadir:
  - Botón `data-lang-btn` (icono `translate` + label EN/ES) con `data-value="{{ active_language|default:'en' }}"`, visible también en móvil (usar `flex`, no `hidden sm:flex`).
  - Form oculto `set_language` (igual patrón que el resto de la app):
    ```html
    <form id="lang-form" method="post" action="{% url 'set_language' %}" class="hidden">
      {% csrf_token %}
      <input type="hidden" name="next" value="{{ request.path }}">
      <input type="hidden" id="lang-input-public" name="language" value="{{ active_language|default:'en' }}">
    </form>
    ```
  - Para usuario autenticado en el landing: incluir también `prefs-form` (post a `account-preferences`, solo `language_preference`) para que el botón persista en DB, reutilizando la lógica existente de [preferences.js:68-97](static/js/preferences.js#L68).
- NO se añade botón de tema (light-only).
- Verificar/traducir strings del landing en `locale/es/LC_MESSAGES/django.po`: `makemessages -l es`, traducir los msgids nuevos del landing, `compilemessages`.

### Problema 3/decisión — eliminar dark mode (toggle de tema app-wide)
- `templates/base.html`: quitar atributo `data-theme=...` ([base.html:3](templates/base.html#L3)) y el script anti-flash ([base.html:14](templates/base.html#L14)).
- `templates/app_base.html:114-127`: eliminar el botón `data-theme-btn` (conservar solo `data-lang-btn`); en `prefs-form` ([app_base.html:109-113](templates/app_base.html#L109)) quitar `theme-input`. Bajar breakpoint del contenedor de `hidden lg:flex` a `flex`/`md:flex` para que el switcher de idioma se vea mejor.
- `static/js/preferences.js`: eliminar `THEME_CYCLE`, `THEME_META`, `applyTheme`, `updateThemeBtn`, `bindThemeButtons` y el listener `matchMedia`. Conservar `LANG_LABELS`, `updateLangBtn`, `bindLangButtons`, `bindAutoSubmit`, `init`.
- Perfil/preferencias: en `templates/accounts/` (profile) quitar el control de tema; en `apps/accounts/views.py` (preferences view) dejar de procesar `theme_preference`.
- `apps/accounts/context_processors.py`: eliminar `active_theme` del dict ([context_processors.py:13-16](apps/accounts/context_processors.py#L13)).
- Modelo `User.theme_preference`: **mantener la columna sin migración** (campo dormido) para acotar el blast radius; se deja de usar en UI/vistas. Marcar como deprecado en el plan; eliminación opcional como follow-up.

### Docs
- `README.md`: sección "Design System" → nueva paleta (snow/sand/taupe/negro), fuentes Libre Baskerville + Roboto, radius. Tabla de preferencias: quitar fila de tema; dejar solo idioma. Quitar menciones a light/dark/system y `ft_theme`.
- `CLAUDE.md` / `AGENTS.md`: actualizar solo si hace falta (mencionar light-only y el set de fuentes/paleta). El stack y arquitectura no cambian.
- `tasks/lessons.md`: registrar la lección de especificidad (selectores por atributo en forms.css pisando utilidades Tailwind).

## Archivos críticos
- `src/css/app.css` (tokens), `src/css/fonts.css` (@font-face)
- `static/css/forms.css` (specificity fix + hardcodes)
- `templates/base.html`, `templates/app_base.html`, `templates/dashboard/landing.html`, `templates/account/signup.html`, `templates/account/login.html`, `templates/accounts/*profile*`
- `static/js/preferences.js`
- `apps/accounts/context_processors.py`, `apps/accounts/views.py`
- `locale/es/LC_MESSAGES/django.po`
- `static/fonts/` (añadir libre-baskerville/roboto, borrar geist/inter)
- `README.md`, `CLAUDE.md`, `AGENTS.md`, `tasks/lessons.md`

## Build / orden
1. Tokens + fuentes (app.css, fonts.css, descargar woff2, base.html preload).
2. forms.css (specificity + hardcodes), signup/login marker class.
3. landing: switcher idioma + form; quitar dark de base/app_base/JS/profile/views/context_processor.
4. i18n: makemessages → traducir → compilemessages.
5. `bin/build-css.sh` (recompila Tailwind a static/css/app.css).

## Verificación (antes de "done")
- `bin/build-css.sh` sin errores; `static/css/app.css` regenerado.
- `uv run python manage.py compilemessages` ok.
- `uv run pytest --cov --cov-fail-under=75` verde (actualizar `tests/test_accounts.py` si toca por quitar tema).
- `uv run ruff check . && uv run ruff format --check .` y `uv run mypy apps config` limpios.
- `uv run python manage.py runserver` + walkthrough manual:
  - `/accounts/signup/`: iconos a la izquierda, texto con padding correcto, sin solape (probar email/password). Comparar con login.
  - Home `/`: botón idioma visible (incl. móvil), click EN↔ES recarga y traduce el landing; sin botón de tema.
  - Dashboard autenticado: navbar con switcher de idioma; persiste en DB; sin toggle de tema.
  - Revisar páginas clave (dashboard, proposals list, profile) con la paleta nueva: fondos snow, cards sand, bordes taupe, CTAs negros con hover taupe, títulos en Libre Baskerville, cuerpo en Roboto, errores en rojo.
- Confirmar que no quedan referencias a Geist/Inter/`data-theme`/`ft_theme` (`grep -rn`).
