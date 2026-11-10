#include "../include/server.h"

Server::Server()
    : shuttingDown(false) {
}

void Server::submitRequest(const Request& request) {
    {
        std::lock_guard<std::mutex> lock(queueMutex);

        // La nueva solicitud se incorpora a la cola
        // compartida para que sea atendida posteriormente.
        pendingRequests.push(request);
    }
    
    // Despierta a uno de los trabajadores que
    // pudiera encontrarse bloqueado esperando trabajo.
    requestAvailable.notify_one();
}

Request Server::getRequest() {
    std::unique_lock<std::mutex> lock(queueMutex);
/*
     * El trabajador permanece dormido mientras:
     *   - no existan solicitudes pendientes
     *   - el servidor no esté cerrándose
     *
     * Esto evita espera activa (busy waiting),
     * uno de los objetivos principales del ejercicio.
     */
    requestAvailable.wait(
        lock,
        [this]
        {
            return !pendingRequests.empty()
                || shuttingDown;
        }
    );

    /*
     * Si el cierre fue solicitado y ya no hay
     * peticiones pendientes, devolvemos una
     * solicitud centinela para terminar la hebra.
     */
    
    if (shuttingDown &&
        pendingRequests.empty())
    {
        return {-1, ""};
    }

    Request request =
        pendingRequests.front();

    pendingRequests.pop();

    return request;
}

void Server::shutdown() {
    {
        std::lock_guard<std::mutex> lock(queueMutex);

        shuttingDown = true;
    }

    requestAvailable.notify_all();
}

void Server::logRequest(
    int workerId, const std::string& page) {
    statistics.registerRequest(workerId, page);
}

Statistics& Server::getStatistics() {
    return statistics;
}