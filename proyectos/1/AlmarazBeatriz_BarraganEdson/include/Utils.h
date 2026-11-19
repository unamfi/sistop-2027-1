// Utilidades auxiliares
#ifndef UTILS_H
#define UTILS_H

#include <fstream>
#include <string>
#include <cstdint>

/**
 * Lee un entero de 32 bits almacenado en formato
 * little-endian desde un archivo binario.
 *
 * @param file Archivo abierto.
 * @return Valor convertido al formato nativo.
 */
uint32_t readLittleEndian32(std::fstream& file);

/**
 * Lee una cadena de longitud fija desde la posición
 * actual del archivo.
 *
 * Si la cadena contiene caracteres nulos ('\0'),
 * éstos son eliminados para facilitar su manejo.
 *
 * @param file Archivo binario abierto.
 * @param length Número de bytes a leer.
 * @return Cadena procesada.
 */
std::string readFixedString(
    std::fstream& file,
    size_t length
);
/**
 * Escribe un entero de 32 bits en formato little-endian.
 *
 * @param file Imagen binaria donde se escribira el valor.
 * @param value Numero que se desea almacenar.
 */
void writeLittleEndian32(std::fstream& file, uint32_t value);

#endif