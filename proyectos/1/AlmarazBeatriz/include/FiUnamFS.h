//Clase principal del sistema de archivos
#ifndef FIUNAMFS_H
#define FIUNAMFS_H

#include <fstream>
#include <string>

#include "SuperBlock.h"
#include <vector>
#include "DirectoryEntry.h"

/**
 * Clase principal responsable de interactuar
 * con una imagen del sistema de archivos FiUnamFS.
 *
 * Funcionalidades implementadas hasta este punto:
 *
 * - Apertura de la imagen del sistema de archivos.
 * - Lectura del superbloque.
 * - Validación del sistema de archivos.
 * - Obtención de metadatos generales del volumen.
 * - Lectura de las entradas del directorio.
 * - Almacenamiento de archivos válidos en memoria.
 *
 * Funcionalidades pendientes:
 *
 * - Listado detallado de archivos.
 * - Copia de archivos desde FiUnamFS al sistema anfitrión.
 * - Copia de archivos hacia FiUnamFS.
 * - Eliminación de archivos.
 * - Sincronización mediante hilos.
 */
class FiUnamFS {
private:

    /// Lista de entradas válidas en el directorio
    std::vector<DirectoryEntry> files;

    /// Archivo binario que representa el volumen
    std::fstream image;

    /// Información cargada desde el superbloque
    SuperBlock superBlock;

public:

    /**
     * Abre la imagen del sistema de archivos.
     *
     * @param path Ruta del archivo .img
     * @return true si la apertura fue exitosa.
     */
    bool openImage(const std::string& path);

    /**
     * Lee el superbloque desde el cluster cero.
     *
     * @return true si la lectura fue exitosa.
     */
    bool loadSuperBlock();

    /**
     * Verifica que la imagen corresponda
     * a una implementación válida de FiUnamFS.
     *
     * @return true si nombre y versión coinciden.
     */
    bool validate();

    // Muestra la información cargada desde el superbloque.
    void printInfo() const;

    /**
     * Carga en memoria los archivos del directorio.
     */
    void loadDirectory();

    // Muestra la información cargada desde el directorio.
    void debugDirectory() const;
};

#endif