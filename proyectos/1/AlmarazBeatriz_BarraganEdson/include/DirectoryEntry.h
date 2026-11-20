#ifndef DIRECTORYENTRY_H
#define DIRECTORYENTRY_H

#include <cstdint>
#include <string>

/// Representa una entrada válida dentro del directorio de FiUnamFS.
struct DirectoryEntry {
    /// Tipo de entrada ('F')
    char type;

    /// Nombre del archivo
    std::string filename;

    /// Tamaño en bytes
    uint32_t size;

    /// Cluster inicial
    uint32_t startCluster;

    /// Fecha de creación
    std::string creationDate;

    /// Fecha de modificación
    std::string modificationDate;
};

#endif