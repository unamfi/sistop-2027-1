from pathlib import Path
from fiunamfs import ErrorFiUnamFS, SistemaFiUnamFS


def main():
    ruta = Path(__file__).resolve().parent.parent / "fiunamfs.img"

    try:
        sistema = SistemaFiUnamFS(ruta)

        for archivo in sistema.listar_archivos():
            print(archivo.nombre, archivo.tamano, "bytes")

    except (ErrorFiUnamFS, OSError) as error:
        print("Error:", error)


if __name__ == "__main__":
    main()
