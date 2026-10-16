"""Servidor Web simulado: ejercicio jefe-trabajador y refinamiento.

No abre conexiones de red. Emplea Semaphore, Condition y Queue de Python.
Al cerrar, atiende la cola y cada hilo informa su rendimiento antes de salir.
"""

import queue
import random
import threading
import time
import tkinter as tk
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from tkinter import ttk

RESERVA = 3
MAX_TRABAJADORES = 8
DURACION_MIN = 2.0
DURACION_MAX = 4.0
PAGINAS = ("/inicio", "/productos", "/contacto", "/usuarios")


class Servidor:
    """Hilo jefe + trabajadores; nunca actualiza widgets de Tkinter."""

    def __init__(self):
        self.solicitudes = queue.Queue()
        self.eventos = queue.Queue()
        self.condicion = threading.Condition()  # Incorpora un candado.
        self.trabajadores = {}                  # Identificador -> datos.
        self.hilos = {}                         # Identificador -> Thread.
        self.libres = deque()
        self.reportes = {}                      # Un reporte por hilo terminado.
        self.siguiente_trabajador = 0
        self.siguiente_solicitud = 0
        self.aceptando = True
        self.jefe_termino = False

        with self.condicion:
            for _ in range(RESERVA):
                self._crear_trabajador()

        self.hilo_jefe = threading.Thread(target=self._jefe, daemon=True)
        self.hilo_jefe.start()

    def _crear_trabajador(self):
        """Debe llamarse con la condición adquirida."""
        self.siguiente_trabajador += 1
        numero = self.siguiente_trabajador
        self.trabajadores[numero] = {
            "semaforo": threading.Semaphore(0),  # Empieza dormido.
            "tarea": None,
            "atendidas": 0,
            "tiempo": 0.0,
            "paginas": Counter(),
        }
        self.libres.append(numero)
        self.eventos.put(("nuevo", numero))
        hilo = threading.Thread(target=self._trabajador, args=(numero,), daemon=True)
        self.hilos[numero] = hilo
        hilo.start()

    def enviar(self, pagina):
        """Introduce una petición de manera segura respecto al cierre."""
        with self.condicion:
            if not self.aceptando:
                return False
            self.siguiente_solicitud += 1
            numero = self.siguiente_solicitud
            self.eventos.put(("recibida", numero, pagina))
            self.solicitudes.put((numero, pagina))
            return True

    def _jefe(self):
        """Extrae solicitudes de la cola y despierta un hilo disponible."""
        while True:
            tarea = self.solicitudes.get()  # Bloquea si aún no llega trabajo.

            if tarea is None:              # Señal de cierre, al final de la cola.
                with self.condicion:
                    self.jefe_termino = True
                    # Los trabajadores libres deben despertar para terminar.
                    for numero in self.libres:
                        self.trabajadores[numero]["semaforo"].release()
                return

            with self.condicion:
                while not self.libres:
                    if len(self.trabajadores) < MAX_TRABAJADORES:
                        self._crear_trabajador()
                    else:
                        self.condicion.wait()  # Espera sin sondeo activo.

                numero = self.libres.popleft()
                datos = self.trabajadores[numero]
                datos["tarea"] = tarea
                self.eventos.put(("asignada", numero, tarea[0], tarea[1]))
                datos["semaforo"].release()  # Señal P/V: despertar a este hilo.

                # Mantener k=RESERVA hilos disponibles si cabe en el límite.
                while (len(self.libres) < RESERVA
                       and len(self.trabajadores) < MAX_TRABAJADORES):
                    self._crear_trabajador()

    def _trabajador(self, numero):
        """Atiende trabajos; antes de salir entrega un informe final."""
        datos = self.trabajadores[numero]
        try:
            while True:
                datos["semaforo"].acquire()  # Dormir hasta recibir una señal.

                with self.condicion:
                    tarea = datos["tarea"]
                    datos["tarea"] = None

                if tarea is None:         # El jefe ordenó finalizar.
                    break

                identificador, pagina = tarea
                inicio = time.perf_counter()
                time.sleep(random.uniform(DURACION_MIN, DURACION_MAX))
                duracion = time.perf_counter() - inicio

                with self.condicion:
                    datos["atendidas"] += 1
                    datos["tiempo"] += duracion
                    datos["paginas"][pagina] += 1
                    self.eventos.put(("terminada", numero, identificador,
                                      pagina, duracion, datos["atendidas"]))

                    if self.jefe_termino:
                        # Ya no llegarán nuevos trabajos: termina el hilo.
                        break

                    self.libres.append(numero)
                    self.condicion.notify()  # Despertar al jefe si esperaba.
        finally:
            # REFINAMIENTO: el propio trabajador informa ANTES de finalizar.
            with self.condicion:
                informe = {
                    "atendidas": datos["atendidas"],
                    "tiempo": datos["tiempo"],
                    "paginas": dict(datos["paginas"]),
                }
                self.reportes[numero] = informe
                self.eventos.put(("informe_hilo", numero, informe))

    def iniciar_cierre(self):
        """Deja de aceptar solicitudes y coloca el aviso al final de la cola."""
        with self.condicion:
            if not self.aceptando:
                return
            self.aceptando = False
            self.solicitudes.put(None)  # Las solicitudes anteriores NO se pierden.
            self.eventos.put(("cierre_iniciado",))

    def esperar_cierre(self):
        """Ejecutar desde un hilo auxiliar para no congelar Tkinter."""
        self.hilo_jefe.join()
        for hilo in self.hilos.values():
            hilo.join()

        with self.condicion:
            assert len(self.reportes) == len(self.hilos)
            reportes = {n: {"atendidas": r["atendidas"],
                            "tiempo": r["tiempo"], "paginas": dict(r["paginas"])}
                        for n, r in sorted(self.reportes.items())}
            return self.siguiente_solicitud, reportes


