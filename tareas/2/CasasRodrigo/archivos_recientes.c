
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#include <dirent.h>

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

	while ((entrada = readdir(dir)) != NULL) {
    		if (entrada->d_name[0] == '.' &&
        	(entrada->d_name[1] == '\0' ||
        	(entrada->d_name[1] == '.' &&
         	entrada->d_name[2] == '\0'))) {
       		 continue;
	}

    	printf("%s\n", entrada->d_name);
}

	closedir(dir);



    return EXIT_SUCCESS;
}
