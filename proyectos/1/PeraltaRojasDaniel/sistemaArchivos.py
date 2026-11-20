import queue
import sys
import threading
from fiunamfs import FiUnamFS


def hilo_trabajador(fs: FiUnamFS, cola_tareas: queue.Queue) -> None:
    """Hilo consumidorque ejecuta las operaciones de I/O sobre el sistema de archivos"""
    while True:
        tarea = cola_tareas.get()
        if tarea is None:  # Señal de terminación limpia
            cola_tareas.task_done()
            break

        accion, args, evento_listo, resultado = tarea
        try:
            if accion == "listar":
                resultado["data"] = fs.listar_entradas()
            elif accion == "extraer":
                fs.copiar_desde_fs(*args)
                resultado["data"] = f"Archivo '{args[0]}' copiado a '{args[1]}'"
            elif accion == "insertar":
                fs.copiar_hacia_fs(*args)
                resultado["data"] = f"Archivo '{args[0]}' guardado como '{args[1]}'"
            elif accion == "eliminar":
                fs.eliminar(*args)
                resultado["data"] = f"Archivo '{args[0]}' eliminado"
        except Exception as e:
            resultado["error"] = str(e)
        finally:
            evento_listo.set()
            cola_tareas.task_done()


def enviar_tarea(cola_tareas: queue.Queue, accion: str, *args):
    """Encola una operacion desde el hilo de UI y espera la señal del hilo trabajador"""
    evento_listo = threading.Event()
    resultado = {}
    cola_tareas.put((accion, args, evento_listo, resultado))
    evento_listo.wait()

    if "error" in resultado:
        raise RuntimeError(resultado["error"])
    return resultado.get("data")


def mostrar_menu() -> None:
    print("\n--- Operaciones FiUnamFS ---")
    print("1. Listar contenido del directorio")
    print("2. Copiar archivo desde FiUnamFS hacia mi computadora")
    print("3. Copiar archivo desde mi computadora hacia FiUnamFS")
    print("4. Eliminar archivo de FiUnamFS")
    print("5. Salir")

def mostrar_banner(fs: FiUnamFS) -> None:
    banner = rf"""
░▄▄▄▄░      ==================================================
▀▀▄██►       FiUnamFS - Gestor de Sistema de Archivos
▀▀███►       Volumen: '{fs.etiqueta}'
░▀███►░█►    Capacidad: {fs.total_clusters} clusters de {fs.tamano_cluster} bytes
▒▄████▀▀    ==================================================
"""
    print(banner)

def main() -> None:
    # Checa que los caracteres del baner no fallen en widnows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ruta_img = sys.argv[1] if len(sys.argv) > 1 else "fiunamfs.img"
    fs = FiUnamFS(ruta_img)

    mostrar_banner(fs)

    cola_tareas = queue.Queue()
    worker = threading.Thread(target=hilo_trabajador, args=(fs, cola_tareas), daemon=True)
    worker.start()

    try:
        while True:
            mostrar_menu()
            opcion = input("Selecciona una opción (1-5): ").strip()

            try:
                if opcion == "1":
                    archivos = enviar_tarea(cola_tareas, "listar")
                    if not archivos:
                        print("El directorio está vacio")
                    else:
                        print(f"\n{'NOMBRE':<16} {'TAMAÑO (B)':<12} {'CLUSTER':<8} {'CREACIÓN':<20} {'MODIFICACIÓN'}")
                        print("-" * 82)
                        for a in archivos:
                            print(
                                f"{a['nombre']:<16} {a['tamano']:<12} {a['cluster_ini']:<8} "
                                f"{a['creacion']:<20} {a['modificacion']}"
                            )

                elif opcion == "2":
                    nombre_fs = input("Nombre del archivo en FiUnamFS: ").strip()
                    ruta_dest = input("Ruta destino en mi computadora: ").strip()
                    msg = enviar_tarea(cola_tareas, "extraer", nombre_fs, ruta_dest)
                    print(msg)

                elif opcion == "3":
                    ruta_orig = input("Ruta del archivo a copiar: ").strip()
                    nombre_dest = input("Nombre destino en FiUnamFS (max 15 caracteres ASCII): ").strip()
                    msg = enviar_tarea(cola_tareas, "insertar", ruta_orig, nombre_dest)
                    print(msg)

                elif opcion == "4":
                    nombre_fs = input("Nombre del archivo a eliminar en FiUnamFS: ").strip()
                    msg = enviar_tarea(cola_tareas, "eliminar", nombre_fs)
                    print(msg)

                elif opcion == "5":
                    print("Cerrando sistema de archivos...")
                    break

                else:
                    print("Ocion invalida. Elige un numero del 1 al 5")

            except RuntimeError as err:
                print(f"Error en la operacion: {err}")

    finally:
        cola_tareas.put(None)
        worker.join()


if __name__ == "__main__":
    main()