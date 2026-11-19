def GaussJordan():
    # SOLICITANDO N ECUACIONES Y VARIABLES
    n = int(input("Ingrese el número de ecuaciones (y variables) de su sistema: "))

    # CREAMOS UNA LISTA CON LAS POSIBLES VARIABLES QUE PODREMOS UTILIZAR (USANDO LETRAS DEL ALFABETO)
    variables = []
    for i in range(n):
        if i < 26:
            variables.append(chr(97 + i))
        else:
            variables.append(f"x{i + 1}")

    #CREAREMOS EL SISTEMA DE ECUACIONES EN LA CUAL LO VEREMOS COMO UNA MATRIZ
    matriz_jordan = []
    print("Ingrese los coeficientes y el resultado para cada ecuación:")
    for i in range(n):
        fila = []
        print(f"Ecuación {i + 1}:")
        for j in range(n + 1):
            if j < n:
                valor = float(input(f"Coeficiente de {variables[j]}: "))
            else:
                valor = float(input("Resultado:"))
            fila.append(valor)
        matriz_jordan.append(fila)

    # REALIZANDO EL TRIANGULO INFERIOR
    for i in range(n):
        # INTERCAMBIANDO FILAS SI ES QUE EL PRIMER ELEMENTO DE NUESTRA DIAGONAL ES IGUAL A 0
        try:    
            if matriz_jordan[i][i] == 0:
                for k in range(i + 1, n):
                    if matriz_jordan[k][i] != 0:
                        # Intercambiar filas
                        matriz_jordan[i], matriz_jordan[k] = matriz_jordan[k], matriz_jordan[i]
                        print(f"Intercambiar fila {i + 1} con fila {k + 1}")
                        for fila in matriz_jordan:
                            print(fila)
                        print()
                        break
                    else:
                        print("El sistema no tiene solución única.")
        except ValueError:
            print("Ingresa un número válido")

        #REALIZANDO QUE EL ELEMENTO DE LA DIAGONAL SEA 1
        elemento_diagonal = matriz_jordan[i][i]
        for j in range(n + 1):
            matriz_jordan[i][j] /= elemento_diagonal
        print(f"Multiplicar fila {i + 1} por {1 / elemento_diagonal} para hacer que el elemento de la diagonal sea 1")
        for fila in matriz_jordan:
            print(fila)
        print()

        # VOLVIENDO 0 LO QUE ESTA DEBAJO DE LA DIAGONAL
        for k in range(i + 1, n):
            inverso_aditivo = -1 * matriz_jordan[k][i]
            for j in range(n + 1):
                matriz_jordan[k][j] += inverso_aditivo * matriz_jordan[i][j]
            print(f"Multiplicar {inverso_aditivo} * fila {i + 1} y sumarlo en fila {k + 1}, escribiéndolo en la fila {k + 1}")
            for fila in matriz_jordan:
                print(fila)
            print()

    # REALIZANDO TRIANGULO SUPERIOR
    for i in range(n - 1, -1, -1):
        for k in range(i - 1, -1, -1):
            inverso_aditivo = -1 * matriz_jordan[k][i]
            for j in range(n + 1):
                matriz_jordan[k][j] += inverso_aditivo * matriz_jordan[i][j]
            print(f"Multiplicar {inverso_aditivo} * fila {i + 1} y sumarlo en fila {k + 1}, escribiéndolo en la fila {k + 1}")
            for fila in matriz_jordan:
                print(fila)
            print()

    # IMPRIMIENDO VALORES DE LAS VARIABLES QUE SATISFACEN EL SISTEMA DE ECUACIONES
    print("Valores finales: ")
    for i in range(n):
        RESULTADO = (matriz_jordan[i][n])
        print(f"{variables[i]} = {RESULTADO}")
GaussJordan()
