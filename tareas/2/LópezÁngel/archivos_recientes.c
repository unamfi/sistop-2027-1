#define _POSIX_C_SOURCE 200809L
#define _FILE_OFFSET_BITS 64

#include <dirent.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

/* scandir usa esta funcion para ordenar los nombres. */
static int comparar(const struct dirent **a, const struct dirent **b)
{
    return strcmp((*a)->d_name, (*b)->d_name);
}

int main(int argc, char *argv[])
{
    if (argc != 3) {
        fprintf(stderr, "Uso: %s <directorio> <dias>\n", argv[0]);
        return 1;
    }

    char *fin;
    errno = 0;
    long dias = strtol(argv[2], &fin, 10);
    if (errno == ERANGE || fin == argv[2] || *fin != '\0' || dias < 0) {
        fprintf(stderr, "Los dias deben ser un entero no negativo.\n");
        return 1;
    }
    // Obtiene la hora actual 
    time_t ahora = time(NULL);
    if (ahora == (time_t)-1) {
        fprintf(stderr, "No se pudo obtener la hora actual.\n");
        return 1;
    }
    /* Obtiene una lista de entradas ya ordenada. */
    struct dirent **entradas;
    int cantidad = scandir(argv[1], &entradas, NULL, comparar);
    if (cantidad == -1) {
        perror(argv[1]);
        return 1;
    }
    // Imprime la cabecera de la tabla
    int resultado = 0;
    printf("%-30s %-19s %-7s %s\n", "Nombre", "Modificacion", "Modo", "Tamano (bytes)");
    puts("============================================================================");

    for (int i = 0; i < cantidad; i++) {
        char *nombre = entradas[i]->d_name;
        if (strcmp(nombre, ".") != 0 && strcmp(nombre, "..") != 0) {
            char ruta[PATH_MAX];
            struct stat datos;
            int longitud = snprintf(ruta, sizeof(ruta), "%s/%s", argv[1], nombre);

            if (longitud < 0 || (size_t)longitud >= sizeof(ruta)) {
                fprintf(stderr, "Ruta demasiado larga: %s\n", nombre);
                resultado = 1;
            } else if (stat(ruta, &datos) == -1) {
                perror(ruta);
                resultado = 1;
            } else if (difftime(ahora, datos.st_mtime) <= (double)dias * 86400) {
                char fecha[32] = "Fecha no disponible";
                struct tm *local = localtime(&datos.st_mtime);
                // Formatea la fecha de modificación
                if (local != NULL)
                    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", local);
                printf("%-30s %-19s %06jo  %jd\n", nombre, fecha,
                       (uintmax_t)datos.st_mode, (intmax_t)datos.st_size);
            }
        }
        free(entradas[i]);
    }
    free(entradas);
    return resultado;
}
