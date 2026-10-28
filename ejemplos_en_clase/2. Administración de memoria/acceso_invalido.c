#include <stdio.h>
#include <stdlib.h>

int MAX = 10;

void main () {
  int* arr;
  int i;
  arr = malloc(MAX * sizeof(int));
  /* Inicializo mi arreglo */
  for (i=0; i<MAX; i++)
    arr[i] = 67;
  /* Recorro mi arreglo -- pero “por error”
     sobrepaso los límites */
  for (i=0; i<1000000; i++) // Al pasar 33787 genera segfault
    printf("En la posición %d tengo: %d\n", i, arr[i]);
}
