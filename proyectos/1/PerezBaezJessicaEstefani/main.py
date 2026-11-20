
import os
import sys
from pathlib import Path

from filesystem import FiUnamFS
from directory import Directorio
from operations import Operaciones
from threads import AdministradorHilos


# Obtener la carpeta donde se encuentra este proyecto.
CARPETA_PROYECTO = Path(__file__).resolve().parent

# Imagen que se utiliza por defecto.
RUTA_DISCO_PREDETERMINADA = (
    CARPETA_PROYECTO / "disco" / "fiunamfs.img"
)


def obtener_ruta_disco():
    """Obtiene y comprueba la ruta de la imagen de FiUnamFS."""

    if len(sys.argv) > 2:
        print("Uso: py main.py [ruta_de_la_imagen]")
        return None

    if len(sys.argv) == 2:

        ruta = Path(sys.argv[1])

        if not ruta.is_absolute():
            ruta = CARPETA_PROYECTO / ruta

    else:
        ruta = RUTA_DISCO_PREDETERMINADA

    ruta = ruta.resolve()

    if not ruta.is_file():

        print("\nNo se encontro la imagen de FiUnamFS.")
        print("\nPara ejecutar el programa necesitas colocar")
        print("la imagen proporcionada para la practica.")
        print("\nPuedes guardarla dentro de la carpeta disco/")
        print("con el nombre: fiunamfs.img")

        print("\nTambien puedes indicar su ubicacion al ejecutar:")
        print('py main.py "disco/fiunamfs prueba.img"')

        print("\nRuta que se intento abrir:")
        print(ruta)

        return None

    return ruta


def mostrar_menu():
    """Muestra las opciones disponibles."""

    print("\n========== FIUNAMFS ==========")
    print("1. Mostrar contenido del directorio")
    print("2. Copiar archivo de FiUnamFS a la computadora")
    print("3. Copiar archivo de la computadora a FiUnamFS")
    print("4. Eliminar archivo de FiUnamFS")
    print("5. Salir")
    print("===============================")


def mostrar_directorio(directorio):
    """Muestra los archivos registrados en FiUnamFS."""

    print("\nCONSULTANDO DIRECTORIO DE FIUNAMFS...")

    try:

        archivos = directorio.listar()

        if not archivos:
            print("\nEl directorio esta vacio.")
            return

        print("\nCONTENIDO DEL DIRECTORIO")
        print("=" * 60)

        for archivo in archivos:

            print("Nombre:", archivo["nombre"])
            print("Tamano:", archivo["tamano"], "bytes")
            print("Cluster inicial:", archivo["cluster_inicial"])
            print("Fecha de creacion:", archivo["fecha_creacion"])
            print("Ultima modificacion:", archivo["fecha_modificacion"])
            print("-" * 60)

        print("Total de archivos:", len(archivos))

    except Exception as error:

        print("\nError al consultar el directorio:")
        print(type(error).__name__, ":", error)


def mostrar_mensajes_hilos(administrador):
    """Muestra los mensajes enviados por el hilo supervisor."""

    mensajes = administrador.obtener_mensajes()

    for mensaje in mensajes:
        print(f"\n[Supervisor] {mensaje}")


def main():
    """Ejecuta el programa principal de FiUnamFS."""

    ruta_disco = obtener_ruta_disco()

    if ruta_disco is None:
        return

    sistema = FiUnamFS(str(ruta_disco))
    administrador = None

    try:

        # Abrir y validar la imagen.
        sistema.abrir()

        directorio = Directorio(sistema)
        operaciones = Operaciones(sistema, directorio)

        # Iniciar los dos hilos.
        administrador = AdministradorHilos(operaciones)
        administrador.iniciar()

        while True:

            mostrar_menu()

            opcion = input(
                "Selecciona una opcion: "
            ).strip()

            # OPCION 1: MOSTRAR DIRECTORIO
            if opcion == "1":

                mostrar_directorio(directorio)

                input("\nPresiona Enter para volver al menu.")

            # OPCION 2: COPIAR DE FIUNAMFS A LA COMPUTADORA
            elif opcion == "2":

                print("\nCOPIAR DE FIUNAMFS A LA COMPUTADORA")

                nombre = input(
                    "Nombre del archivo que deseas copiar: "
                ).strip()

                if not nombre:
                    print("Debes escribir un nombre.")
                    continue

                try:

                    archivo = directorio.buscar(nombre)

                    if archivo is None:

                        print("El archivo no existe en FiUnamFS.")

                    else:

                        administrador.enviar_solicitud(
                            "copiar_desde",
                            nombre
                        )

                        mostrar_mensajes_hilos(administrador)

                        ruta_destino = (
                            CARPETA_PROYECTO
                            / "archivos"
                            / nombre
                        )

                        if ruta_destino.is_file():
                            print("\nCopia verificada correctamente.")
                            print("Ubicacion:", ruta_destino)

                except Exception as error:

                    mostrar_mensajes_hilos(administrador)

                    print("\nError durante la copia:")
                    print(type(error).__name__, ":", error)

                input("\nPresiona Enter para volver al menu.")

            # OPCION 3: COPIAR DE LA COMPUTADORA A FIUNAMFS
            elif opcion == "3":

                print("\nCOPIAR DE LA COMPUTADORA A FIUNAMFS")

                ruta = input(
                    "Ruta completa del archivo que deseas agregar: "
                ).strip().strip('"')

                if not ruta:
                    print("Debes escribir una ruta.")
                    continue

                try:

                    administrador.enviar_solicitud(
                        "copiar_hacia",
                        os.path.basename(ruta),
                        ruta
                    )

                    mostrar_mensajes_hilos(administrador)

                    print("\nComprobando el directorio...")
                    mostrar_directorio(directorio)

                except Exception as error:

                    mostrar_mensajes_hilos(administrador)

                    print("\nError al agregar el archivo:")
                    print(type(error).__name__, ":", error)

                input("\nPresiona Enter para volver al menu.")

            # OPCION 4: ELIMINAR ARCHIVO
            elif opcion == "4":

                print("\nELIMINAR ARCHIVO DE FIUNAMFS")

                nombre = input(
                    "Nombre del archivo que deseas eliminar: "
                ).strip()

                if not nombre:
                    print("Debes escribir un nombre.")
                    continue

                try:

                    administrador.enviar_solicitud(
                        "eliminar",
                        nombre
                    )

                    mostrar_mensajes_hilos(administrador)

                    print("\nDirectorio actualizado:")
                    mostrar_directorio(directorio)

                except Exception as error:

                    mostrar_mensajes_hilos(administrador)

                    print("\nError al eliminar el archivo:")
                    print(type(error).__name__, ":", error)

                input("\nPresiona Enter para volver al menu.")

            # OPCION 5: SALIR
            elif opcion == "5":

                print("\nCerrando FiUnamFS...")
                break

            else:

                print("\nOpcion no valida. Selecciona del 1 al 5.")
                input("Presiona Enter para continuar.")

    except KeyboardInterrupt:

        print("\nPrograma interrumpido por el usuario.")

    except Exception as error:

        print("\nError en el sistema:")
        print(type(error).__name__, ":", error)

    finally:

        if administrador is not None:
            administrador.finalizar()

        sistema.cerrar()


if __name__ == "__main__":
    main()