def construir_informe(total_recibidas, reportes):
    """Informe legible del refinamiento; se calcula después del join()."""
    total_atendidas = sum(r["atendidas"] for r in reportes.values())
    duracion = sum(r["tiempo"] for r in reportes.values())
    paginas = Counter()
    for datos in reportes.values():
        paginas.update(datos["paginas"])

    lineas = [
        "INFORME FINAL - SERVIDOR WEB SIMULADO",
        "Modelo jefe-trabajador | Refinamiento: contabilidad de hilos",
        "=" * 60,
        f"Solicitudes recibidas: {total_recibidas}",
        f"Solicitudes atendidas: {total_atendidas}",
        f"Trabajadores que finalizaron e informaron: {len(reportes)}",
        f"Tiempo total acumulado de procesamiento: {duracion:.2f} s",
        f"Promedio por solicitud: {duracion / total_atendidas:.2f} s"
        if total_atendidas else "Promedio por solicitud: sin solicitudes",
        "",
        "PÁGINAS SOLICITADAS",
    ]
    lineas.extend(f"  {pagina}: {cantidad}" for pagina, cantidad in sorted(paginas.items()))
    if not paginas:
        lineas.append("  Ninguna")

    lineas.extend(["", "RENDIMIENTO INDIVIDUAL"])
    for numero, datos in reportes.items():
        promedio = (datos["tiempo"] / datos["atendidas"]
                    if datos["atendidas"] else 0.0)
        lineas.append(
            f"  Hilo {numero}: {datos['atendidas']} solicitud(es), "
            f"{datos['tiempo']:.2f} s acumulados, promedio {promedio:.2f} s"
        )
        for pagina, cantidad in sorted(datos["paginas"].items()):
            lineas.append(f"    {pagina}: {cantidad}")
    lineas.append("=" * 60)
    return "\n".join(lineas) + "\n"


