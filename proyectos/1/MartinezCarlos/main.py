#!/usr/bin/env python3
import sys
import os
import threading
import queue
from fiunamfs import SistemaArchivosFiUnamFS, ErrorFiUnamFS

class ControladorConcurrenteFS:
    """Gestiona operaciones sobre FiUnamFS en un hilo trabajador sincronizado."""
    def __init__(self, fs):
        self.fs = fs
        self.cola_tareas = queue.Queue()
        self.mutex_disco = threading.Lock()
        self.semaforo_tareas = threading.Semaphore(0)
        self.activo = True
        self.hilo_trabajador = threading.Thread(target=self._ciclo_trabajador, daemon=True)
        self.hilo_trabajador.start()

    def _ciclo_trabajador(self):
        while self.activo:
            self.semaforo_tareas.acquire()
            if not self.activo:
                break

            tarea = self.cola_tareas.get()
            accion, args, contenedor_respuesta, evento_listo = tarea

            with self.mutex_disco:
                try:
                    if accion == "LISTAR":
                        contenedor_respuesta["datos"] = self.fs.listar_contenido()
                    elif accion == "COPIAR_A_HOST":
                        self.fs.copiar_a_host(*args)
                        contenedor_respuesta["mensaje"] = f"Archivo '{args[0]}' copiado exitosamente a '{args[1]}'."
                    elif accion == "COPIAR_A_FS":
                        self.fs.copiar_desde_host(*args)
                        contenedor_respuesta["mensaje"] = f"Archivo '{args[0]}' importado exitosamente a FiUnamFS."
                    elif accion == "ELIMINAR":
                        self.fs.eliminar_archivo(*args)
                        contenedor_respuesta["mensaje"] = f"Archivo '{args[0]}' eliminado de FiUnamFS."
                    contenedor_respuesta["exito"] = True
                except Exception as e:
                    contenedor_respuesta["exito"] = False
                    contenedor_respuesta["error"] = str(e)
                finally:
                    self.cola_tareas.task_done()
                    evento_listo.set()

    def ejecutar_operacion(self, accion, *args):
        """Encola una tarea desde la interfaz y espera sincronizadamente su resultado."""
        respuesta = {}
        evento_listo = threading.Event()
        self.cola_tareas.put((accion, args, respuesta, evento_listo))
        self.semaforo_tareas.release()
        evento_listo.wait()
        return respuesta

    def detener(self):
        self.activo = False
        self.semaforo_tareas.release()
        self.hilo_trabajador.join(timeout=1.0)


def formatear_fecha(cadena_fecha):
    if len(cadena_fecha) == 14 and cadena_fecha.isdigit():
        return f"{cadena_fecha[0:4]}-{cadena_fecha[4:6]}-{cadena_fecha[6:8]} {cadena_fecha[8:10]}:{cadena_fecha[10:12]}:{cadena_fecha[12:14]}"
    return cadena_fecha


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 main.py <ruta_imagen_fiunamfs.img>")
        sys.exit(1)

    ruta_img = sys.argv[1]

    try:
        fs = SistemaArchivosFiUnamFS(ruta_img)
    except ErrorFiUnamFS as e:
        print(f"\n[ERROR CRÍTICO] {e}")
        sys.exit(1)

    controlador = ControladorConcurrenteFS(fs)

    print("=================================================================")
    print(f"  SISTEMA DE ARCHIVOS FiUnamFS v27-1 | Etiqueta: {fs.etiqueta}")
    print(f"  Cluster: {fs.tamano_cluster} bytes | Total: {fs.clusters_totales} clusters")
    print("=================================================================")

    while True:
        print("\n--- MENÚ DE OPERACIONES ---")
        print("1. Listar contenido del directorio")
        print("2. Copiar archivo de FiUnamFS hacia tu computadora")
        print("3. Copiar archivo de tu computadora hacia FiUnamFS")
        print("4. Eliminar archivo de FiUnamFS")
        print("5. Salir")

        opcion = input("\nSelecciona una opción (1-5): ").strip()

        if opcion == "1":
            res = controlador.ejecutar_operacion("LISTAR")
            if res["exito"]:
                archivos = res["datos"]
                print(f"\n{'Nombre':<16} {'Tamaño (B)':<12} {'Cluster Ini':<12} {'Creación':<20} {'Modificación'}")
                print("-" * 82)
                if not archivos:
                    print("(El directorio se encuentra vacío)")
                for a in archivos:
                    print(f"{a['nombre']:<16} {a['tamano']:<12} {a['cluster_inicial']:<12} {formatear_fecha(a['creacion']):<20} {formatear_fecha(a['modificacion'])}")
            else:
                print(f"[ERROR] {res['error']}")

        elif opcion == "2":
            nombre_fs = input("Nombre del archivo en FiUnamFS a extraer: ").strip()
            destino = input("Ruta/nombre destino en tu computadora (Enter para usar el mismo nombre): ").strip()
            if not destino:
                destino = nombre_fs
            res = controlador.ejecutar_operacion("COPIAR_A_HOST", nombre_fs, destino)
            print(f"\n[{'OK' if res['exito'] else 'ERROR'}] {res.get('mensaje') or res.get('error')}")

        elif opcion == "3":
            origen = input("Ruta del archivo en tu computadora a importar: ").strip()
            nombre_fs = input("Nombre destino en FiUnamFS (máx. 15 caracteres ASCII, Enter para conservar): ").strip()
            res = controlador.ejecutar_operacion("COPIAR_A_FS", origen, nombre_fs if nombre_fs else None)
            print(f"\n[{'OK' if res['exito'] else 'ERROR'}] {res.get('mensaje') or res.get('error')}")

        elif opcion == "4":
            nombre_fs = input("Nombre del archivo en FiUnamFS a eliminar: ").strip()
            confirmar = input(f"¿Seguro que deseas eliminar '{nombre_fs}'? (s/n): ").strip().lower()
            if confirmar == "s":
                res = controlador.ejecutar_operacion("ELIMINAR", nombre_fs)
                print(f"\n[{'OK' if res['exito'] else 'ERROR'}] {res.get('mensaje') or res.get('error')}")

        elif opcion == "5":
            print("\nCerrando hilos y desmontando FiUnamFS...")
            controlador.detener()
            break
        else:
            print("\n[AVISO] Opción no válida. Elige un número del 1 al 5.")

if __name__ == "__main__":
    main()
