# ecosistema

una terminal que es un juego.

no hay mapa, no hay puntos, no hay ayuda. hay verbos: el mundo se abre
en la medida en que aprendés a hacer cosas. y hay una máquina que
recuerda — si le das una palabra de anclaje.

**jugar:** https://projectsindex.github.io/jumanji/

## cómo se juega

1. esperá a que la máquina despierte (la primera carga tarda unos segundos)
2. elegí tu palabra de anclaje (no se ve mientras la escribís) o entrá como `anonimo`
3. escribí `mirar` para empezar
4. de ahí en más, el ecosistema dirá

la ruta de verbos, sin spoilers de más:
`mirar` → `esperar` → `cruzar` → *(mundo 1: el claro)* → `tocar` → `recordar`

### comandos de la máquina (siempre disponibles)

- `verbos` — ver los verbos que ya sabés hacer
- `tema` / `tema [nombre]` — cambiar la luz (clasico, amanecer, bosque, oceano, papel)
- `limpiar` — limpiar la terminal (también Ctrl+L)
- `olvidar` — la máquina te olvida. para siempre. pide confirmación
- `ayuda` — no hay ayuda
- `salir` — cerrar la sesión

flechas ↑ ↓ navegan el historial de comandos. tu progreso se guarda
solo, en tu navegador (localStorage). si limpiás los datos del sitio,
la máquina te olvida de verdad.

## probar localmente

> ⚠️ no abras `index.html` directamente con doble clic: el navegador
> bloquea la lectura de `juego.py` desde `file://`. usá un servidor:

```bash
cd jumanji
python3 -m http.server 8000
# abrir http://localhost:8000
```

necesitás internet igual: Pyodide y xterm.js se cargan desde CDN.

## publicar en GitHub Pages

ya está activado para este repo (Settings → Pages → rama `main`, `/root`).
cada push a `main` republica el juego en ~1 minuto.

para un repo nuevo: subí los archivos, andá a **Settings → Pages**,
en *Source* elegí la rama y `/ (root)`, guardá. el juego queda en
`tuusuario.github.io/nombre-del-repo`.

## estructura

- `index.html` — carga xterm.js + Pyodide y define el puente `eco_*`
  (lo único que el juego conoce del navegador)
- `juego.py` — toda la lógica del juego, en Python
- `estilos.css` — página, loader, pulso y variables de tema
- `.nojekyll` — le dice a GitHub Pages que sirva los archivos tal cual

### el puente entre Python y la terminal

`juego.py` no toca el DOM ni xterm: llama funciones chicas que viven
en `window` — `eco_write` (sin salto de línea), `eco_writeln` (con
estilo), `eco_limpiar`, `eco_pausa` (una Promise que Python espera con
`await`), `eco_set_tema` — y guarda en `window.localStorage`. gracias
a eso, el juego entero se puede testear fuera del navegador corriendo
Pyodide en Node con un `window` falso.

## próximo paso

el mundo 2. y que la palabra de anclaje sirva, algún día, para
volver de verdad.
