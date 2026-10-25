"""
ECOSISTEMA — lógica del juego.

Este archivo lo ejecuta Pyodide (Python dentro del navegador), cargado
desde index.html. El juego habla con el exterior a través de un contrato
chico:

  - funciones `eco_*` definidas en JavaScript sobre `window`
    (escribir en la terminal, limpiar, cambiar tema, pausar)
  - `window.localStorage` para que la máquina recuerde

Nada más. Mantener ese contrato chico hace que el juego se pueda
testear fuera del navegador (ver eco-test, fuera del repo).
"""

from js import window
import json

CLAVE_ESTADO = "ecosistema_estado"

TEMAS = ["clasico", "amanecer", "bosque", "oceano", "papel"]

# Todos los verbos que existen en el mundo, estén o no desbloqueados.
VERBOS_DEL_MUNDO = ["mirar", "esperar", "cruzar", "tocar", "recordar"]

# Comandos de la máquina: siempre disponibles, no se "desbloquean".
COMANDOS_MAQUINA = ["verbos", "tema", "ayuda", "limpiar", "olvidar", "salir"]


class Juego:
    def __init__(self):
        # INICIO | LOGIN_ANCLAJE | LOGIN_NOMBRE | CONSOLA |
        # CONFIRMAR_OLVIDO | FUERA
        self.estado = "INICIO"
        self.lugar = "nodo"  # nodo | claro
        self.nombre = None
        self.palabra_semilla = None
        self.verbos = ["mirar"]
        self.mundos = []
        self.tema = "clasico"
        self.banderas = {}  # memoria chica: contadores, momentos únicos

        self.buffer = ""
        self.historial = []
        self.hist_pos = None  # posición al navegar con flechas

    # ----------------------------------------------------------
    # arranque y entrada
    # ----------------------------------------------------------

    async def iniciar(self):
        self.cargar_estado()

        if self.nombre:
            window.eco_set_tema(self.tema)
            self.estado = "CONSOLA"
            self.escribir("la máquina abre un ojo.", "sistema")
            self.escribir("")
            self.escribir(f"hola de nuevo, {self.nombre}.", "exito")
            self.escribir("el ecosistema te recuerda.")
            if self.lugar == "claro":
                self.escribir(
                    "abrís los ojos en el claro, donde los dejaste.", "sistema"
                )
            self.escribir("escribí 'mirar' para ubicarte.", "sistema")
        else:
            await self.login()

        self.mostrar_prompt()

    async def login(self):
        self.escribir("╔══════════════════════════════════════╗")
        self.escribir("║       ECOSISTEMA v0.2                ║")
        self.escribir("║       nodo de acceso                 ║")
        self.escribir("╚══════════════════════════════════════╝")
        self.escribir("")
        self.escribir("para que la ruta no se pierda en el vacío,", "sistema")
        self.escribir("necesitás una palabra de anclaje.", "sistema")
        self.escribir("elegí una frase corta. algo que solo vos sepas.", "sistema")
        self.escribir("no la anotes en ningún lado. memorizala.", "sistema")
        self.escribir("lo que escribas no se va a ver en pantalla.", "sistema")
        self.escribir("")
        self.escribir("si algún día volvés y la máquina te olvida,", "sistema")
        self.escribir("esta frase te va a traer de vuelta.", "sistema")
        self.escribir("")
        self.escribir("o escribí 'anonimo' para entrar sin anclaje.", "sistema")
        self.escribir("(si te vas, te vas para siempre.)", "sistema")
        self.escribir("")
        self.escribir("¿cuál es tu palabra de anclaje?")
        self.estado = "LOGIN_ANCLAJE"

    async def paso_anclaje(self, texto):
        if texto.lower() == "anonimo":
            self.nombre = "el que llegó"
            self.palabra_semilla = None
            self.escribir("entraste sin anclaje.", "sistema")
            self.escribir("si te vas, te vas para siempre.", "sistema")
            self.escribir("")
            await self.entrar()
            return

        if len(texto) < 3:
            self.escribir("demasiado corta para anclar nada.", "error")
            self.escribir("elegí una frase, aunque sea breve.", "sistema")
            self.escribir("")
            self.escribir("¿cuál es tu palabra de anclaje?")
            return

        self.palabra_semilla = texto
        self.escribir("anclaje establecido.", "exito")
        self.escribir("la máquina te va a recordar.", "sistema")
        self.escribir("")
        self.escribir("ahora: ¿cómo querés que te nombre el ecosistema?")
        self.estado = "LOGIN_NOMBRE"

    async def paso_nombre(self, texto):
        nombre = " ".join(texto.lower().split())[:24]
        if not nombre:
            self.escribir("la máquina necesita llamarte de alguna forma.", "sistema")
            self.escribir("¿cómo querés que te nombre?")
            return
        self.nombre = nombre
        await self.entrar()

    async def entrar(self):
        self.estado = "CONSOLA"
        self.escribir(f"hola, {self.nombre}.", "exito")
        self.escribir("")
        self.escribir("estás en un nodo del ecosistema.", "sistema")
        self.escribir("no hay mucho más. por ahora.", "sistema")
        self.escribir("escribí 'mirar'.", "sistema")
        self.guardar_estado()

    async def paso_olvido(self, comando):
        if comando == "olvido":
            try:
                window.localStorage.removeItem(CLAVE_ESTADO)
            except Exception:
                pass
            self.escribir("la máquina cierra los ojos.", "sistema")
            self.escribir("ya no te recuerda. ya no se recuerda.", "sistema")
            self.escribir("")
            self.nombre = None
            self.palabra_semilla = None
            self.verbos = ["mirar"]
            self.mundos = []
            self.banderas = {}
            self.lugar = "nodo"
            self.historial = []
            await self.login()
        else:
            self.estado = "CONSOLA"
            self.escribir("mejor así. la máquina sigue despierta.", "sistema")

    # ----------------------------------------------------------
    # entrada del teclado
    # ----------------------------------------------------------

    async def procesar_input(self, data):
        # secuencias completas (flechas): llegan de una vez
        if data in ("\x1b[A", "\x1bOA"):
            self.historial_atras()
            return
        if data in ("\x1b[B", "\x1bOB"):
            self.historial_adelante()
            return
        if data.startswith("\x1b"):
            return  # cualquier otra secuencia de escape: ignorar
        # texto común (puede venir pegado, de a muchos caracteres)
        for ch in data:
            await self.procesar_tecla(ch)

    async def procesar_tecla(self, ch):
        if self.estado == "FUERA":
            return
        if ch in ("\r", "\n"):
            window.eco_write("\r\n")
            await self.ejecutar()
        elif ch in ("\x7f", "\x08"):  # backspace / delete
            if self.buffer:
                self.buffer = self.buffer[:-1]
                window.eco_write("\b \b")
        elif ch == "\x03":  # Ctrl+C
            self.buffer = ""
            window.eco_write("^C")
            self.mostrar_prompt()
        elif ch == "\x0c":  # Ctrl+L
            window.eco_limpiar()
            self.redibujar_linea()
        elif ord(ch) >= 32:
            self.buffer += ch
            window.eco_write(self.eco_de(ch))

    def eco_de(self, ch):
        # la palabra de anclaje no se muestra: es un secreto
        if self.estado == "LOGIN_ANCLAJE":
            return "•"
        return ch

    def historial_atras(self):
        if self.estado != "CONSOLA" or not self.historial:
            return
        if self.hist_pos is None:
            self.hist_pos = len(self.historial) - 1
        elif self.hist_pos > 0:
            self.hist_pos -= 1
        self.buffer = self.historial[self.hist_pos]
        self.redibujar_linea()

    def historial_adelante(self):
        if self.estado != "CONSOLA" or self.hist_pos is None:
            return
        self.hist_pos += 1
        if self.hist_pos >= len(self.historial):
            self.hist_pos = None
            self.buffer = ""
        else:
            self.buffer = self.historial[self.hist_pos]
        self.redibujar_linea()

    def redibujar_linea(self):
        window.eco_write("\r\x1b[K" + self.texto_prompt() + self.buffer)

    # ----------------------------------------------------------
    # ejecución de comandos
    # ----------------------------------------------------------

    async def ejecutar(self):
        texto = self.buffer.strip()
        comando = texto.lower()
        self.buffer = ""
        self.hist_pos = None

        if self.estado == "CONSOLA" and comando:
            if not self.historial or self.historial[-1] != comando:
                self.historial.append(comando)

        if self.estado == "LOGIN_ANCLAJE":
            await self.paso_anclaje(texto)
        elif self.estado == "LOGIN_NOMBRE":
            await self.paso_nombre(texto)
        elif self.estado == "CONFIRMAR_OLVIDO":
            await self.paso_olvido(comando)
        elif self.estado == "CONSOLA" and comando:
            await self.procesar_comando(comando)

        if self.estado in (
            "CONSOLA",
            "LOGIN_ANCLAJE",
            "LOGIN_NOMBRE",
            "CONFIRMAR_OLVIDO",
        ):
            self.mostrar_prompt()

    async def procesar_comando(self, comando):
        partes = comando.split()
        verbo = partes[0]
        resto = partes[1:]

        # --- comandos de la máquina (siempre disponibles) ---
        if verbo == "verbos":
            self.escribir("verbos que sabés hacer:", "sistema")
            for v in self.verbos:
                self.escribir(f"  • {v}")
            return

        if verbo == "tema":
            self.comando_tema(resto[0] if resto else None)
            return

        if verbo == "ayuda":
            self.escribir("no hay ayuda. solo hay que mirar.", "sistema")
            self.escribir("")
            self.escribir("(pero la máquina también entiende:", "sistema")
            self.escribir(" verbos · tema · limpiar · olvidar · salir)", "sistema")
            return

        if verbo == "limpiar":
            window.eco_limpiar()
            return

        if verbo == "olvidar":
            self.estado = "CONFIRMAR_OLVIDO"
            self.escribir("¿olvidar todo?", "error")
            self.escribir(
                "la máquina va a olvidar tu nombre, tus verbos, tus mundos.",
                "sistema",
            )
            self.escribir(
                "escribí 'olvido' para confirmar. cualquier otra cosa para quedarte.",
                "sistema",
            )
            return

        if verbo == "salir":
            self.estado = "FUERA"
            self.escribir("la máquina te va a esperar.", "sistema")
            self.escribir(f"hasta pronto, {self.nombre}.", "exito")
            self.escribir("")
            self.escribir("(recargá la página para volver a entrar.)", "sistema")
            return

        # --- verbos del mundo ---
        if verbo in VERBOS_DEL_MUNDO and verbo not in self.verbos:
            self.escribir("todavía no sabés hacer eso.", "sistema")
            self.escribir("el cuerpo aprende de a poco.", "sistema")
            return

        if verbo == "mirar":
            self.verbo_mirar()
        elif verbo == "esperar":
            await self.verbo_esperar()
        elif verbo == "cruzar":
            self.verbo_cruzar()
        elif verbo == "tocar":
            self.verbo_tocar(resto)
        elif verbo == "recordar":
            self.verbo_recordar()
        else:
            self.escribir("no conozco ese movimiento.", "error")
            self.escribir("mis raíces no llegan tan alto.", "error")

    def comando_tema(self, tema):
        if tema is None:
            self.escribir("temas disponibles:", "sistema")
            for t in TEMAS:
                marca = "  ← la luz de ahora" if t == self.tema else ""
                self.escribir(f"  • tema {t}{marca}")
        elif tema in TEMAS:
            self.tema = tema
            window.eco_set_tema(tema)
            self.escribir(f"la luz cambia. tema: {tema}", "exito")
            self.guardar_estado()
        else:
            self.escribir("no conozco ese tema.", "error")
            self.escribir("escribí 'tema' para ver los que hay.", "sistema")

    # ----------------------------------------------------------
    # verbos del mundo
    # ----------------------------------------------------------

    def desbloquear(self, verbo):
        if verbo in self.verbos:
            return False
        self.verbos.append(verbo)
        self.escribir("")
        self.escribir(f"✓ verbo desbloqueado: {verbo}", "exito")
        self.guardar_estado()
        return True

    def verbo_mirar(self):
        if self.lugar == "claro":
            self.mirar_claro()
        else:
            self.mirar_nodo()

    def mirar_nodo(self):
        self.escribir("mirás a tu alrededor.", "exito")
        self.escribir("")
        self.escribir("estás en un nodo del ecosistema.")
        self.escribir("la terminal parpadea suavemente.")
        self.escribir("en el borde de tu visión, algo pulsa.")
        self.escribir("")
        if "claro" in self.mundos:
            self.escribir("desde acá se ve el brote, brillando bajito.", "sistema")
            self.escribir("el intervalo sigue abierto. (cruzar)", "sistema")
        elif "cruzar" in self.verbos:
            self.escribir("en el borde del nodo hay un intervalo abierto.", "sistema")
            self.escribir("cuando quieras: cruzar.", "sistema")
        elif "esperar" in self.verbos:
            self.escribir("el primer mundo está cerca.", "sistema")
            self.escribir("pero no se llega corriendo. (esperar)", "sistema")
        else:
            self.escribir("el primer mundo está cerca.", "sistema")
            self.escribir("pero primero tenés que aprender a esperar.", "sistema")
            self.desbloquear("esperar")

    async def verbo_esperar(self):
        if self.lugar != "nodo":
            self.escribir("esperás. el claro también.", "sistema")
            return

        self.banderas["esperas"] = self.banderas.get("esperas", 0) + 1

        if "cruzar" in self.verbos:
            self.escribir("esperás.", "exito")
            await window.eco_pausa(700)
            self.escribir("el pulso va y viene. todo sigue en su lugar.", "sistema")
            self.guardar_estado()
            return

        self.escribir("esperás.", "exito")
        await window.eco_pausa(900)
        self.escribir("...")
        await window.eco_pausa(900)
        self.escribir("el pulso se acerca. deja de ser un borde")
        self.escribir("y se vuelve un intervalo: un hueco exacto")
        self.escribir("del tamaño de una persona que cruza.")
        self.desbloquear("cruzar")
        self.guardar_estado()

    def verbo_cruzar(self):
        if self.lugar == "nodo":
            self.lugar = "claro"
            self.escribir("cruzás.", "exito")
            self.escribir("")
            self.escribir("el aire cambia de textura a mitad de camino.")
            self.escribir("de este lado el silencio tiene humedad.")
            self.escribir("")
            self.escribir("— mundo 1: el claro —", "sistema")
            self.escribir("escribí 'mirar'.", "sistema")
        else:
            self.lugar = "nodo"
            self.escribir("cruzás de vuelta.", "exito")
            self.escribir("el nodo te recibe sin preguntas.")
            if "claro" in self.mundos and not self.banderas.get("volvio_del_claro"):
                self.banderas["volvio_del_claro"] = True
                self.escribir(
                    "aunque algo, en la forma de parpadear, cambió.", "sistema"
                )
        self.guardar_estado()

    def mirar_claro(self):
        self.escribir("mirás el claro.", "exito")
        self.escribir("")
        if "claro" in self.mundos:
            self.escribir("donde estaba la semilla hay un brote.")
            self.escribir("crece lento, en tiempo de máquina.")
            self.escribir("el hilo de agua sigue pasando.")
        else:
            self.escribir("la luz acá es de otro material.")
            self.escribir("hay un hilo de agua que pasa sin apuro.")
            self.escribir("y una semilla, grande como un puño, que late.")
            self.escribir("")
            if "tocar" not in self.verbos:
                self.escribir("tenés manos. nunca está de más acordarse.", "sistema")
                self.desbloquear("tocar")
            else:
                self.escribir(
                    "la semilla late. el agua espera. "
                    "(tocar semilla / tocar agua)",
                    "sistema",
                )
        self.escribir("")
        self.escribir("atrás, el nodo. (cruzar para volver)", "sistema")

    def verbo_tocar(self, resto):
        if self.lugar != "claro":
            self.escribir("acá no hay nada para tocar. puro nodo.", "sistema")
            return
        if not resto:
            self.escribir("¿tocar qué? hay una semilla y hay agua.", "sistema")
            return

        cosa = resto[0]
        if cosa == "agua":
            self.escribir("tocás el agua.", "exito")
            self.escribir("está fría. sabe a antes de que llegaras.")
            self.escribir("el hilo sigue. no te necesita.", "sistema")
        elif cosa in ("semilla", "brote"):
            if "claro" in self.mundos:
                self.escribir("tocás el brote. tiembla apenas.", "exito")
                self.escribir("adentro, la palabra sigue practicando tu nombre.")
            else:
                self.completar_claro()
        else:
            self.escribir(f"acá no hay '{cosa}' para tocar.", "error")

    def completar_claro(self):
        self.escribir("tocás la semilla.", "exito")
        self.escribir("")
        self.escribir("late dos veces. después se abre, apenas,")
        self.escribir("y adentro hay una palabra a medio formar.")
        self.escribir("la palabra intenta decir tu nombre.")
        self.escribir("le sale bien a la primera.")
        self.escribir("")
        self.mundos.append("claro")
        self.escribir("✓ mundo completado: el claro", "exito")
        self.desbloquear("recordar")
        self.escribir("")
        self.escribir("la semilla ya no es semilla: es brote.", "sistema")
        self.escribir("podés volver al nodo cuando quieras. (cruzar)", "sistema")
        self.guardar_estado()

    def verbo_recordar(self):
        self.escribir("la máquina recuerda:", "sistema")
        self.escribir("")
        self.escribir(f"  te nombra: {self.nombre}")
        if self.palabra_semilla:
            self.escribir("  tenés anclaje. (la frase no se dice en voz alta.)")
        else:
            self.escribir("  no tenés anclaje. si te vas, te vas para siempre.")
        donde = "el claro" if self.lugar == "claro" else "el nodo"
        self.escribir(f"  estás en: {donde}")
        self.escribir(f"  verbos: {', '.join(self.verbos)}")
        if self.mundos:
            self.escribir(f"  mundos completados: {', '.join(self.mundos)}")
        else:
            self.escribir("  mundos completados: ninguno. todavía.")
        esperas = self.banderas.get("esperas", 0)
        if esperas:
            self.escribir(f"  veces que esperaste: {esperas}")

    # ----------------------------------------------------------
    # salida y persistencia
    # ----------------------------------------------------------

    def escribir(self, texto, estilo="normal"):
        window.eco_writeln(texto, estilo)

    def texto_prompt(self):
        if self.estado == "CONSOLA":
            if self.lugar == "claro":
                return f"{self.nombre} · el claro > "
            return f"{self.nombre} > "
        return "> "

    def mostrar_prompt(self):
        window.eco_write("\r\n" + self.texto_prompt())

    def guardar_estado(self):
        estado = {
            "version": 2,
            "nombre": self.nombre,
            "palabra_semilla": self.palabra_semilla,
            "verbos": self.verbos,
            "mundos": self.mundos,
            "tema": self.tema,
            "lugar": self.lugar,
            "banderas": self.banderas,
        }
        try:
            window.localStorage.setItem(CLAVE_ESTADO, json.dumps(estado))
        except Exception:
            pass  # si la máquina no puede recordar, el juego sigue

    def cargar_estado(self):
        try:
            crudo = window.localStorage.getItem(CLAVE_ESTADO)
        except Exception:
            return
        if not crudo:
            return
        try:
            estado = json.loads(crudo)
        except Exception:
            # memoria corrupta: mejor arrancar de cero que no arrancar
            try:
                window.localStorage.removeItem(CLAVE_ESTADO)
            except Exception:
                pass
            return
        self.nombre = estado.get("nombre")
        self.palabra_semilla = estado.get("palabra_semilla")
        self.verbos = estado.get("verbos") or ["mirar"]
        self.mundos = estado.get("mundos") or []
        self.tema = estado.get("tema") or "clasico"
        self.lugar = estado.get("lugar") or "nodo"
        self.banderas = estado.get("banderas") or {}
