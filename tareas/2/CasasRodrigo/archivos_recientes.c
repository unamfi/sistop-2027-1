
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <dirent.h>
#include <sys/stat.h>
#include <time.h>

// Compara dos nombres para ordenarlos alfabeticamente.
int comparar(const void *a, const void *b)
{
    const char *nombre1 = *(const char *const *)a;
    const char *nombre2 = *(const char *const *)b;

    return strcmp(nombre1, nombre2);
}

int main(int argc, char *argv[])
{
    if (argc != 3) {
        fprintf(stderr, "Uso: %s <directorio> <dias>\n", argv[0]);
        return EXIT_FAILURE;
    }

    char *directorio = argv[1];
    char *fin;

    errno = 0;
    long dias = strtol(argv[2], &fin, 10);

    if (errno == ERANGE || fin == argv[2] ||
        *fin != '\0' || dias < 0 || dias > INT_MAX) {
        fprintf(stderr, "Error: numero de dias invalido.\n");
        return EXIT_FAILURE;
    }

    DIR *dir = opendir(directorio);

    if (dir == NULL) {
        perror("Error al abrir el directorio");
        return EXIT_FAILURE;
    }

    struct dirent *entrada;
    char **nombres = NULL;
    size_t cantidad = 0;

    // Guardar los nombres encontrados.
    while ((entrada = readdir(dir)) != NULL) {

        if (strcmp(entrada->d_name, ".") == 0 ||
            strcmp(entrada->d_name, "..") == 0) {
            continue;
        }

        size_t longitud = strlen(entrada->d_name) + 1;
        char *nombre = malloc(longitud);

        if (nombre == NULL) {
            perror("Error de memoria");
            goto error;
        }

        memcpy(nombre, entrada->d_name, longitud);

        char **aux = realloc(nombres,
                             (cantidad + 1) * sizeof(char *));

        if (aux == NULL) {
            free(nombre);
            perror("Error de memoria");
            goto error;
        }

        nombres = aux;
        nombres[cantidad++] = nombre;
    }

    closedir(dir);
    dir = NULL;

    // Ordenar lexicograficamente.
    qsort(nombres, cantidad, sizeof(char *), comparar);

    time_t ahora = time(NULL);

    printf("%-30s %-16s %-7s %s\n",
           "Nombre", "Modificacion", "Modo", "Tamano");
    printf("==================================================================\n");

    // Consultar los datos de cada entrada ordenada.
    for (size_t i = 0; i < cantidad; i++) {

        size_t longitud = strlen(directorio) +
                          strlen(nombres[i]) + 2;

        char *ruta = malloc(longitud);

        if (ruta == NULL) {
            perror("Error de memoria");
            goto error;
        }

        snprintf(ruta, longitud, "%s/%s", directorio, nombres[i]);

        struct stat informacion;

        if (stat(ruta, &informacion) == -1) {
            perror(ruta);
            free(ruta);
            continue;
        }

        free(ruta);

        double segundos = difftime(ahora, informacion.st_mtime);

        if (segundos >= 0 && segundos <= (double)dias * 86400.0) {

            char fecha[20];
            struct tm *tiempo = localtime(&informacion.st_mtime);

            if (tiempo == NULL ||
                strftime(fecha, sizeof(fecha),
                         "%Y-%m-%d %H:%M", tiempo) == 0) {
                continue;
            }

            printf("%-30s %-16s %06o %lld\n",
                   nombres[i],
                   fecha,
                   (unsigned int)informacion.st_mode,
                   (long long)informacion.st_size);
        }
    }

    for (size_t i = 0; i < cantidad; i++) {
        free(nombres[i]);
    }

    free(nombres);
    return EXIT_SUCCESS;

error:
    if (dir != NULL) {
        closedir(dir);
    }

    for (size_t i = 0; i < cantidad; i++) {
        free(nombres[i]);
    }

    free(nombres);
    return EXIT_FAILURE;
}
