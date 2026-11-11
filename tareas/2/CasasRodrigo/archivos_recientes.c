
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#include <dirent.h>
#include <sys/stat.h>
#include <time.h>
#include <string.h>

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
        fprintf(stderr, "Error: el numero de dias debe ser un entero no negativo.\n");
        return EXIT_FAILURE;
    }

    DIR *dir = opendir(directorio);

    if (dir == NULL) {
        perror("Error al abrir el directorio");
        return EXIT_FAILURE;
    }

    struct dirent *entrada;
    time_t ahora = time(NULL);

    printf("%-30s %-16s %-7s %s\n",
           "Nombre", "Modificacion", "Modo", "Tamano");
    printf("==================================================================\n");

    while ((entrada = readdir(dir)) != NULL) {

        if (strcmp(entrada->d_name, ".") == 0 ||
            strcmp(entrada->d_name, "..") == 0) {
            continue;
        }

        char ruta[4096];

        int longitud = snprintf(ruta, sizeof(ruta), "%s/%s",
                                directorio, entrada->d_name);

        if (longitud < 0 || (size_t)longitud >= sizeof(ruta)) {
            fprintf(stderr, "Ruta demasiado larga: %s\n", entrada->d_name);
            continue;
        }

        struct stat informacion;

        if (stat(ruta, &informacion) == -1) {
            perror(ruta);
            continue;
        }

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
                   entrada->d_name,
                   fecha,
                   (unsigned int)informacion.st_mode,
                   (long long)informacion.st_size);
        }
    }

    closedir(dir);

    return EXIT_SUCCESS;
}
