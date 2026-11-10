
#!/usr/bin/env python3
"""Muestra archivos recientes de un directorio y sus atributos."""

import os
import sys
import time
from datetime import datetime


def mostrar_uso():
    """Muestra la forma correcta de ejecutar el programa."""
    programa = os.path.basename(sys.argv[0])
    print(
        f"Uso: python3 {programa} <directorio> <dias>",
        file=sys.stderr
    )
    print(
        f"Ejemplo: python3 {programa} /tmp 3",
        file=sys.stderr
    )


def es_reciente(fecha_modificacion, dias, ahora):
    """Comprueba si una entrada corresponde al periodo solicitado."""

    # No consideramos archivos con fechas futuras.
    if fecha_modificacion > ahora:
        return False

    if dias == 0:
        # Para cero dias se consideran los archivos modificados hoy.
        inicio_hoy = datetime.fromtimestamp(ahora).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        ).timestamp()

        return fecha_modificacion >= inicio_hoy

    # Para otros valores usamos periodos de 24 horas.
    limite = ahora - dias * 24 * 60 * 60
    return fecha_modificacion >= limite


def obtener_entradas(directorio, dias):
    """Consulta las entradas del directorio y las ordena por nombre."""

    ahora = time.time()
    resultados = []
    hubo_errores = False

    # Se revisa solamente el contenido directo del directorio.
    with os.scandir(directorio) as elementos:
        for elemento in elementos:
            try:
                # Consulta los atributos sin seguir enlaces simbolicos.
                datos = elemento.stat(follow_symlinks=False)

            except OSError as error:
                print(
                    f"Aviso: no se pudo consultar '{elemento.name}': {error}",
                    file=sys.stderr
                )
                hubo_errores = True
                continue

            # Guardamos solamente las entradas del periodo solicitado.
            if es_reciente(datos.st_mtime, dias, ahora):
                resultados.append((elemento.name, datos))

    # Ordenamiento lexicografico por nombre.
    resultados.sort(key=lambda entrada: entrada[0])

    return resultados, hubo_errores


def imprimir_tabla(entradas):
    """Muestra los resultados en una tabla con columnas alineadas."""

    ancho_nombre = max(
        [len("Nombre")] + [len(nombre) for nombre, _ in entradas]
    )

    encabezado = (
        f"{'Nombre':<{ancho_nombre}}  "
        f"{'Modificacion':<16}  "
        f"{'Modo':>6}  "
        f"{'Tamano':>10}"
    )

    print(encabezado)
    print("=" * len(encabezado))

    for nombre, datos in entradas:
        fecha = datetime.fromtimestamp(
            datos.st_mtime
        ).strftime("%Y-%m-%d %H:%M")

        # Formato octal Unix: tipo de archivo y permisos.
        modo = f"{datos.st_mode:06o}"

        print(
            f"{nombre:<{ancho_nombre}}  "
            f"{fecha:<16}  "
            f"{modo:>6}  "
            f"{datos.st_size:>10}"
        )

    if not entradas:
        print("No hay entradas modificadas en el periodo indicado.")


def main():
    """Valida los argumentos y ejecuta la consulta."""

    if len(sys.argv) != 3:
        mostrar_uso()
        return 2

    directorio = sys.argv[1]

    # El numero de dias debe ser un entero no negativo.
    try:
        dias = int(sys.argv[2])
    except ValueError:
        print(
            "Error: los dias deben ser un numero entero no negativo.",
            file=sys.stderr
        )
        mostrar_uso()
        return 2

    if dias < 0:
        print(
            "Error: el numero de dias no puede ser negativo.",
            file=sys.stderr
        )
        return 2

    if not os.path.isdir(directorio):
        print(
            f"Error: '{directorio}' no existe o no es un directorio.",
            file=sys.stderr
        )
        return 1

    try:
        entradas, hubo_errores = obtener_entradas(directorio, dias)
    except OSError as error:
        print(
            f"Error: no se pudo leer el directorio '{directorio}': {error}",
            file=sys.stderr
        )
        return 1

    imprimir_tabla(entradas)

    return 1 if hubo_errores else 0


if __name__ == "__main__":
    sys.exit(main())
