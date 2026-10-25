# ecosistema / jumanji

**una terminal que es el juego.** no una página con una aventura adentro: un gabinete de arcade que finge ser un nodo, una máquina que te reconoce por el nombre que elegiste y un tablero que no explica por qué algunas rutas se abren.

**jugar:** https://projectsindex.github.io/jumanji/

## el gabinete

La interfaz tiene cuatro compartimentos separados; el archivo del tablero o las compras no se mezclan con el log:

- **consola** — una terminal xterm dentro de un monitor. La máquina registra lo que pasa y espera frases cortas.
- **tablero** — los mundos son casillas conectadas. Los que abriste quedan disponibles para volver o viajar; los cerrados muestran qué falta, no un botón muerto.
- **archivo** — salidas que te llevás. Cada mundo estabilizado deja un `.txt` descargable.
- **gabinete** — intercambia eco por verbos. Al principio la máquina no ofrece nada; primero hay que ganarse el eco.

En escritorio podés usar **F1–F4** para cambiar de compartimento y **Esc** para volver a la consola. En móvil, tocá las pestañas de arriba.

## primera ruta

1. Esperá a que la máquina despierte. La primera carga baja Pyodide y puede tardar unos segundos.
2. La terminal pide un usuario falso: escribí cualquier nombre, no se verifica. O escribí `anonimo` para entrar como `el que llegó`.
3. En la consola, `mirar` hace aparecer el primer verbo. `esperar` abre una ventana de pulso de 15 segundos; usá `cruzar` —o F2 y la casilla encendida— antes de que se cierre.
4. En **el claro**, mirá las tres condiciones y deducí el orden. Cada intento incorrecto vuelve las piezas a la mesa; no perdés progreso ni eco.
5. El claro deja 3 ecos. En **F4 / gabinete**, intercambiá 2 por `preguntar`; luego F2 abre la **biblioteca subterránea 7**.
6. En la biblioteca, preguntá por agua, semilla y eco. Combiná las condiciones y colocá las fichas en el orden que dedujiste.
7. F3 abre el archivo de salidas. Descargá los rastros que quieras conservar.

La secuencia no está escrita aquí: el juego confía en que leas las marcas.

## comandos de la máquina

- `mirar`, `esperar`, `cruzar`, `tocar [objeto]`, `preguntar [registro]`, `recordar`
- `mapa` / `tablero`, `archivo`, `gabinete`, `consola` — cambian de compartimento; también hay botones y teclas de función
- `verbos` — lo que ya aprendiste
- `tema` / `tema [nombre]` — clasico, amanecer, bosque, oceano o papel
- `limpiar` / **Ctrl+L**, `olvidar` (con confirmación), `salir`
- **↑ / ↓** para el historial; **Ctrl+C** para descartar la línea

El nombre, los verbos, ecos, mundos, tema y ubicación se guardan en el `localStorage` de este navegador. No hay cuenta ni servidor de progreso.

## probar localmente

No abras `index.html` con doble clic: el navegador bloquea el `fetch` de `juego.py` desde `file://`.

```bash
cd jumanji
python3 -m http.server 8000
# abrir http://localhost:8000
```

Hace falta conexión a internet para cargar xterm.js y Pyodide desde CDN.

## publicar en GitHub Pages

En este repo, Pages sirve desde `main` en `/`. Cada push a `main` republica `https://projectsindex.github.io/jumanji/`.

Para otro repo: **Settings → Pages → Deploy from a branch**, elegí la rama y `/(root)`. `.nojekyll` evita que Pages procese los archivos como Jekyll.

## arquitectura

- `index.html` — gabinete, xterm.js, FitAddon, navegación de compartimentos y puente JS/Python.
- `juego.py` — parser, persistencia, pulsos, reglas, mapas y puzzles.
- `estilos.css` — pantalla de arcade, paletas, animación y diseño responsive.
- `.nojekyll` — sirve los recursos estáticos sin transformación.

El navegador puede ofrecer una descarga cuando la pedís, pero no puede escribir archivos arbitrarios en `~/.jumanji/` ni instalar un comando en tu terminal real. El paquete `pip install ...` y el bot externo de Telegram/Discord son **otra fase**: requieren un programa/servicio aparte y permisos explícitos; esta versión no finge tenerlos.
