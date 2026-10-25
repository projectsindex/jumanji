"""
ECOSISTEMA — motor del arcade terminal.

Lo ejecuta Pyodide desde index.html. La máquina solo conoce un puente
pequeño en `window.eco_*`; las vistas (consola, tablero, archivo y gabinete)
son compartimentos distintos y no se mezclan con el log.
"""

from js import window
import json
import time

CLAVE_ESTADO = "ecosistema_estado"
TEMAS = ["clasico", "amanecer", "bosque", "oceano", "papel"]

# Los verbos se incorporan poco a poco: algunos nacen en un mundo,
# otros se intercambian por eco en el gabinete.
VERBOS_DEL_MUNDO = [
    "mirar", "esperar", "cruzar", "tocar", "recordar", "preguntar",
    "descifrar", "ordenar",
]
COSTE_VERBOS = {"preguntar": 2, "descifrar": 3}
DURACION_PULSO_MS = 15000
ORDEN_CLARO = ["piedra", "semilla", "agua"]
ORDEN_BIBLIOTECA = ["semilla", "eco", "agua"]
ORDEN_MARTE = ["mercurio", "venus", "tierra", "marte"]

NOMBRES_LUGAR = {
    "nodo": "nodo de acceso",
    "claro": "el claro",
    "biblioteca": "biblioteca subterránea 7",
    "marte": "Marte",
}


