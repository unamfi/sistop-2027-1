#ifndef SUPERBLOCK_H
#define SUPERBLOCK_H

#include <string>
#include <cstdint>

/**
 * Representa la información contenida en el superbloque
 * del sistema de archivos FiUnamFS.
 *
 * El superbloque corresponde al cluster 0 del volumen
 * y almacena los metadatos principales necesarios para
 * validar e interpretar correctamente la imagen.
 */
struct SuperBlock {
    /// Nombre del sistema de archivos (FiUnamFS)
    std::string fileSystemName;

    /// Versión del sistema de archivos (27-1)
    std::string version;

    /// Etiqueta o nombre asignado al volumen
    std::string volumeLabel;

    /// Tamaño de cada cluster en bytes
    uint32_t clusterSize;

    /// Cantidad de clusters destinados al directorio
    uint32_t directoryClusters;

    /// Cantidad total de clusters del volumen
    uint32_t totalClusters;
};

#endif