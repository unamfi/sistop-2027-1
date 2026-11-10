/*
 * Tarea: Obtener información de un directorio
 * Alumnos: Beatriz Almaraz Garcia, Edson Barragán Galicia
 *
 * El programa recibe:
 *   1. Ruta de un directorio
 *   2. Número de días
 *
 * Muestra todas las entradas del directorio cuya última modificación
 * haya ocurrido hace el número de días indicado o menos.
 *
 * Para cada entrada se imprime:
 *   - Nombre
 *   - Fecha de modificación
 *   - Modo (permisos en octal)
 *   - Tamaño
 *
 * La salida se ordena lexicográficamente por nombre.
 */

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <ctime>
#include <iomanip>

#include <dirent.h>     // opendir(), readdir(), closedir()
#include <sys/stat.h>   // stat()
#include <unistd.h>

using namespace std;

/*
 * Estructura para almacenar la información
 * de cada entrada encontrada en el directorio.
 */
struct Entrada {
    string nombre;
    time_t modificacion;
    mode_t modo;
    off_t tamano;
};

int main(int argc, char* argv[]) {
    /*
     * Verificar cantidad de argumentos.
     *
     * Uso esperado:
     * ./archivos_recientes <directorio> <dias>
     */
    if (argc != 3) {
        cerr << "Invocacion: "
             << argv[0]
             << " <directorio> <dias>"
             << endl;

        return 1;
    }

    string ruta = argv[1];

    /*
     * Convertir el segundo argumento a entero.
     * Representa la cantidad máxima de días
     * transcurridos desde la última modificación.
     */
    int dias;

    try {
        dias = stoi(argv[2]);
    }
    catch (...) {
        cerr << "Error: el parametro <dias> debe ser un numero entero."
             << endl;

        return 1;
    }

    /*
     * Abrir el directorio indicado.
     */
    DIR* directorio = opendir(ruta.c_str());

    if (directorio == nullptr) {
        cerr << "Error: no se pudo abrir el directorio: "
             << ruta
             << endl;

        return 1;
    }

    vector<Entrada> resultados;

    /*
     * Obtener el tiempo actual para comparar la antigüedad de cada archivo.
     */
    time_t ahora = time(nullptr);

    struct dirent* elemento;

    /*
     * Recorrer todas las entradas del directorio.
     */
    while ((elemento = readdir(directorio)) != nullptr) {
        string nombre = elemento->d_name;

        /*
         * Ignorar las entradas especiales "." y "..".
         */
        if (nombre == "." || nombre == "..") {
            continue;
        }

        string rutaCompleta = ruta + "/" + nombre;

        struct stat informacion;

        /*
         * Obtener los metadatos de la entrada.
         */
        if (stat(rutaCompleta.c_str(), &informacion) == -1) {
            continue;
        }

        /*
         * Calcular cuántos días han pasado desde la última modificación.
         */
        double segundos =
            difftime(ahora, informacion.st_mtime);

        double diasTranscurridos =
            segundos / (60 * 60 * 24);

        /*
         * Guardar únicamente aquellas entradas que cumplan con el filtro solicitado.
         */
        if (diasTranscurridos <= dias) {
            Entrada e;

            e.nombre = nombre;
            e.modificacion = informacion.st_mtime;
            e.modo = informacion.st_mode;
            e.tamano = informacion.st_size;

            resultados.push_back(e);
        }
    }

    /*
     * Cerrar el directorio una vez terminado el recorrido.
     */
    closedir(directorio);

    /*
     * Ordenar lexicográficamente por nombre.
     */
    sort(
        resultados.begin(),
        resultados.end(),
        [](const Entrada& a, const Entrada& b) {
            return a.nombre < b.nombre;
        }
    );

    /*
     * Imprimir encabezado.
     */
    cout << left
         << setw(35) << "Nombre"
         << setw(20) << "Modificacion"
         << setw(10) << "Modo"
         << "Tamano"
         << endl;

    cout << string(75, '=') << endl;

    /*
     * Imprimir resultados.
     */
    for (const auto& e : resultados) {
        char fecha[20];

        strftime(
            fecha,
            sizeof(fecha),
            "%Y-%m-%d %H:%M",
            localtime(&e.modificacion)
        );

        cout << left
             << setw(35) << e.nombre
             << setw(20) << fecha;

        /*
         * Imprimir el modo en formato octal, como en el ejemplo.
         */
        cout << setfill('0')
             << oct
             << setw(6)
             << (e.modo & 077777)
             << setfill(' ');

        cout << dec
             << " ";

        cout << e.tamano
             << endl;
    }

    return 0;
}