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

    /// Muestra los archivos encontrados dentro del directorio.
    void listFiles() const;

    
        /**
     * Exporta un archivo desde FiUnamFS
     * hacia una ruta del sistema anfitrion.
     *
     * @param filename Nombre del archivo en FiUnamFS.
     * @param destination Ruta completa del archivo de destino.
     * @return true si la exportacion fue exitosa.
     */
    bool exportFile(
        const std::string& filename,
        const std::string& destination
    );
        /**
 * Importa un archivo desde el sistema anfitrion
 * hacia la imagen FiUnamFS.
 *
 * @param source Ruta del archivo en Windows.
 * @param filename Nombre que tendra dentro de FiUnamFS.
 * @return true si la importacion fue exitosa.
 */
    bool importFile(
        const std::string& source,
        const std::string& filename
    );
 };

#endif 