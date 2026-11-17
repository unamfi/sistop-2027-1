//Clase principal del sistema de archivos
#ifndef FIUNAMFS_H
#define FIUNAMFS_H

#include <fstream>
#include <string>

#include "SuperBlock.h"

/**
 * Clase principal responsable de interactuar
 * con una imagen del sistema de archivos FiUnamFS.
 *
 * Durante este segundo commit la clase únicamente:
 *
 * - Abre la imagen
 * - Lee el superbloque
 * - Valida su contenido
 * - Muestra información básica
 */
class FiUnamFS {
private:

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

    /** Muestra la información cargada desde el superbloque.
     */
    void printInfo() const;
};

#endif