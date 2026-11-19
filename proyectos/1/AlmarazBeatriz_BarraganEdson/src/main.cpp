/**
 * Descripción:
 * Punto de entrada principal del programa.
 * En esta etapa del desarrollo el programa:
 *
 * - Abre la imagen FiUnamFS.
 * - Lee y valida el superbloque.
 * - Muestra la información general del volumen.
 * - Lee las entradas del directorio.
 * - Carga en memoria los archivos válidos encontrados.
 *
 * Este avance corresponde al tercer commit funcional del proyecto.
 */

#include "../include/FiUnamFS.h"

#include <iostream>
#include <string>
int main(int argc, char* argv[]) {
    // Instancia principal del sistema de archivos
    FiUnamFS fs;

    std::cout << "Abriendo imagen FiUnamFS...\n";

    // Intentar abrir la imagen
    // Utilizar la imagen indicada por el usuario.
    // Si no se proporciona una ruta, abrir la imagen original.
    std::string imagePath = "../fiunamfs.img";

    if (argc > 1) {
        imagePath = argv[1];
    }

    if (!fs.openImage(imagePath)) {
        std::cerr << "Error: No se pudo abrir la imagen: "
                << imagePath << '\n';
        return 1;
    }

    std::cout << "Imagen abierta correctamente.\n";

    // Leer información del superbloque
    if (!fs.loadSuperBlock()) {
        std::cerr
            << "Error: No fue posible leer el superbloque.\n";

        return 1;
    }

    // Validar que sea una imagen FiUnamFS válida
    if (!fs.validate()) {
        std::cerr
            << "Error: El archivo no corresponde "
            << "a una imagen valida de FiUnamFS.\n";

        return 1;
    }

    std::cout
        << "\nSistema de archivos validado correctamente.\n";

    // Mostrar información general obtenida desde el superbloque.
    fs.printInfo();

    // Leer las entradas de directorio
    // definidas en los clusters 1 al 4.
    fs.loadDirectory();

    // Mostrar archivos encontrados
    fs.listFiles();

    // Mostrar los archivos detectados (salida para depuración).
    //fs.debugDirectory();

   
    // Permitir al usuario elegir el archivo que desea exportar.
    std::cout << "\n=== EXPORTAR ARCHIVO ===\n";

    std::string filename;

    std::cout << "Escribe el nombre del archivo a exportar: ";
    std::getline(std::cin, filename);

    if (!filename.empty()) {
        // Guardar el archivo en la carpeta de salida.
        std::string destination = "salida/" + filename;

        if (fs.exportFile(filename, destination)) {
            std::cout << "Exportacion completada.\n";
        } else {
            std::cerr << "No fue posible exportar el archivo.\n";
        }
    } else {
        std::cout << "No se ingreso ningun archivo.\n";
    }


   
        // Permitir importar un archivo desde Windows hacia FiUnamFS.
    std::cout << "\n=== IMPORTAR ARCHIVO ===\n";

    std::string source;

    std::cout << "Escribe la ruta del archivo que deseas importar: ";
    std::getline(std::cin, source);

    if (!source.empty()) {
        std::string importName;

        std::cout << "Nombre que tendra dentro de FiUnamFS: ";
        std::getline(std::cin, importName);

        if (fs.importFile(source, importName)) {
            std::cout << "Importacion completada.\n";

            // Mostrar el directorio actualizado.
            fs.listFiles();
        } else {
            std::cerr << "No fue posible importar el archivo.\n";
        }
    } else {
        std::cout << "No se solicito ninguna importacion.\n";
    }
     return 0;
}