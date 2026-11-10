import os
import sys
import time

SEG_DIA = 24 * 60 * 60   # segundos en un dia 


def main():
    if len(sys.argv) != 3: # En esta linea nos aseguramos que sean solo los 3 argumentos que necesitamos
        print(f"Por favor ingrese solo lo siguiente Invocación: {sys.argv[0]} <directorio> <días>") #Si no se cumple muestra este mensaje y nos saca
        sys.exit(1)

    ruta = sys.argv[1] #Aqui se guarda el directorio o la ruta 
    try:
        num_dias = float(sys.argv[2]) #Conversion a numero de SEG_DIA
    except ValueError:
        print("Error: Por favor ingresa valores solo numericos.")
        sys.exit(1)

    if num_dias < 0:
        print("Error: Ingrese un numero positivo.")
        sys.exit(1)

    # Aqui es donde hacemos la "Resta" para ver hasta que dia se muestra en la ejecucion
    fecha_limite = time.time() - num_dias * SEG_DIA

    # Obtener la información de cada entrada del directorio
    try:
        nombres = sorted(os.listdir(ruta)) #Esta funcion devuelve en lista todo lo que hay en ese directorio o ruta hasta la fecha establecida y sorted la acomoda alfabeticamnete
    except (FileNotFoundError, NotADirectoryError, PermissionError) as e: # En caso de poder abrirla guarda la "advertencia " en variable e y la muestra 
        print(f"Error: no se puede abrir '{ruta}': {e.strerror}")
        sys.exit(1)

    print(f"{'Nombre':<30}{'Modificación':<17}{'Modo':<7}Tamaño")  #Encabezado 
    print("*" * 60)

    for nombre in nombres:
        try:
            info = os.lstat(os.path.join(ruta, nombre)) #la funcion os.path.join(ruta, nombre) une la carpeta y el nombre en una ruta completa. y os.lstat obtiene informacion de archivo
        except OSError:
            continue  # el archivo pudo desaparecer o no ser accesible

        if info.st_mtime < fecha_limite: # comparamos si los archivos entran en el ranfo de tiempo que ingresamos como limite 
            continue

        fecha = time.strftime("%Y-%m-%d %H:%M", time.localtime(info.st_mtime))
        modo = format(info.st_mode, "06o") 
        print(f"{nombre:<30}{fecha:<17}{modo:<7}{info.st_size}")


if __name__ == "__main__":
    main()