#include <stdio.h>

int main(int argc, char *argv[])
{
    if (argc < 2) {
        printf("Uso: %s <nombre>\n", argv[0]);
        return 1;
    }

    printf("Hola, %s!\n", argv[1]);
    return 0;
}
