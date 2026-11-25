#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
        char buffer[256];
        if(argc > 1) strcpy(buffer, argv[1]);
        printf("Escribiste %s\n", buffer);
        return 0;
}