class Interfaz:
    """Todas las actualizaciones de Tkinter ocurren en el hilo principal."""

    def __init__(self, raiz):
        self.raiz = raiz
        self.servidor = Servidor()
        self.recibidas = self.pendientes = self.procesando = 0
        self.terminadas = 0
        self.total_duracion = 0.0
        self.cerrando = False
        self.cierre_completo = False

        self.raiz.title("Servidor Web | Simulación de sincronización")
        self.raiz.geometry("850x680")
        self.raiz.minsize(730, 590)
        self.raiz.configure(bg="#101827")
        self._construir()
        self.raiz.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.raiz.after(80, self._leer_eventos)

    def _construir(self):
        fondo, panel = "#101827", "#1d2a3d"
        texto, secundario = "#f4f7fb", "#b5c4d5"
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("Tabla.Treeview", background=panel,
                         fieldbackground=panel, foreground=texto,
                         rowheight=29, borderwidth=0)
        estilo.configure("Tabla.Treeview.Heading", background="#293b54",
                         foreground=texto, relief="flat", padding=7)
        estilo.map("Tabla.Treeview", background=[("selected", "#345677")])

        contenedor = tk.Frame(self.raiz, bg=fondo, padx=20, pady=17)
        contenedor.pack(fill="both", expand=True)
        tk.Label(contenedor, text="SERVIDOR WEB SIMULADO", bg=fondo,
                 fg=texto, font=("Arial", 19, "bold")).pack(anchor="w")
        tk.Label(contenedor, text="Modelo jefe-trabajador | Semáforos y condición",
                 bg=fondo, fg=secundario).pack(anchor="w", pady=(1, 15))

        acciones = tk.Frame(contenedor, bg=panel, padx=12, pady=12)
        acciones.pack(fill="x")
        tk.Label(acciones, text="Página:", bg=panel, fg=texto).pack(side="left")
        self.pagina = ttk.Combobox(acciones, values=PAGINAS, state="readonly", width=15)
        self.pagina.set(PAGINAS[0])
        self.pagina.pack(side="left", padx=8)
        self.boton_enviar = tk.Button(acciones, text="Enviar solicitud", command=self._enviar,
                                     bg="#3c82db", fg="white", relief="flat", padx=8, pady=6)
        self.boton_enviar.pack(side="left", padx=3)
        self.boton_rafaga = tk.Button(acciones, text="Enviar 5", command=self._rafaga,
                                     bg="#35516e", fg="white", relief="flat", padx=8, pady=6)
        self.boton_rafaga.pack(side="left", padx=3)
        self.boton_cerrar = tk.Button(acciones, text="Finalizar e informar",
                                     command=self._iniciar_cierre, bg="#327d68",
                                     fg="white", relief="flat", padx=8, pady=6)
        self.boton_cerrar.pack(side="right", padx=3)

        resumen = tk.Frame(contenedor, bg=fondo)
        resumen.pack(fill="x", pady=13)
        self.indicadores = {}
        for clave, titulo in (("recibidas", "Recibidas"),
                              ("pendientes", "En cola"),
                              ("procesando", "En proceso"),
                              ("terminadas", "Terminadas")):
            caja = tk.Frame(resumen, bg=panel, padx=12, pady=8)
            caja.pack(side="left", expand=True, fill="x", padx=3)
            cifra = tk.Label(caja, text="0", bg=panel, fg=texto,
                             font=("Arial", 20, "bold"))
            cifra.pack()
            tk.Label(caja, text=titulo, bg=panel, fg=secundario).pack()
            self.indicadores[clave] = cifra

        tk.Label(contenedor, text="Trabajadores", bg=fondo, fg=texto,
                 font=("Arial", 12, "bold")).pack(anchor="w", pady=(4, 6))
        tabla_panel = tk.Frame(contenedor, bg=panel)
        tabla_panel.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(tabla_panel, style="Tabla.Treeview",
                                  columns=("estado", "pagina", "total"),
                                  show="tree headings", height=7)
        for columna, titulo in (("#0", "Hilo"), ("estado", "Estado"),
                                ("pagina", "Página"), ("total", "Atendidas")):
            self.tabla.heading(columna, text=titulo)
        self.tabla.column("#0", width=90)
        self.tabla.column("estado", width=130)
        self.tabla.column("pagina", width=155)
        self.tabla.column("total", width=85, stretch=False, anchor="center")
        barra = ttk.Scrollbar(tabla_panel, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tabla.pack(fill="both", expand=True)

        tk.Label(contenedor, text="Historial de eventos", bg=fondo, fg=texto,
                 font=("Arial", 12, "bold")).pack(anchor="w", pady=(13, 5))
        self.historial = tk.Text(contenedor, height=8, bg=panel, fg=texto,
                                 relief="flat", padx=10, pady=8,
                                 font=("Consolas", 10), state="disabled")
        self.historial.pack(fill="both", expand=True)
        self.pie = tk.Label(contenedor,
                            text="Tiempo promedio: — | Máximo de trabajadores: 8",
                            bg=fondo, fg=secundario, anchor="w")
        self.pie.pack(fill="x", pady=(8, 0))

    def _enviar(self):
        self.servidor.enviar(self.pagina.get())

    def _rafaga(self):
        for _ in range(5):
            self._enviar()

    def _escribir(self, mensaje):
        hora = datetime.now().strftime("%H:%M:%S")
        self.historial.configure(state="normal")
        self.historial.insert("end", f"[{hora}] {mensaje}\n")
        self.historial.see("end")
        self.historial.configure(state="disabled")

    def _leer_eventos(self):
        try:
            while True:
                evento = self.servidor.eventos.get_nowait()
                tipo = evento[0]
                if tipo == "nuevo":
                    _, numero = evento
                    self.tabla.insert("", "end", iid=str(numero),
                                      text=f"Hilo {numero}",
                                      values=("Dormido", "—", 0))
                    self._escribir(f"Se creó el trabajador {numero}.")
                elif tipo == "recibida":
                    _, ident, pagina = evento
                    self.recibidas += 1
                    self.pendientes += 1
                    self._escribir(f"Solicitud #{ident}: {pagina} (recibida).")
                elif tipo == "asignada":
                    _, numero, ident, pagina = evento
                    self.pendientes -= 1
                    self.procesando += 1
                    anteriores = self.tabla.item(str(numero), "values")
                    self.tabla.item(str(numero), values=("Procesando", pagina, anteriores[2]))
                    self._escribir(f"Trabajador {numero} atiende #{ident}.")
                elif tipo == "terminada":
                    _, numero, ident, pagina, duracion, atendidas = evento
                    self.procesando -= 1
                    self.terminadas += 1
                    self.total_duracion += duracion
                    self.tabla.item(str(numero), values=("Dormido", "—", atendidas))
                    self._escribir(f"Trabajador {numero} terminó #{ident} ({pagina}) "
                                  f"en {duracion:.2f} s.")
                elif tipo == "informe_hilo":
                    _, numero, informe = evento
                    self.tabla.item(str(numero), values=("Finalizado", "—", informe["atendidas"]))
                    self._escribir(f"Hilo {numero} notificó su rendimiento final: "
                                  f"{informe['atendidas']} solicitud(es).")
                elif tipo == "cierre_iniciado":
                    self._escribir("Cierre iniciado: se atenderá toda la cola antes de terminar.")
                elif tipo == "cierre_completo":
                    _, ruta, informe, error = evento
                    self.cierre_completo = True
                    self.boton_cerrar.configure(text="Ver informe", state="normal",
                                                command=lambda: self._mostrar_informe(ruta, informe, error))
                    self._escribir("Todos los trabajadores finalizaron y notificaron su rendimiento.")
                    self._mostrar_informe(ruta, informe, error)
                self._actualizar_resumen()
        except queue.Empty:
            pass
        if self.raiz.winfo_exists():
            self.raiz.after(80, self._leer_eventos)

    def _actualizar_resumen(self):
        for nombre in self.indicadores:
            self.indicadores[nombre].configure(text=str(getattr(self, nombre)))
        promedio = (f"{self.total_duracion / self.terminadas:.2f} s"
                    if self.terminadas else "—")
        self.pie.configure(text=(f"Tiempo promedio: {promedio} | "
                                   f"Trabajadores creados: "
                                   f"{len(self.servidor.trabajadores)}/{MAX_TRABAJADORES}"))

    def _iniciar_cierre(self):
        if self.cerrando:
            return
        self.cerrando = True
        self.boton_enviar.configure(state="disabled")
        self.boton_rafaga.configure(state="disabled")
        self.pagina.configure(state="disabled")
        self.boton_cerrar.configure(text="Finalizando...", state="disabled")
        self.servidor.iniciar_cierre()
        # Esperar con join() en un hilo aparte, sin bloquear Tkinter.
        threading.Thread(target=self._esperar_y_guardar, daemon=True).start()

    def _esperar_y_guardar(self):
        total, reportes = self.servidor.esperar_cierre()
        informe = construir_informe(total, reportes)
        ruta = Path(__file__).resolve().parent / "informe_servidor.txt"
        error = None
        try:
            ruta.write_text(informe, encoding="utf-8")
        except OSError as exc:
            error = str(exc)
        # Enviar el resultado al hilo principal, nunca tocar Tkinter aquí.
        self.servidor.eventos.put(("cierre_completo", str(ruta), informe, error))

    def _mostrar_informe(self, ruta, informe, error):
        ventana = tk.Toplevel(self.raiz)
        ventana.title("Informe final de trabajadores")
        ventana.geometry("740x590")
        etiqueta = (f"Informe guardado en: {ruta}" if not error
                    else f"No se pudo guardar el informe: {error}")
        tk.Label(ventana, text=etiqueta, wraplength=700, justify="left",
                 padx=10, pady=12).pack(fill="x")
        area = tk.Text(ventana, wrap="none", font=("Consolas", 10))
        area.pack(fill="both", expand=True, padx=10, pady=7)
        area.insert("1.0", informe)
        area.configure(state="disabled")
        tk.Button(ventana, text="Cerrar informe", command=ventana.destroy).pack(pady=9)

    def _cerrar(self):
        if self.cierre_completo:
            self.raiz.destroy()
        else:
            # La X también hace un cierre ordenado, sin perder trabajos.
            self._iniciar_cierre()


if __name__ == "__main__":
    ventana = tk.Tk()
    Interfaz(ventana)
    ventana.mainloop()
