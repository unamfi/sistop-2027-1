#include "../include/Trabajador.h"
#include "../include/server.h"

#include <iostream>
#include <thread>
#include <chrono>

Worker::Worker(
    int workerId,
    Server& server)
    : workerId(workerId),
      server(server)
{
}

void Worker::operator()()
{
    while (true)
    {
        Request request =
            server.getRequest();

        if (request.id == -1)
        {
            break;
        }

        std::cout
            << "[Worker "
            << workerId
            << "] atendiendo "
            << request.page
            << "\n";

        std::this_thread::sleep_for(
            std::chrono::milliseconds(
                1000 + rand() % 3000
            )
        );

        std::cout
            << "[Worker "
            << workerId
            << "] finalizo "
            << request.page
            << "\n";

        server.logRequest(
            workerId,
            request.page
        );
    }
}