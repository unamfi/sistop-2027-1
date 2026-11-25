//Contiene macros con los valores minimos y maximos de los enteros
#include <limits.h>
#include <stdio.h>

int main(int argc, char *argv[]){
  int numero;
  //INT_MAX es el valor máximo que se le puede asignar a un entero.
  numero = INT_MAX;
  printf("El número máximo que puede representarse en un entero es %d (%x)\n",
	 numero, numero);
  //Desbordamiento de entero con signo
  numero += 1;
  printf("...Porque si me paso... ¡Obtengo %d (%x)!\n", numero, numero);
  printf("Nomás por si acaso, recordemos que “-1” es %d (%x)\n", -1, -1);
}
