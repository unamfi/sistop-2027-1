from pathlib import Path
import sys

from fiunamfs import ErrorFiUnamFS, SistemaFiUnamFS
from interfaz import iniciar


def main():
    if len(sys.argv) > 1:
        ruta = Path(sys.argv[1]).resolve()
    else:
        ruta = Path(__file__).resolve().parent.parent / "fiunamfs.img"

    try:
        sistema = SistemaFiUnamFS(ruta)
        iniciar(sistema)

    except (ErrorFiUnamFS, OSError) as error:
        print("Error:", error)


if __name__ == "__main__":
    main()
