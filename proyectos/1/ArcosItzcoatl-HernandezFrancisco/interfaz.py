
"""Interfaz gráfica de FiUnamFS con dos hilos trabajadores."""

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from fiunamfs import ErrorFiUnamFS, FiUnamFS


class InterfazFiUnamFS:
    def __init__(self, ventana):
        self.ventana = ventana
        self.ventana.title("Administrador FiUnamFS 27-1")
        self.ventana.geometry("950x520")

        self.ruta_imagen = tk.StringVar(value="")
        self.estado = tk.StringVar(
            value="Selecciona una imagen FiUnamFS."
        )

        # Comunicación y sincronización de los trabajadores.
        self.solicitudes = queue.Queue()
        self.resultados = queue.Queue()
        self.bloqueo = threading.Lock()
        self.condicion = threading.Condition()

        self.numero_solicitud = 0
        self.siguiente_turno = 0
        self.ultimo_resultado = -1
        self.pendientes = 0

        self.crear_componentes()

        # Crear dos hilos trabajadores.
        self.trabajadores = []

        for numero in range(1, 3):
            hilo = threading.Thread(
                target=self.trabajador,
                name=f"Trabajador-{numero}",
                daemon=True
            )
            hilo.start()
            self.trabajadores.append(hilo)

        self.ventana.after(100, self.revisar_resultados)
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar)

    def crear_componentes(self):
        contenedor = ttk.Frame(self.ventana, padding=15)
        contenedor.pack(fill="both", expand=True)

        ttk.Label(
            contenedor,
            text="Administrador de archivos FiUnamFS",
            font=("Arial", 16, "bold")
        ).pack(anchor="w", pady=(0, 15))

        # Selección de la imagen.
        fila_imagen = ttk.Frame(contenedor)
        fila_imagen.pack(fill="x", pady=(0, 10))

        ttk.Label(
            fila_imagen, text="Imagen:"
        ).pack(side="left", padx=(0, 8))

        ttk.Entry(
            fila_imagen,
            textvariable=self.ruta_imagen,
            state="readonly"
        ).pack(side="left", fill="x", expand=True)

        self.boton_seleccionar = ttk.Button(
            fila_imagen,
            text="Seleccionar",
            command=self.seleccionar_imagen
        )
        self.boton_seleccionar.pack(side="left", padx=(8, 0))
        # Operaciones disponibles.
        acciones = ttk.Frame(contenedor)
        acciones.pack(fill="x", pady=(0, 12))

        ttk.Button(
            acciones,
            text="Consultar directorio",
            command=lambda: self.enviar("listar")
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            acciones,
            text="Importar",
            command=self.importar
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            acciones,
            text="Exportar",
            command=self.exportar
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            acciones,
            text="Eliminar",
            command=self.eliminar
        ).pack(side="left")

        # Tabla del directorio.
        columnas = (
            "nombre", "tamanio", "cluster",
            "creacion", "modificacion"
        )

        self.tabla = ttk.Treeview(
            contenedor,
            columns=columnas,
            show="headings",
            height=12
        )

        titulos = {
            "nombre": "Nombre",
            "tamanio": "Bytes",
            "cluster": "Cluster",
            "creacion": "Creación",
            "modificacion": "Modificación"
        }

        for columna, titulo in titulos.items():
            self.tabla.heading(columna, text=titulo)
            self.tabla.column(
                columna, width=150, anchor="center"
            )

        self.tabla.column(
            "nombre", width=180, anchor="w"
        )
        self.tabla.column("tamanio", width=90)
        self.tabla.column("cluster", width=80)

        self.tabla.pack(fill="both", expand=True)

        ttk.Label(
            contenedor,
            text=(
                "Importar y eliminar modifican la imagen "
                "seleccionada; utiliza una copia para las pruebas."
            )
        ).pack(anchor="w", pady=(10, 0))

        ttk.Label(
            contenedor,
            textvariable=self.estado
        ).pack(anchor="w", pady=(6, 0))

    def seleccionar_imagen(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen FiUnamFS",
            filetypes=[
                ("Imágenes de disco", "*.img"),
                ("Todos los archivos", "*.*")
            ]
        )

        if ruta:
            self.ruta_imagen.set(ruta)

            for fila in self.tabla.get_children():
                self.tabla.delete(fila)

            self.enviar("listar")

    def archivo_seleccionado(self):
        seleccion = self.tabla.selection()

        if not seleccion:
            messagebox.showwarning(
                "FiUnamFS",
                "Selecciona un archivo de la tabla."
            )
            return None

        return self.tabla.item(
            seleccion[0], "values"
        )[0]

    def importar(self):
        if not self.ruta_imagen.get():
            messagebox.showwarning(
                "FiUnamFS",
                "Primero selecciona una imagen."
            )
            return

        origen = filedialog.askopenfilename(
            title="Archivo que se importará"
        )

        if origen:
            self.enviar("importar", origen)

    def exportar(self):
        if not self.ruta_imagen.get():
            messagebox.showwarning(
                "FiUnamFS",
                "Primero selecciona una imagen."
            )
            return

        nombre = self.archivo_seleccionado()

        if nombre is None:
            return

        destino = filedialog.asksaveasfilename(
            title="Guardar archivo exportado",
            initialfile=nombre
        )

        if destino:
            self.enviar(
                "exportar", (nombre, destino)
            )

    def eliminar(self):
        if not self.ruta_imagen.get():
            messagebox.showwarning(
                "FiUnamFS",
                "Primero selecciona una imagen."
            )
            return

        nombre = self.archivo_seleccionado()

        if nombre is None:
            return

        confirmar = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar {nombre} de la imagen seleccionada?\n"
            "Esta operación modifica el archivo de imagen."
        )

        if confirmar:
            self.enviar("eliminar", nombre)

    def enviar(self, operacion, dato=None):
        ruta = self.ruta_imagen.get()

        if not ruta:
            messagebox.showwarning(
                "FiUnamFS",
                "Selecciona una imagen FiUnamFS."
            )
            return

        numero = self.numero_solicitud
        self.numero_solicitud += 1

        self.pendientes += 1
        self.boton_seleccionar.configure(state="disabled")

        self.solicitudes.put(
            (numero, operacion, ruta, dato)
            )

        self.estado.set(
            f"Solicitud enviada: {operacion}..."
        )

    def trabajador(self):
        while True:
            solicitud = self.solicitudes.get()

            if solicitud is None:
                self.solicitudes.task_done()
                return

            numero, operacion, ruta, dato = solicitud
            hilo = threading.current_thread().name

            # Respetar el orden de las solicitudes.
            with self.condicion:
                while numero != self.siguiente_turno:
                    self.condicion.wait()

            try:
                # Proteger el acceso a la imagen FiUnamFS.
                with self.bloqueo:
                    disco = FiUnamFS(ruta)
                    superbloque = disco.leer_superbloque()

                    mensaje = "Directorio consultado"

                    if operacion == "importar":
                        archivo = disco.importar_archivo(dato)
                        mensaje = (
                            f"Importado: {archivo.nombre}"
                        )

                    elif operacion == "exportar":
                        nombre, destino = dato

                        disco.exportar_archivo(
                            nombre, destino
                        )

                        mensaje = f"Exportado: {nombre}"

                    elif operacion == "eliminar":
                        archivo = disco.eliminar_archivo(
                            dato
                        )

                        mensaje = (
                            f"Eliminado: {archivo.nombre}"
                        )

                    # Actualizar el directorio tras la operación.
                    archivos = disco.listar_archivos()

                    filas = [
                        (
                            archivo.nombre,
                            archivo.tamanio,
                            archivo.cluster_inicial,
                            archivo.creacion,
                            archivo.modificacion
                        )
                        for archivo in archivos
                    ]

                self.resultados.put(
                    (
                        numero,
                        ruta,
                        hilo,
                        None,
                        superbloque.etiqueta,
                        filas,
                        mensaje
                    )
                )

            except (
                OSError, ErrorFiUnamFS, ValueError
            ) as error:
                self.resultados.put(
                    (
                        numero,
                        ruta,
                        hilo,
                        str(error),
                        None,
                        None,
                        None
                    )
                )

            finally:
                with self.condicion:
                    self.siguiente_turno += 1
                    self.condicion.notify_all()

                self.solicitudes.task_done()

    def revisar_resultados(self):
        while True:
            try:
                (
                    numero, ruta, hilo, error,
                    etiqueta, filas, mensaje
                ) = self.resultados.get_nowait()

            except queue.Empty:
                break
            self.pendientes -= 1
            if self.pendientes == 0:
                 self.boton_seleccionar.configure(state="normal")
            # Evitar mostrar resultados de otra imagen.

            # Evitar mostrar resultados de otra imagen.
            if (
                ruta != self.ruta_imagen.get()
                or numero < self.ultimo_resultado
            ):
                continue

            self.ultimo_resultado = numero

            if error is not None:
                self.estado.set(f"{hilo}: error")
                messagebox.showerror(
                    "FiUnamFS", error
                )
                continue

            for fila in self.tabla.get_children():
                self.tabla.delete(fila)

            for fila in filas:
                self.tabla.insert(
                    "", "end", values=fila
                )

            self.estado.set(
                f"{mensaje} | Volumen: {etiqueta} | "
                f"Archivos: {len(filas)} | "
                f"Atendido por: {hilo}"
            )

        self.ventana.after(
            100, self.revisar_resultados
        )

    def cerrar(self):
        if self.pendientes:
            messagebox.showwarning(
                "Operaciones pendientes",
                "Hay solicitudes en ejecución."
            )
            return

        for _ in self.trabajadores:
            self.solicitudes.put(None)

        self.ventana.destroy()


if __name__ == "__main__":
    ventana = tk.Tk()
    InterfazFiUnamFS(ventana)
    ventana.mainloop()
