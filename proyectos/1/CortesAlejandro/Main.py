import os
import sys

from fiunamfs import ErrorFiUnamFS, FiUnamFS
from trabajador import Tarea, Trabajador

IMAGEN_POR_DEFECTO = "fiunamfs.img"

# --------------------------------------------------------------------------
# Funciones para mejorar la presentación
# --------------------------------------------------------------------------
def formatear_fecha(texto):
    if len(texto) == 14 and texto.isdigit():
        return (f"{texto[0:4]}-{texto[4:6]}-{texto[6:8]} "
                f"{texto[8:10]}:{texto[10:12]}:{texto[12:14]}")
    return "-"

def formatear_tamano(n):

    if n < 1024:
        return f"{n} B"
    return f"{n / 1024:.1f} KiB"

def preguntar(texto, defecto=None):
    respuesta = input(texto).strip()
    return respuesta if respuesta else defecto


def confirmar(texto):
    return (preguntar(f"{texto} [s/N]: ", "n") or "n").lower() in ("s", "si", "sí", "y")

def ejecutar(trabajador, descripcion, funcion):
    """
    Envía una operación al hilo trabajador y espera a que termine
    Devuelve el resultado; si falló, lanza la excepción del trabajador
    """
    tarea = trabajador.enviar(Tarea(descripcion, funcion))
    return tarea.esperar()


# --------------------------------------------------------------------------
# Acciones del menú
# --------------------------------------------------------------------------
def listar(fs, trabajador):
    """Muestra el directorio y devuelve la lista de entradas"""
    archivos = ejecutar(trabajador, "Listar", lambda: fs.listar())
    print()
    if not archivos:
        print("  (El directorio está vacío)")
    else:
        print(f"  {'#':>3}  {'Nombre':<15}  {'Tamaño':>10}  "
              f"{'Creado':<19}  {'Modificado':<19}")
        print("  " + "-" * 74)
        for i, e in enumerate(archivos, start=1):
            print(f"  {i:>3}  {e.nombre:<15}  {formatear_tamano(e.tamano):>10}  "
                  f"{formatear_fecha(e.creacion):<19}  {formatear_fecha(e.modificacion):<19}")
    libre = ejecutar(trabajador, "Espacio", lambda: fs.espacio_libre())
    print(f"\n  Espacio libre: {formatear_tamano(libre)}")
    return archivos


def elegir_archivo(archivos, accion):
    """Deja elegir un archivo por número o por nombre. None si se cancela"""
    if not archivos:
        return None
    eleccion = preguntar(f"\nArchivo a {accion} (número o nombre, Enter cancela): ")
    if not eleccion:
        return None
    if eleccion.isdigit() and 1 <= int(eleccion) <= len(archivos):
        return archivos[int(eleccion) - 1].nombre
    if any(e.nombre == eleccion for e in archivos):
        return eleccion
    print(f"  '{eleccion}' no corresponde a ningún archivo de la lista")
    return None


def copiar_a_mi_sistema(fs, trabajador):
    archivos = listar(fs, trabajador)
    nombre = elegir_archivo(archivos, "copiar a tu computadora")
    if nombre is None:
        return
    destino = preguntar("Carpeta o ruta de destino (Enter = carpeta actual): ", ".")
    destino = os.path.expanduser(destino)
    if os.path.isdir(destino):
        destino = os.path.join(destino, nombre)
    if os.path.exists(destino) and not confirmar(f"'{destino}' ya existe. ¿Sobrescribir?"):
        print("  Operación cancelada.")
        return
    tamano = ejecutar(trabajador, f"Extraer {nombre}",
                      lambda: fs.extraer(nombre, destino))
    print(f"  Listo: '{nombre}' ({formatear_tamano(tamano)}) copiado a '{destino}'.")


def copiar_a_fiunamfs(fs, trabajador):
    origen = preguntar("Ruta del archivo de tu computadora (Enter cancela): ")
    if not origen:
        return
    origen = os.path.expanduser(origen)
    if not os.path.isfile(origen):
        print(f"  '{origen}' no existe o no es un archivo")
        return
    nombre, tamano = ejecutar(trabajador, f"Importar {origen}",
                              lambda: fs.importar(origen))
    print(f"  Listo: '{nombre}' ({formatear_tamano(tamano)}) copiado a FiUnamFS")


def eliminar(fs, trabajador):
    archivos = listar(fs, trabajador)
    nombre = elegir_archivo(archivos, "eliminar")
    if nombre is None:
        return
    if not confirmar(f"¿Seguro que quieres eliminar '{nombre}' de FiUnamFS?"):
        print("  Operación cancelada.")
        return
    ejecutar(trabajador, f"Eliminar {nombre}", lambda: fs.eliminar(nombre))
    print(f"  Listo: '{nombre}' eliminado")


MENU = """
==================== FiUnamFS ====================
  1) Listar los archivos del directorio
  2) Copiar un archivo de FiUnamFS a mi computadora
  3) Copiar un archivo de mi computadora a FiUnamFS
  4) Eliminar un archivo de FiUnamFS
  5) Salir
==================================================="""

ACCIONES = {
    "1": lambda fs, t: listar(fs, t),
    "2": copiar_a_mi_sistema,
    "3": copiar_a_fiunamfs,
    "4": eliminar,
}


def bucle_principal(fs, trabajador):
    while True:
        print(MENU)
        opcion = preguntar("Elige una opción (1-5): ", "")
        if opcion == "5":
            return
        accion = ACCIONES.get(opcion)
        if accion is None:
            print("  Opción no válida; escribe un número del 1 al 5")
            continue
        try:
            accion(fs, trabajador)
        except ErrorFiUnamFS as e:
            print(f"  Error: {e}")


def main():
    if len(sys.argv) > 2:
        print("Escribe: python3 main.py imagen.img")
        return 1

    if len(sys.argv) == 2:
        ruta = sys.argv[1]
    else:
        print("Bienvenido a FiUnamFS")
        ruta = preguntar(f"Ruta de la imagen del sistema de archivos "
                         f"(Enter = {IMAGEN_POR_DEFECTO}): ", IMAGEN_POR_DEFECTO)
    ruta = os.path.expanduser(ruta)

    try:
        fs = FiUnamFS(ruta)          # valida nombre, versión y tamaño
    except ErrorFiUnamFS as e:
        print(f"Error: {e}")
        return 1

    print(f"\nVolumen '{fs.etiqueta}' abierto ({fs.clusters_totales} clusters de "
          f"{fs.tam_cluster} bytes).")

    trabajador = Trabajador()
    trabajador.start()
    try:
        bucle_principal(fs, trabajador)
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        trabajador.detener()
        fs.cerrar()
    print("Hasta pronto")
    return 0

if __name__ == "__main__":
    sys.exit(main())