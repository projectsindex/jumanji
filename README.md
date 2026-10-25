# ecosistema / jumanji

**Una terminal que es el juego.** No una página con una aventura adentro: un gabinete arcade que finge ser un nodo, una máquina que te reconoce por el nombre que elegiste y un tablero que conserva los lugares que ya lograste reconocer.

**Jugar:** https://projectsindex.github.io/jumanji/

## El gabinete

La interfaz tiene cuatro compartimentos independientes. La navegación, el archivo y las compras no se mezclan con el log de la consola:

- **Consola** — terminal xterm: acá se juega, se prueban comandos y la máquina responde.
- **Tablero** — muestra solo las ubicaciones descubiertas. No dibuja rutas ni marca etapas; podés volver a los lugares que ya reconociste.
- **Archivo** — conserva salidas descargables `.txt` de los lugares estabilizados.
- **Gabinete** — intercambia eco por verbos, de acuerdo con lo que la partida ya reveló.

Junto a la consola hay una paleta de comandos que crece con el vocabulario. Tocá un verbo o una sugerencia contextual para escribirla en el terminal y luego presioná **Enter**. La paleta ayuda a recordar qué probar, pero no resuelve los acertijos.

En escritorio podés usar **F1–F4** para cambiar de compartimento y **Esc** para volver a la consola. En móvil, tocá las pestañas de arriba.

## Primera exploración

1. Esperá a que la máquina despierte. La primera carga baja Pyodide y puede tardar unos segundos.
2. La terminal pide un usuario falso: escribí cualquier nombre, no se verifica. O escribí `anonimo` para entrar como `el que llegó`.
3. En la consola, `mirar` descubre `esperar`. Esperá al pulso: abre un intervalo breve. Usá `cruzar` —o elegí el lugar iluminado en el tablero— antes de que se cierre.
4. En **el claro**, leé las tres marcas y deducí el orden de las fichas. Un intento incorrecto vuelve las piezas a la mesa; no perdés progreso ni eco.
5. El claro deja 3 ecos. En **gabinete**, intercambiá 2 por `preguntar`; aparecerá una nueva ubicación en el tablero.
6. En la **biblioteca 7**, preguntá por agua, semilla y eco. Combiná las condiciones y tocá las fichas en el orden que dedujiste.
7. Al estabilizar la biblioteca, prestá atención al nuevo texto del log y al margen del registro. Es una palabra familiar escrita al revés, no una instrucción directa. El gabinete ofrecerá `descifrar` a cambio de eco; usá el nuevo verbo con lo que logres reconocer.
8. Cuando aparezca **Marte** en el tablero, explorá el planetario. Ordená sus cuatro nombres desde el Sol hacia afuera. `preguntar sol` da una pista opcional si necesitás recordar astronomía básica.
9. El archivo guarda una salida por cada lugar estabilizado. Podés descargarla desde **archivo**.

La solución de los acertijos no está escrita aquí: el juego confía en que leas las marcas.

## Comandos

Los verbos de exploración se desbloquean durante la partida. Los botones de la paleta contextual escriben comandos en la consola; también podés teclearlos directamente.

- `mirar`, `esperar`, `cruzar`, `tocar [objeto]`, `preguntar [registro]`, `descifrar [texto]`, `ordenar [cuatro nombres]`, `recordar`
- `mapa` / `tablero`, `archivo`, `gabinete`, `consola` — cambian de compartimento sin añadir navegación al log
- `verbos` — muestra lo que ya aprendiste
- `tema` / `tema [nombre]` — clasico, amanecer, bosque, oceano o papel
- `limpiar` / **Ctrl+L**, `olvidar` (con confirmación), `salir`
- **↑ / ↓** para el historial; **Ctrl+C** para descartar la línea

El nombre, los verbos, los ecos, los lugares estabilizados, el tema y la ubicación se guardan en el `localStorage` de este navegador. No hay cuenta ni servidor de progreso.

## Probar localmente

No abras `index.html` con doble clic: el navegador bloquea el `fetch` de `juego.py` desde `file://`.

```bash
cd jumanji
python3 -m http.server 8000
# abrir http://localhost:8000
```

Hace falta conexión a internet para cargar xterm.js y Pyodide desde CDN.

## Publicar en GitHub Pages

Durante la revisión del PR #1, Pages sirve la rama `arena/d3afdbaf-jumanji` desde `/`. Después de integrar los cambios, si querés que los siguientes despliegues sigan a `main`, elegí `main` y `/(root)` en **Settings → Pages**.

Para otro repo: **Settings → Pages → Deploy from a branch**, elegí la rama y `/(root)`. `.nojekyll` evita que Pages procese los archivos como Jekyll.

## Arquitectura

- `index.html` — gabinete, xterm.js, FitAddon, navegación de compartimentos y puente JS/Python.
- `juego.py` — parser, persistencia local, pulsos, reglas, ubicaciones y acertijos.
- `estilos.css` — pantalla arcade, paletas, animación y diseño responsive.
- `.nojekyll` — sirve los recursos estáticos sin transformación.

El navegador puede ofrecer una descarga cuando la pedís, pero no puede escribir archivos arbitrarios en `~/.jumanji/` ni instalar un comando en tu terminal real. El paquete `pip install ...` y el bot externo de Telegram/Discord son **otra fase**: requieren un programa/servicio aparte y permisos explícitos; esta versión no finge tenerlos.
