
import threading
import time
import random


cont_renos = 0
cont_elfos = 0
mutex = threading.Semaphore(1)
semSanta = threading.Semaphore(0)
semRenos = threading.Semaphore(0)
semElfos = threading.Semaphore(0)
grupoElfos = threading.Semaphore(3)


def santa_claus():
    global cont_renos

    while True:
        semSanta.acquire()
        mutex.acquire()

        if cont_renos == 9:
            print("\nSanta: Los renos ya están listo\n")
            print("Preparando el Trineo\n")

            cont_renos = 0

            for i in range(9):
                semRenos.release()

        elif cont_elfos == 3:
            print("\Ayudando a los 3 elfos...\n")

            for i in range(3):
                semElfos.release()

        mutex.release()


def renos():
    global cont_renos

    time.sleep(random.uniform(0.1, 1.0))
    print("Un reno ya está devuelta de sus vacaciones.\n")

    mutex.acquire()
    cont_renos += 1

    if cont_renos == 9:
        semSanta.release()

    mutex.release()

    semRenos.acquire()
    print("Un reno esta listo para el viaje.\n")


def elfos():
    global cont_elfos

    grupoElfos.acquire()

    print("Un elfo necesita ayuda.\n")

    mutex.acquire()
    cont_elfos += 1

    if cont_elfos == 3:
        semSanta.release()

    mutex.release()

    semElfos.acquire()

    mutex.acquire()
    cont_elfos -= 1

    if cont_elfos == 0:
        for _ in range(3):
            grupoElfos.release()

    mutex.release()

    print("Un elfo recibio ayuda y continua trabajando.\n")



threading.Thread(target=santa_claus, daemon=True).start()


hilos_renos = []

for i in range(9):
    hilo = threading.Thread(target=renos)
    hilos_renos.append(hilo)
    hilo.start()


hilos_elfos = []

for i in range(6):
    hilo = threading.Thread(target=elfos)
    hilos_elfos.append(hilo)
    hilo.start()

for hilo in hilos_renos:
    hilo.join()

for hilo in hilos_elfos:
    hilo.join()

print("Todos los renos y elfos terminaron.\n")