class Juego:
    def __init__(self):
        # INICIO | LOGIN_NOMBRE | CONSOLA | CONFIRMAR_OLVIDO | FUERA
        self.estado = "INICIO"
        self.lugar = "nodo"
        self.nombre = None
        self.palabra_semilla = None
        self.verbos = ["mirar"]
        self.mundos = []
        self.eco = 0
        self.salidas = []
        self.tema = "clasico"
        self.banderas = {}

        self.buffer = ""
        self.historial = []
        self.hist_pos = None

    # ----------------------------------------------------------
    # arranque, memoria e interfaz
    # ----------------------------------------------------------

    async def iniciar(self):
        self.cargar_estado()
        window.eco_set_tema(self.tema)
        if self.nombre:
            self.estado = "CONSOLA"
            self.escribir("la máquina abre un ojo.", "sistema")
            self.escribir("")
            self.escribir(f"hola de nuevo, {self.nombre}.", "exito")
            if self.banderas.get("olvido_de_nombre"):
                self.escribir("por un instante te llamó 'el que llegó'. después corrigió.", "tenue")
                self.banderas["olvido_de_nombre"] = False
                self.guardar_estado()
            else:
                self.escribir("el ecosistema te recuerda.")
            self.escribir(f"seguís en {NOMBRES_LUGAR.get(self.lugar, 'el nodo')}.", "sistema")
            self.escribir("F2 abre el tablero. el mapa no habla en el log.", "sistema")
        else:
            await self.login()
        self.sincronizar_interfaz()
        self.mostrar_prompt()

    async def login(self):
        self.escribir("╔══════════════════════════════════════════╗")
        self.escribir("║       ECOSISTEMA / NODO DE ACCESO        ║")
        self.escribir("║       terminal de tránsito · 07         ║")
        self.escribir("╚══════════════════════════════════════════╝")
        self.escribir("")
        self.escribir("enlace entrante. usuario requerido.", "sistema")
        self.escribir("no hay cuentas. no hay verificación. escribí cualquier nombre.", "tenue")
        self.escribir("la máquina lo va a guardar y usar cuando te hable.", "sistema")
        self.escribir("o escribí 'anonimo' para entrar como el que llegó.", "tenue")
        self.escribir("")
        self.estado = "LOGIN_NOMBRE"
        self.sincronizar_interfaz()

    async def paso_nombre(self, texto):
        nombre = " ".join(texto.lower().split())[:24]
        if not nombre:
            self.escribir("el campo vacío no alcanza para que la máquina te nombre.", "sistema")
            return
        if nombre == "anonimo":
            self.nombre = "el que llegó"
            self.palabra_semilla = None
        else:
            self.nombre = nombre
            self.palabra_semilla = None
        await self.entrar()

    async def entrar(self):
        self.estado = "CONSOLA"
        self.escribir("")
        self.escribir(f"el nodo registró: {self.nombre}.", "exito")
        self.escribir("la señal cambia mientras mirás hacia otro lado.", "sistema")
        self.escribir("los comandos disponibles están junto a la consola.", "tenue")
        self.escribir("")
        self.escribir("escribí 'mirar'. cuando el pulso cambie, decidí si cruzás.", "sistema")
        self.guardar_estado()

    def _estado_publico(self):
        ahora = time.time()
        fin_ventana = float(self.banderas.get("ventana_hasta", 0) or 0)
        ventana_ms = max(0, int((fin_ventana - ahora) * 1000))
        if self.banderas.get("claro_visitado") or "claro" in self.mundos:
            ventana_ms = 0
        ubicaciones = ["nodo"]
        if self.lugar == "claro" or self.banderas.get("claro_visitado") or ventana_ms > 0:
            ubicaciones.append("claro")
        if self.lugar == "biblioteca" or "preguntar" in self.verbos:
            ubicaciones.append("biblioteca")
        if self.lugar == "marte" or self.banderas.get("ruta_marte"):
            ubicaciones.append("marte")

        if ventana_ms > 0:
            pulso = "ventana"
        elif (self.lugar == "nodo" and "esperar" in self.verbos
              and not self.banderas.get("claro_visitado")):
            pulso = "cerca"
        elif self.lugar == "claro" and "claro" not in self.mundos:
            pulso = "cerca"
        elif self.lugar == "biblioteca" and "biblioteca" not in self.mundos:
            pulso = "cerca"
        elif self.lugar == "marte" and "marte" not in self.mundos:
            pulso = "cerca"
        elif self.mundos:
            pulso = "eco"
        else:
            pulso = "latente"

        if self.estado in ("LOGIN_NOMBRE", "INICIO"):
            indicio = "la máquina todavía no sabe cómo llamarte."
        elif self.lugar == "nodo" and not self.banderas.get("claro_visitado"):
            indicio = "el intervalo aparece cuando dejás de perseguirlo."
        elif self.lugar == "claro" and "claro" not in self.mundos:
            indicio = "tres marcas ocupan una fila. el orden importa."
        elif self.lugar == "biblioteca" and "biblioteca" not in self.mundos:
            indicio = "tres registros se contradicen; no pueden llegar primeros a la vez."
        elif self.lugar == "biblioteca" and "biblioteca" in self.mundos and not self.banderas.get("ruta_marte"):
            indicio = "ETRAM: una palabra conocida, escrita al revés."
        elif self.lugar == "biblioteca" and "biblioteca" in self.mundos:
            indicio = "Marte ya aparece en el tablero; la nota conserva el reverso."
        elif self.lugar == "marte" and "marte" not in self.mundos:
            indicio = "cuatro órbitas. una fila que se ordena desde el Sol."
        elif "marte" in self.mundos:
            indicio = "la señal de Marte ya tiene nombre. el ruido no terminó."
        elif "biblioteca" in self.mundos:
            indicio = "quedó una señal detrás del último registro."
        elif "claro" in self.mundos:
            indicio = "el gabinete cambió de forma desde la última vez."
        else:
            indicio = "la señal todavía no sabe qué estás buscando."

        return {
            "autenticado": bool(self.nombre) and self.estado != "FUERA",
            "nombre": self.nombre or "el que llegó",
            "lugar": self.lugar,
            "etiqueta_lugar": NOMBRES_LUGAR.get(self.lugar, "nodo de acceso"),
            "tema": self.tema,
            "eco": self.eco,
            "verbos": self.verbos,
            "mundos": self.mundos,
            "salidas": self.salidas,
            "ubicaciones_abiertas": ubicaciones,
            "ventana_ms": ventana_ms,
            "pulso": pulso,
            "indicio": indicio,
            "pistas_biblioteca": self.banderas.get("pistas_biblioteca", []),
            "progreso_claro": self.banderas.get("puzzle_claro", 0),
            "progreso_biblioteca": self.banderas.get("puzzle_biblioteca", 0),
            "progreso_marte": self.banderas.get("puzzle_marte", 0),
        }

    def sincronizar_interfaz(self):
        try:
            estado = json.dumps(self._estado_publico(), ensure_ascii=False)
            window.eco_estado(estado)
        except Exception:
            pass

    def guardar_estado(self):
        estado = {
            "version": 4,
            "nombre": self.nombre,
            "palabra_semilla": self.palabra_semilla,
            "verbos": self.verbos,
            "mundos": self.mundos,
            "eco": self.eco,
            "salidas": self.salidas,
            "tema": self.tema,
            "lugar": self.lugar,
            "banderas": self.banderas,
        }
        try:
            window.localStorage.setItem(CLAVE_ESTADO, json.dumps(estado, ensure_ascii=False))
        except Exception:
            pass
        self.sincronizar_interfaz()

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
            try:
                window.localStorage.removeItem(CLAVE_ESTADO)
            except Exception:
                pass
            return

        self.nombre = estado.get("nombre")
        self.palabra_semilla = estado.get("palabra_semilla")
        self.verbos = estado.get("verbos") or ["mirar"]
        self.mundos = estado.get("mundos") or []
        self.tema = estado.get("tema") if estado.get("tema") in TEMAS else "clasico"
        lugar = estado.get("lugar") or "nodo"
        self.lugar = lugar if lugar in NOMBRES_LUGAR else "nodo"
        self.banderas = estado.get("banderas") or {}
        self.salidas = estado.get("salidas") or []

        # Migración del guardado v0.2: el claro ya estaba resuelto, pero aún
        # no existían la moneda de eco ni su salida descargable.
        try:
            self.eco = max(0, int(estado.get("eco", 0)))
        except (TypeError, ValueError):
            self.eco = 0
        if "claro" in self.mundos:
            self.banderas["claro_visitado"] = True
            if "eco" not in estado:
                self.eco += 3
            self.banderas["recompensa_claro"] = True
            if "eco_mundo_01.txt" not in self.salidas:
                self.salidas.append("eco_mundo_01.txt")
        if "biblioteca" in self.mundos:
            if "eco" not in estado:
                self.eco += 4
            self.banderas["recompensa_biblioteca"] = True
            if "eco_mundo_02.txt" not in self.salidas:
                self.salidas.append("eco_mundo_02.txt")
        if self.lugar == "claro":
            self.banderas["claro_visitado"] = True
        # Reescribe también partidas viejas con el formato vigente y crea
        # las salidas/recompensas que antes no existían.
        self.guardar_estado()

    # ----------------------------------------------------------
    # entrada de consola y navegación de compartimentos
    # ----------------------------------------------------------

    async def procesar_input(self, data):
        if data in ("\x1b[A", "\x1bOA"):
            self.historial_atras()
            return
        if data in ("\x1b[B", "\x1bOB"):
            self.historial_adelante()
            return
        if data.startswith("\x1b"):
            return
        for ch in data:
            await self.procesar_tecla(ch)

    async def procesar_tecla(self, ch):
        if self.estado == "FUERA":
            return
        if ch in ("\r", "\n"):
            window.eco_write("\r\n")
            await self.ejecutar()
        elif ch in ("\x7f", "\x08"):
            if self.buffer:
                self.buffer = self.buffer[:-1]
                window.eco_write("\b \b")
        elif ch == "\x03":
            self.buffer = ""
            window.eco_write("^C")
            self.mostrar_prompt()
        elif ch == "\x0c":
            window.eco_limpiar()
            self.redibujar_linea()
        elif ord(ch) >= 32:
            self.buffer += ch
            window.eco_write(self.eco_de(ch))

    def eco_de(self, ch):
        return ch

    def cancelar_linea_ui(self):
        if self.estado != "CONSOLA":
            return
        self.buffer = ""
        self.hist_pos = None
        window.eco_write("\r\x1b[K" + self.texto_prompt())

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

    async def ejecutar(self):
        texto = self.buffer.strip()
        comando = texto.lower()
        self.buffer = ""
        self.hist_pos = None
        if self.estado == "CONSOLA" and comando:
            if not self.historial or self.historial[-1] != comando:
                self.historial.append(comando)

        if self.estado == "LOGIN_NOMBRE":
            await self.paso_nombre(texto)
        elif self.estado == "CONFIRMAR_OLVIDO":
            await self.paso_olvido(comando)
        elif self.estado == "CONSOLA" and comando:
            await self.procesar_comando(comando)

        if self.estado in ("CONSOLA", "LOGIN_NOMBRE", "CONFIRMAR_OLVIDO"):
            self.mostrar_prompt()
        self.sincronizar_interfaz()

    async def procesar_comando(self, comando):
        partes = comando.split()
        verbo, resto = partes[0], partes[1:]

        if verbo == "verbos":
            self.escribir("verbos que la máquina reconoce:", "sistema")
            for palabra in self.verbos:
                self.escribir(f"  ◈ {palabra}", "eco")
            self.escribir(f"eco disponible: {self.eco:02d}", "tenue")
            return
        if verbo == "tema":
            self.comando_tema(resto[0] if resto else None)
            return
        if verbo in ("mapa", "tablero", "gabinete", "archivo", "consola"):
            destino = "mapa" if verbo == "tablero" else verbo
            ventana = "mapa" if destino == "mapa" else destino
            if ventana in ("mapa", "gabinete", "archivo", "consola"):
                window.eco_cambiar_vista(ventana)
            return
        if verbo == "ayuda":
            self.escribir("la máquina no tiene una habitación llamada ayuda.", "sistema")
            self.escribir("F2: tablero · F3: archivo · F4: gabinete.", "tenue")
            return
        if verbo == "limpiar":
            window.eco_limpiar()
            return
        if verbo == "olvidar":
            self.estado = "CONFIRMAR_OLVIDO"
            self.escribir("¿borrar este recorrido?", "error")
            self.escribir("se perderían tu nombre, tus verbos y los mundos que estabilizaste.", "sistema")
            self.escribir("escribí 'olvido' para hacerlo. cualquier otra cosa para quedarte.", "sistema")
            return
        if verbo == "salir":
            self.estado = "FUERA"
            self.escribir("la máquina guarda silencio, pero no cierra la puerta.", "sistema")
            self.escribir(f"hasta el próximo pulso, {self.nombre}.", "exito")
            self.escribir("(la memoria queda en este navegador.)", "tenue")
            return

        if verbo in VERBOS_DEL_MUNDO and verbo not in self.verbos:
            self.escribir("todavía no tenés ese verbo.", "sistema")
            self.escribir("el gabinete intercambia eco por nuevas maneras de entrar.", "tenue")
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
        elif verbo == "preguntar":
            self.verbo_preguntar(resto)
        elif verbo == "descifrar":
            self.verbo_descifrar(resto)
        elif verbo == "ordenar":
            self.verbo_ordenar(resto)
        else:
            self.escribir("ese movimiento no pertenece a esta máquina.", "error")
            self.escribir("probá otro verbo. escuchá lo que hace el pulso.", "tenue")

    def comando_tema(self, tema):
        if tema is None:
            self.escribir("la luz disponible:", "sistema")
            for nombre in TEMAS:
                marca = " ← activa" if nombre == self.tema else ""
                self.escribir(f"  tema {nombre}{marca}")
        elif tema in TEMAS:
            self.tema = tema
            window.eco_set_tema(tema)
            self.escribir(f"la luz cambia. tema: {tema}.", "exito")
            self.guardar_estado()
        else:
            self.escribir("esa luz no existe en este nodo.", "error")
            self.escribir("escribí 'tema' para leer las frecuencias disponibles.", "tenue")

    async def paso_olvido(self, comando):
        if comando == "olvido":
            try:
                window.localStorage.removeItem(CLAVE_ESTADO)
            except Exception:
                pass
            self.escribir("la máquina cierra los ojos. algo deja de existir.", "sistema")
            self.escribir("")
            self.nombre = None
            self.palabra_semilla = None
            self.verbos = ["mirar"]
            self.mundos = []
            self.eco = 0
            self.salidas = []
            self.tema = "clasico"
            self.banderas = {}
            self.lugar = "nodo"
            self.historial = []
            window.eco_set_tema(self.tema)
            await self.login()
        else:
            self.estado = "CONSOLA"
            self.escribir("mejor así. el nodo sigue encendido.", "sistema")

    # ----------------------------------------------------------
    # interfaz del tablero y del gabinete (fuera del log)
    # ----------------------------------------------------------

    async def viajar_a(self, destino):
        estado = self._estado_publico()
        if destino not in estado["ubicaciones_abiertas"]:
            self.escribir("")
            self.escribir("esa ubicación todavía no responde al tablero.", "error")
            if destino == "claro":
                self.escribir("el intervalo se cerró. esperá hasta sentir otro pulso.", "sistema")
            else:
                self.escribir("el tablero conserva solo las señales que ya reconociste.", "sistema")
            self.mostrar_prompt()
            self.sincronizar_interfaz()
            return
        if destino == self.lugar:
            self.escribir("")
            self.escribir("no hay distancia entre vos y este lugar.", "tenue")
            self.mostrar_prompt()
            return

        window.eco_evento("transito")
        await window.eco_pausa(360)
        anterior = self.lugar
        self.lugar = destino
        window.eco_write("\r\n")
        self.escribir(f"coordenada ajustada: {NOMBRES_LUGAR.get(anterior, anterior)} → {NOMBRES_LUGAR[destino]}.", "tenue")
        self.escribir("")
        self.introducir_lugar(destino)
        if destino == "claro" and not self.banderas.get("claro_visitado"):
            self.banderas["claro_visitado"] = True
            self.banderas["ventana_hasta"] = 0
        if destino == "biblioteca":
            self.banderas["biblioteca_visitada"] = True
        self.guardar_estado()
        self.mostrar_prompt()

    def introducir_lugar(self, destino):
        if destino == "nodo":
            self.escribir("el nodo de acceso", "exito")
            self.escribir("el ruido cambia de forma. todavía podés volver al tablero.", "sistema")
        elif destino == "claro":
            self.escribir("un cambio de presión: el claro.", "exito")
            self.escribir("en el centro, una semilla late junto a un tablero de piedra.")
            self.escribir("podés volver cuando quieras. (cruzar / F2 tablero)", "sistema")
        elif destino == "biblioteca":
            self.escribir("biblioteca subterránea 7", "exito")
            self.escribir("tres registros llegaron sin orden. cada uno conserva una condición.")
            self.escribir("preguntá por agua, semilla y eco. después decidí qué tocás primero.", "sistema")
        elif destino == "marte":
            self.escribir("la señal encontró un nombre: Marte. 🪐", "exito")
            self.escribir("una maqueta de planetario dejó cuatro órbitas sin ordenar.")
            self.escribir("los nombres aparecen en el panel; el Sol no espera que los adivines.", "sistema")

    def comprar_verbo_ui(self, verbo):
        requisitos = {"preguntar": "claro", "descifrar": "biblioteca"}
        mensajes = {
            "preguntar": "preguntar abrió una respuesta bajo tierra.",
            "descifrar": "descifrar ya está en tu vocabulario. la palabra invertida no cambió.",
        }
        if verbo not in requisitos:
            window.eco_mensaje_gabinete("esa ranura todavía no tiene una palabra.", "error")
            return
        if verbo in self.verbos:
            window.eco_mensaje_gabinete(mensajes[verbo], "exito")
            return
        if requisitos[verbo] not in self.mundos:
            window.eco_mensaje_gabinete("la máquina todavía no puso esa palabra en circulación.", "normal")
            return
        coste = COSTE_VERBOS[verbo]
        if self.eco < coste:
            window.eco_mensaje_gabinete("faltan ecos. ningún registro pierde su resonancia.", "error")
            return
        self.eco -= coste
        self.verbos.append(verbo)
        if verbo == "preguntar":
            mensaje = "verbo instalado. una respuesta apareció bajo tierra."
        else:
            mensaje = "verbo instalado. ahora podés leer la línea que quedó al revés."
        window.eco_mensaje_gabinete(mensaje, "exito")
        window.eco_evento("recompensa")
        self.guardar_estado()

    def insertar_comando_ui(self, comando):
        """La paleta de comandos escribe en la consola sin ejecutarlo."""
        if self.estado != "CONSOLA" or not comando:
            return
        texto = " ".join(str(comando).split())
        if not texto:
            return
        self.buffer = texto
        self.hist_pos = None
        window.eco_write("\r\x1b[K" + self.texto_prompt() + texto)

    # ----------------------------------------------------------
    # verbos de exploración
    # ----------------------------------------------------------

    def desbloquear(self, verbo):
        if verbo in self.verbos:
            return False
        self.verbos.append(verbo)
        self.escribir("")
        self.escribir(f"◈ el cuerpo aprendió: {verbo}", "eco")
        self.guardar_estado()
        return True

    def verbo_mirar(self):
        if self.lugar == "nodo":
            self.mirar_nodo()
        elif self.lugar == "claro":
            self.mirar_claro()
        elif self.lugar == "biblioteca":
            self.mirar_biblioteca()
        else:
            self.mirar_marte()

    def mirar_nodo(self):
        self.escribir("mirás alrededor. la consola devuelve las señales que ya reconocés:", "exito")
        conocidas = self._estado_publico()["ubicaciones_abiertas"]
        self.escribir("  " + " · ".join(NOMBRES_LUGAR[lugar] for lugar in conocidas), "eco")
        self.escribir("")
        if self.banderas.get("claro_visitado"):
            self.escribir("la casilla conocida vuelve a respirar. otra quedó debajo del ruido.", "sistema")
            self.escribir("F2 para ver el tablero. 'cruzar' también sigue funcionando.", "tenue")
            return
        if "esperar" not in self.verbos:
            self.escribir("algo pulsa detrás del ruido. no responde a la velocidad.", "sistema")
            self.escribir("el borde de la consola tiembla una vez.", "tenue")
            window.eco_pulso("cerca", 0)
            self.desbloquear("esperar")
            return
        if "cruzar" not in self.verbos:
            self.escribir("el pulso deja un hueco del tamaño de una persona.", "sistema")
            self.escribir("esperar abre el intervalo; cruzar no espera por siempre.", "tenue")
        else:
            self.escribir("el intervalo vuelve a cerrarse cuando termina de respirar.", "sistema")
            self.escribir("esperar para encontrar la próxima ventana.", "tenue")

    async def verbo_esperar(self):
        if self.lugar == "claro":
            self.escribir("esperás. la semilla acompasa el agua, pero no resuelve la fila.", "sistema")
            return
        if self.lugar == "biblioteca":
            self.escribir("esperás. los registros no cambian de orden por sí solos.", "sistema")
            return
        if self.lugar == "marte":
            self.escribir("esperás. las órbitas siguen su curso aunque la consola calle.", "sistema")
            return
        if self.banderas.get("claro_visitado"):
            self.banderas["esperas"] = self.banderas.get("esperas", 0) + 1
            self.escribir("esperás. el primer cruce ya conoce tu paso.", "sistema")
            self.guardar_estado()
            return

        ahora = time.time()
        hasta = float(self.banderas.get("ventana_hasta", 0) or 0)
        if hasta > ahora:
            self.escribir("el intervalo sigue abierto.", "exito")
            self.escribir("la señal no necesita otra todavía.", "tenue")
            return

        self.banderas["esperas"] = self.banderas.get("esperas", 0) + 1
        await window.eco_pausa(420)
        self.banderas["ventana_hasta"] = time.time() + DURACION_PULSO_MS / 1000
        self.escribir("contás el ruido de fondo. uno. dos. ...", "tenue")
        if "cruzar" not in self.verbos:
            self.desbloquear("cruzar")
        self.escribir("el pulso se abre: quedan quince segundos para entrar.", "exito")
        self.escribir("cruzá ahora o elegí el lugar iluminado en F2.", "sistema")
        window.eco_pulso("ventana", DURACION_PULSO_MS)
        self.guardar_estado()

    def verbo_cruzar(self):
        if self.lugar == "nodo":
            if "cruzar" not in self.verbos:
                self.escribir("la señal está ahí, pero todavía no aprendiste a cruzar.", "sistema")
                return
            if not self.banderas.get("claro_visitado"):
                hasta = float(self.banderas.get("ventana_hasta", 0) or 0)
                if hasta <= time.time():
                    self.banderas["ventana_hasta"] = 0
                    self.escribir("el intervalo se cerró antes de que llegaras.", "error")
                    self.escribir("esperá otra vez. no perdiste nada.", "sistema")
                    window.eco_pulso("latente", 0)
                    self.guardar_estado()
                    return
                self.banderas["claro_visitado"] = True
                self.banderas["ventana_hasta"] = 0
            self.lugar = "claro"
            self.escribir("cruzás.", "exito")
            self.escribir("la presión cambia al cruzar.")
            self.escribir("")
            self.introducir_lugar("claro")
            self.guardar_estado()
        else:
            anterior = self.lugar
            self.lugar = "nodo"
            self.escribir("cruzás de vuelta.", "exito")
            self.escribir("el nodo recibe el ruido que trajiste.", "sistema")
            if anterior == "claro" and "claro" in self.mundos and not self.banderas.get("olvido_de_nombre"):
                self.banderas["olvido_de_nombre"] = True
                self.escribir(f"un segundo te llama 'el que llegó'. después recuerda: {self.nombre}.", "tenue")
            self.guardar_estado()

    def mirar_claro(self):
        self.escribir("mirás el claro. la consola toma la forma de una mesa pequeña.", "exito")
        self.escribir("tres marcas, tres ranuras. la fila no se arma sola.")
        if "claro" in self.mundos:
            self.escribir("")
            self.escribir("la semilla ahora es un brote. el agua sigue sin detenerse.", "sistema")
            self.escribir("una casilla nueva espera eco en el gabinete.", "tenue")
            return
        self.escribir("")
        self.escribir("la inscripción se partió en tres:", "sistema")
        self.escribir("  agua: no fui la primera.")
        self.escribir("  piedra: me moví antes de lo que despierta.")
        self.escribir("  semilla: no cierro la fila.")
        self.escribir("")
        if "tocar" not in self.verbos:
            self.escribir("la mesa deja tres ranuras libres.", "tenue")
            self.desbloquear("tocar")
        else:
            progreso = int(self.banderas.get("puzzle_claro", 0))
            self.escribir(f"marcas sincronizadas: {progreso}/3. elegí qué tocar primero.", "tenue")

    def verbo_tocar(self, resto):
        if not resto:
            if self.lugar == "claro" and "claro" not in self.mundos:
                progreso = int(self.banderas.get("puzzle_claro", 0))
                self.escribir(f"la mesa espera una pieza para la ranura {progreso + 1}/3.", "sistema")
                self.escribir("tocar piedra / tocar semilla / tocar agua", "tenue")
            elif self.lugar == "biblioteca" and "biblioteca" not in self.mundos:
                self.escribir("¿qué registro querés mover? agua, semilla o eco.", "sistema")
            else:
                self.escribir("¿tocar qué?", "sistema")
            return

        objeto = resto[0]
        if self.lugar == "claro":
            self.tocar_claro(objeto)
        elif self.lugar == "biblioteca":
            self.tocar_biblioteca(objeto)
        else:
            self.escribir("acá solo hay un nodo y una máquina que finge no mirar.", "sistema")

    def tocar_claro(self, objeto):
        if "claro" in self.mundos:
            if objeto in ("semilla", "brote"):
                self.escribir("tocás el brote. el lugar devuelve un pulso conocido.", "exito")
            elif objeto in ("agua", "piedra"):
                self.escribir(f"tocás {objeto}. ya no hay una ranura que completar.", "tenue")
            else:
                self.escribir(f"el claro no reconoce '{objeto}'.", "error")
            return

        aliases = {"roca": "piedra", "tierra": "piedra"}
        objeto = aliases.get(objeto, objeto)
        if objeto not in ORDEN_CLARO:
            self.escribir(f"no hay una marca llamada '{objeto}'.", "error")
            return
        progreso = int(self.banderas.get("puzzle_claro", 0))
        esperado = ORDEN_CLARO[progreso]
        if objeto != esperado:
            self.banderas["puzzle_claro"] = 0
            self.escribir(f"la ranura {progreso + 1} rechaza {objeto}.", "error")
            self.escribir("las piezas vuelven a la mesa. mirá las tres condiciones otra vez.", "sistema")
            self.guardar_estado()
            window.eco_pulso("cerca", 0)
            return
        progreso += 1
        self.banderas["puzzle_claro"] = progreso
        self.escribir(f"la marca encaja: {objeto} · {progreso}/3", "eco")
        if progreso == len(ORDEN_CLARO):
            self.completar_claro()
        else:
            self.escribir("la mesa conserva el orden. la siguiente pieza no se adivina sola.", "tenue")
            self.guardar_estado()

    def completar_claro(self):
        if "claro" not in self.mundos:
            self.mundos.append("claro")
        if not self.banderas.get("recompensa_claro"):
            self.eco += 3
            self.banderas["recompensa_claro"] = True
        self.banderas["puzzle_claro"] = 3
        self.banderas["olvido_de_nombre"] = False
        if "eco_mundo_01.txt" not in self.salidas:
            self.salidas.append("eco_mundo_01.txt")
        self.escribir("")
        self.escribir("las tres marcas se alinean. la consola deja de zumbar.", "exito")
        self.escribir("el nodo se estabilizó.", "exito")
        self.escribir("resonancia +03 eco.", "eco")
        self.escribir("el gabinete recibió una palabra: preguntar · 02 eco.", "sistema")
        self.escribir("el tablero anotó una señal que todavía no sabe nombrar.", "tenue")
        self.desbloquear("recordar")
        window.eco_evento("recompensa")
        window.eco_pulso("eco", 0)
        self.guardar_estado()

    def mirar_biblioteca(self):
        self.escribir("mirás la biblioteca. los estantes están vacíos salvo por tres fichas.", "exito")
        if "biblioteca" in self.mundos:
            self.escribir("la secuencia reconstruida quedó guardada en el archivo.", "sistema")
            if not self.banderas.get("ruta_marte"):
                self.escribir("en el margen: ETRAM. una palabra conocida, escrita en sentido contrario.", "eco")
                if "descifrar" in self.verbos:
                    self.escribir("la consola acepta: descifrar [texto].", "sistema")
                else:
                    self.escribir("el gabinete quizá tenga una forma de leer lo invertido.", "tenue")
            else:
                self.escribir("el borde del papel se quemó en forma de planeta rojo.", "tenue")
            return
        pistas = self.banderas.get("pistas_biblioteca", [])
        self.escribir(f"registros preguntados: {len(set(pistas))}/3.", "tenue")
        if len(set(pistas)) < 3:
            self.escribir("los sellos dicen: agua · semilla · eco.", "sistema")
            self.escribir("preguntá por cada uno. tocar una ficha antes de leer los sellos no sirve.", "tenue")
        else:
            progreso = int(self.banderas.get("puzzle_biblioteca", 0))
            self.escribir(f"secuencia propuesta: {progreso}/3 fichas colocadas.", "sistema")
            self.escribir("cuando tengas un orden, tocá las fichas de a una.", "tenue")

    def verbo_preguntar(self, resto):
        if self.lugar == "marte":
            self.preguntar_marte(resto)
            return
        if self.lugar != "biblioteca":
            self.escribir("la pregunta sale de la consola, pero no encuentra a quién llegar.", "sistema")
            return
        if "biblioteca" in self.mundos:
            self.escribir("la biblioteca ya respondió. la nueva señal pide otra palabra.", "sistema")
            return
        if not resto:
            pistas = self.banderas.get("pistas_biblioteca", [])
            faltan = [x for x in ("agua", "semilla", "eco") if x not in pistas]
            if faltan:
                self.escribir("tres sellos esperan una pregunta.", "sistema")
                self.escribir("preguntar agua / preguntar semilla / preguntar eco", "tenue")
            else:
                self.escribir("las tres condiciones ya están en el log. la máquina no las va a ordenar.", "sistema")
                self.escribir("ahora podés tocar las fichas según lo que dedujiste.", "sistema")
            return

        objetivo = resto[0]
        aliases = {"a": "agua", "s": "semilla", "e": "eco", "archivo": "eco"}
        objetivo = aliases.get(objetivo, objetivo)
        pistas = self.banderas.setdefault("pistas_biblioteca", [])
        condiciones = {
            "agua": "el agua llegó después del eco.",
            "semilla": "la semilla no llegó después del agua.",
            "eco": "el eco no fue lo primero que llegó.",
        }
        if objetivo not in condiciones:
            self.escribir("ese registro no tiene un sello legible.", "error")
            self.escribir("probá agua, semilla o eco.", "tenue")
            return
        if objetivo not in pistas:
            pistas.append(objetivo)
        self.escribir(f"preguntás por {objetivo}.", "exito")
        self.escribir(condiciones[objetivo], "sistema")
        leidos = len(set(pistas))
        self.escribir(f"condiciones reunidas: {leidos}/3.", "tenue")
        if leidos == 3:
            self.escribir("cuando el orden te cierre, tocá las fichas una por una.", "sistema")
        self.guardar_estado()
        window.eco_pulso("cerca", 0)

    def preguntar_marte(self, resto):
        if "marte" in self.mundos:
            self.escribir("el planetario ya registró la secuencia.", "sistema")
            return
        if not resto:
            self.escribir("la transmisión responde sobre el Sol o las órbitas.", "tenue")
            return
        tema = resto[0]
        if tema in ("sol", "órbita", "orbitas", "orden", "planetas"):
            self.escribir("Mercurio es el planeta más cercano al Sol.", "sistema")
            self.escribir("la Tierra queda entre Venus y Marte.", "sistema")
            self.escribir("el resto lo decide tu memoria.", "tenue")
        else:
            self.escribir("la señal no reconoce esa pregunta todavía.", "tenue")

    def tocar_biblioteca(self, objeto):
        if "biblioteca" in self.mundos:
            self.escribir("la secuencia ya quedó grabada. las fichas no se mueven.", "tenue")
            return
        objeto = {"a": "agua", "s": "semilla", "e": "eco", "archivo": "eco"}.get(objeto, objeto)
        if objeto not in ORDEN_BIBLIOTECA:
            self.escribir(f"la ficha '{objeto}' no pertenece a esta mesa.", "error")
            return
        pistas = set(self.banderas.get("pistas_biblioteca", []))
        if pistas != {"agua", "semilla", "eco"}:
            self.escribir("la mesa todavía no recibe piezas.", "sistema")
            self.escribir("primero leé los tres sellos: agua, semilla y eco.", "tenue")
            return
        progreso = int(self.banderas.get("puzzle_biblioteca", 0))
        esperado = ORDEN_BIBLIOTECA[progreso]
        if objeto != esperado:
            self.banderas["puzzle_biblioteca"] = 0
            self.escribir("la secuencia no coincide. las fichas vuelven al margen.", "error")
            self.escribir("no se borraron las condiciones; podés intentarlo de nuevo.", "sistema")
            self.guardar_estado()
            return
        progreso += 1
        self.banderas["puzzle_biblioteca"] = progreso
        self.escribir(f"registro ordenado: {objeto} · {progreso}/3", "eco")
        if progreso == len(ORDEN_BIBLIOTECA):
            self.completar_biblioteca()
        else:
            self.escribir("la biblioteca espera la siguiente ficha.", "tenue")
            self.guardar_estado()

    def completar_biblioteca(self):
        if "biblioteca" not in self.mundos:
            self.mundos.append("biblioteca")
        if not self.banderas.get("recompensa_biblioteca"):
            self.eco += 4
            self.banderas["recompensa_biblioteca"] = True
        self.banderas["puzzle_biblioteca"] = 3
        if "eco_mundo_02.txt" not in self.salidas:
            self.salidas.append("eco_mundo_02.txt")
        self.escribir("")
        self.escribir("los registros dejaron de contradecirse.", "exito")
        self.escribir("la biblioteca se estabilizó.", "exito")
        self.escribir("resonancia +04 eco.", "eco")
        self.escribir("un archivo nuevo quedó esperando en el compartimento 03.", "sistema")
        self.escribir("la máquina oyó otra señal. todavía no sabe cómo llamarla.", "tenue")
        self.escribir("en el margen quedó ETRAM. la palabra parece conocida, aunque venga al revés.", "eco")
        self.escribir("el gabinete recibió una nueva frecuencia.", "tenue")
        window.eco_evento("recompensa")
        window.eco_pulso("eco", 0)
        self.guardar_estado()

    def verbo_descifrar(self, resto):
        if "biblioteca" not in self.mundos:
            self.escribir("todavía no hay suficientes registros para leer el margen.", "sistema")
            return
        if not resto:
            self.escribir("la consola necesita una cadena. el margen conserva cuatro letras.", "sistema")
            return
        cadena = "".join(resto).strip().upper()
        if cadena == "MARTE":
            self.escribir("la palabra ya se puede leer. el registro, no.", "tenue")
            self.escribir("probá desde el otro extremo.", "sistema")
            return
        if cadena != "ETRAM":
            self.escribir("la cadena no encontró una órbita.", "error")
            self.escribir("la nota sigue al revés, en la biblioteca.", "tenue")
            return
        if self.banderas.get("ruta_marte"):
            self.escribir("Marte ya aparece en el tablero. el punto rojo no se mueve.", "tenue")
            return
        self.banderas["ruta_marte"] = True
        self.escribir("la cadena invierte su dirección: MARTE.", "exito")
        self.escribir("un punto rojo apareció en la cartografía, sin advertencia.", "sistema")
        self.desbloquear("ordenar")
        window.eco_evento("transito")
        self.guardar_estado()

    def mirar_marte(self):
        self.escribir("mirás el planetario. cuatro tarjetas tiemblan dentro de sus órbitas.", "exito")
        if "marte" in self.mundos:
            self.escribir("la fila solar sigue girando en el archivo.", "sistema")
            self.escribir("más allá, el ruido todavía no tiene país.", "tenue")
            return
        self.escribir("marte · venus · mercurio · tierra", "eco")
        self.escribir("la indicación es simple: ordená desde el Sol hacia afuera.", "sistema")
        self.escribir("Mercurio abre la órbita; el planeta rojo queda en la cuarta.", "tenue")
        progreso = int(self.banderas.get("puzzle_marte", 0))
        self.escribir(f"órbitas sincronizadas: {progreso}/4.", "tenue")
        self.escribir("usar: ordenar [los cuatro nombres]", "sistema")

    def verbo_ordenar(self, resto):
        if self.lugar != "marte":
            self.escribir("no hay órbitas que ordenar en esta coordenada.", "sistema")
            return
        if "marte" in self.mundos:
            self.escribir("el planetario conserva la fila que armaste.", "tenue")
            return
        nombres = ["".join(char for char in palabra if char.isalpha()) for palabra in resto]
        if len(nombres) != 4:
            self.escribir("faltan tarjetas. hay cuatro órbitas y cuatro nombres.", "sistema")
            self.escribir("la orientación va desde el Sol hacia afuera.", "tenue")
            return
        if nombres != ORDEN_MARTE:
            intentos = int(self.banderas.get("intentos_marte", 0)) + 1
            self.banderas["intentos_marte"] = intentos
            self.escribir("las órbitas no aceptan esa disposición.", "error")
            if intentos >= 2:
                self.escribir("recordá: Mercurio queda más cerca del Sol; Marte es el planeta rojo.", "sistema")
            else:
                self.escribir("el panel conserva los cuatro nombres. podés probar otra vez.", "tenue")
            self.guardar_estado()
            return
        self.banderas["puzzle_marte"] = 4
        self.escribir("las cuatro tarjetas encajan. el planetario deja de temblar.", "exito")
        self.completar_marte()

    def completar_marte(self):
        if "marte" not in self.mundos:
            self.mundos.append("marte")
        if not self.banderas.get("recompensa_marte"):
            self.eco += 5
            self.banderas["recompensa_marte"] = True
        if "eco_mundo_03.txt" not in self.salidas:
            self.salidas.append("eco_mundo_03.txt")
        self.escribir("Marte estabilizó su órbita.", "exito")
        self.escribir("resonancia +05 eco.", "eco")
        self.escribir("el archivo guardó una forma más precisa del cielo.", "sistema")
        window.eco_evento("recompensa")
        window.eco_pulso("eco", 0)
        self.guardar_estado()

    def verbo_recordar(self):
        self.escribir("el registro disponible:", "sistema")
        self.escribir(f"  te llama: {self.nombre}")
        self.escribir("  anclaje: guardado en este navegador; nunca escrito en el log." if self.palabra_semilla else "  anclaje: ninguno.")
        self.escribir(f"  lugar: {NOMBRES_LUGAR.get(self.lugar, self.lugar)}")
        self.escribir(f"  eco: {self.eco:02d}")
        self.escribir(f"  verbos: {', '.join(self.verbos)}")
        self.escribir(f"  mundos estables: {', '.join(self.mundos) if self.mundos else 'ninguno'}")
        self.escribir(f"  salidas: {', '.join(self.salidas) if self.salidas else 'ninguna'}")
        esperas = self.banderas.get("esperas", 0)
        self.escribir(f"  pulsos esperados: {esperas}")

    # ----------------------------------------------------------
    # salida
    # ----------------------------------------------------------

    def escribir(self, texto, estilo="normal"):
        window.eco_writeln(str(texto), estilo)

    def texto_prompt(self):
        if self.estado == "CONSOLA":
            nombre = self.nombre or "el que llegó"
            sitio = {"nodo": "nodo-07", "claro": "claro", "biblioteca": "biblioteca-7"}.get(self.lugar, "nodo-07")
            return f"{nombre}@{sitio} > "
        if self.estado == "LOGIN_NOMBRE":
            return "usuario: "
        if self.estado == "CONFIRMAR_OLVIDO":
            return "confirmar > "
        return "> "

    def mostrar_prompt(self):
        window.eco_write("\r\n" + self.texto_prompt())


# Fin del motor. Las vistas y los gráficos viven en index.html / estilos.css.
