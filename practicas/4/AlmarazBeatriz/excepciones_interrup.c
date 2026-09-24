#include <stdio.h>
#include <signal.h>
#include <stdlib.h>

// Manejador de interrupción (simulada con señal SIGINT)
void manejador_interrupcion(int sig) {
    printf("\n[InterrupciOn] Señal recibida: %d (Ctrl+C)\n", sig);
    printf("El flujo del programa fue interrumpido externamente.\n");
    exit(0); // Terminamos el programa
}

void ejecutar_excepcion(void) {
    int a = 10, b = 0;

    printf("\n[ExcepciOn] Intentando dividir %d entre %d...\n", a, b);
    int c = a / b;
    printf("Resultado: %d\n", c);
}

void ejecutar_interrupcion(void) {
    // Registrar el manejador para la señal SIGINT
    signal(SIGINT, manejador_interrupcion);

    // Ejemplo de interrupción: esperar señal externa
    printf("\n[InterrupciOn] Programa en espera. Presiona Ctrl+C para interrumpir.\n");
    while (1) {
        // Loop infinito esperando la señal
    }
}

int main(void) {
    int opcion;

    printf("=== ComparaciOn Excepciones vs Interrupciones ===\n");
    printf("1. Ejecutar excepciOn (divisiOn por cero)\n");
    printf("2. Ejecutar interrupciOn (Ctrl+C)\n");
    printf("Selecciona una opciOn: ");
    scanf("%d", &opcion);

    if (opcion == 1) {
        ejecutar_excepcion();
    } else if (opcion == 2) {
        ejecutar_interrupcion();
    } else {
        printf("OpciOn no vAlida.\n");
    }

    return 0;
}
