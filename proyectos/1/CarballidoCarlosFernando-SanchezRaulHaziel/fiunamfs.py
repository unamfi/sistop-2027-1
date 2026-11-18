
#!/usr/bin/env python3
"""Interfaz FiUnamFS con dos hilos y sincronizacion."""

import shutil
import sys
import tempfile
import threading
from pathlib import Path
from queue import Queue

from listar_directorio import leer_superbloque, leer_directorio
from extraer_archivo import extraer_archivo
from agregar_archivo import agregar_archivo
from eliminar_archivo import eliminar_archivo


class Tarea:
    def __init__(self, accion, imagen, argumentos=(), barrera=None):
        self.accion = accion
        self.imagen = imagen
        self.argumentos = argumentos
        self.barrera = barrera
        self.fin = threading.Event()
        self.resultado = None
        self.error = None


def listar_archivos(ruta):
    with ruta.open("rb") as imagen:
        etiqueta, tam_cluster, clusters_dir, clusters_total = (
            leer_superbloque(imagen, ruta.stat().st_size)
        )
        archivos, _ = leer_directorio(
            imagen, tam_cluster, clusters_dir, clusters_total
        )

    print(f"Volumen: {etiqueta}")
    print(f"{'Nombre':15} {'Bytes':>10} {'Cluster':>8}")
    print("-" * 36)

    for archivo in archivos:
        print(
            f"{archivo['nombre']:15} "
            f"{archivo['tamano']:>10} "
            f"{archivo['cluster']:>8}"
        )

    print(f"Total de archivos: {len(archivos)}")
    return [archivo["nombre"] for archivo in archivos]


def trabajador(cola, candado):
    """Procesa tareas y protege el acceso a FiUnamFS."""
    while True:
        tarea = cola.get()

        if tarea is None:
            cola.task_done()
            break

        try:
            # En la prueba, ambos hilos comienzan juntos.
            if tarea.barrera is not None:
                tarea.barrera.wait(timeout=10)

            # Solo un hilo puede usar la imagen a la vez.
            with candado:
                nombre = threading.current_thread().name
                print(f"\n[{nombre}] Ejecutando: {tarea.accion}")

                if tarea.accion == "listar":
                    tarea.resultado = listar_archivos(tarea.imagen)

                elif tarea.accion == "extraer":
                    extraer_archivo(
                        tarea.imagen, *tarea.argumentos
                    )

                elif tarea.accion == "agregar":
                    agregar_archivo(
                        tarea.imagen, *tarea.argumentos
                    )

                elif tarea.accion == "eliminar":
                    eliminar_archivo(
                        tarea.imagen, *tarea.argumentos
                    )

                else:
                    raise ValueError("Operacion desconocida.")

        except Exception as error:
            tarea.error = error

        finally:
            tarea.fin.set()
            cola.task_done()


def esperar(tarea):
    tarea.fin.wait()

    if tarea.error is not None:
        print(f"Error: {tarea.error}")
        return False

    return True


def prueba_concurrencia(ruta_imagen, cola):
    """Prueba dos hilos sobre una copia temporal."""
    with tempfile.TemporaryDirectory() as temporal:
        carpeta = Path(temporal)
        copia = carpeta / "copia.img"
        origen = carpeta / "HILOS.TXT"
        destino = carpeta / "recuperado.txt"

        shutil.copyfile(ruta_imagen, copia)

        contenido = b"Prueba de sincronizacion FiUnamFS\n" * 150
        origen.write_bytes(contenido)

        # Obliga a los dos trabajadores a iniciar juntos.
        barrera = threading.Barrier(2)

        lectura = Tarea("listar", copia, barrera=barrera)
        escritura = Tarea(
            "agregar", copia, (origen,), barrera=barrera
        )

        # Enviar ambas tareas antes de esperar.
        cola.put(lectura)
        cola.put(escritura)

        ok_lectura = esperar(lectura)
        ok_escritura = esperar(escritura)

        if not (ok_lectura and ok_escritura):
            print("No se completo la prueba de concurrencia.")
            return

        # Confirmar que los datos no se corrompieron.
        extraccion = Tarea(
            "extraer", copia, ("HILOS.TXT", destino)
        )
        cola.put(extraccion)

        if esperar(extraccion) and destino.read_bytes() == contenido:
            print("\nPRUEBA CORRECTA:")
            print("Dos hilos ejecutados con acceso sincronizado.")
            print("El archivo recuperado es identico al original.")
            print("La imagen de trabajo no fue modificada.")
        else:
            print("PRUEBA FALLIDA: los datos no coinciden.")


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 fiunamfs.py <imagen>")
        return 1

    ruta = Path(sys.argv[1]).expanduser().resolve()

    if not ruta.is_file():
        print("Error: no existe la imagen indicada.")
        return 1

    cola = Queue()
    candado = threading.RLock()

    hilo1 = threading.Thread(
        target=trabajador,
        args=(cola, candado),
        name="Hilo-1"
    )

    hilo2 = threading.Thread(
        target=trabajador,
        args=(cola, candado),
        name="Hilo-2"
    )

    hilo1.start()
    hilo2.start()

    try:
        while True:
            print("\n===== SISTEMA FiUnamFS =====")
            print("1. Listar archivos")
            print("2. Extraer archivo")
            print("3. Agregar archivo")
            print("4. Eliminar archivo")
            print("5. Probar concurrencia")
            print("0. Salir")

            opcion = input("Selecciona una opcion: ").strip()

            if opcion == "0":
                break

            elif opcion == "1":
                tarea = Tarea("listar", ruta)

            elif opcion == "2":
                nombre = input("Nombre en FiUnamFS: ").strip()
                destino = Path(
                    input("Ruta de destino: ").strip()
                ).expanduser()
                tarea = Tarea("extraer", ruta, (nombre, destino))

            elif opcion == "3":
                origen = Path(
                    input("Ruta del archivo origen: ").strip()
                ).expanduser()
                tarea = Tarea("agregar", ruta, (origen,))

            elif opcion == "4":
                nombre = input("Archivo a eliminar: ").strip()
                tarea = Tarea("eliminar", ruta, (nombre,))

            elif opcion == "5":
                prueba_concurrencia(ruta, cola)
                continue

            else:
                print("Opcion no valida.")
                continue

            cola.put(tarea)
            esperar(tarea)

    except (KeyboardInterrupt, EOFError):
        print("\nSaliendo del programa.")

    finally:
        cola.put(None)
        cola.put(None)
        hilo1.join()
        hilo2.join()
        print("Los dos hilos finalizaron correctamente.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
