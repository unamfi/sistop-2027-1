#include "../include/stats.h"

#include <iostream>

Statistics::Statistics()
    : totalRequests(0)
{
}

void Statistics::registerRequest(
    int workerId,
    const std::string& page)
{
    std::lock_guard<std::mutex> lock(mutex_);

    totalRequests++;

    pageRequests[page]++;

    workerRequests[workerId]++;
}

void Statistics::printReport()
{
    std::lock_guard<std::mutex> lock(mutex_);

    std::cout << "\n========== REPORTE ==========\n";

    std::cout << "\nTotal solicitudes: "
              << totalRequests
              << "\n";

    std::cout << "\nPaginas solicitadas:\n";

    for (const auto& page : pageRequests)
    {
        std::cout
            << page.first
            << " -> "
            << page.second
            << "\n";
    }

    std::cout << "\nTrabajo por hilo:\n";

    for (const auto& worker : workerRequests)
    {
        std::cout
            << "Worker "
            << worker.first
            << " -> "
            << worker.second
            << "\n";
    }
}