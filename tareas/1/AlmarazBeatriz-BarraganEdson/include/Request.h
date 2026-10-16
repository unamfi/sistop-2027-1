#pragma once

#include <string>

/**
 * Representa una solicitud recibida por el servidor.
 *
 * En un servidor web real podría contener:
 * - URL solicitada
 * - Dirección IP del cliente
 * - Método HTTP
 *
 * Para esta simulación únicamente almacenamos un
 * identificador y la página requerida.
 */

struct Request {
    int id;
    std::string page;
};