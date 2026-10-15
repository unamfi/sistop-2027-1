import threading
import time
import random

autos_Hoz=10
autos_Ver=10

#Creamos semaforo y torniquete necesrios

semaforo=threading.Semaphore(1) #semaforo
alto= threading.Semaphore(1)  #Torniquete
mutex_Hoz=threading.Semaphore(1)  # Mutex para carros en direcciones Horizontales
mutex_Ver=threading.Semaphore(1) # Mutes para carros en direcciones Vderticales

#En esta parte creamos e inicializamos los contadores 

Hoz=0
Ver=0

def Autos_Horizontales (num):
    global Hoz 
    while True:
        time.sleep(5*random.random())
        print(f"Un auto {num} ha llegado al cruce, esta en algun carril horizontal\n")
        alto.acquire()
        mutex_Hoz.acquire()
        Hoz +=1
        if Hoz==1:
            semaforo.acquire()
            print(f'El auto{num} es el primero en llegar al cruce\n')
        mutex_Hoz.release()
        alto.release()

        print(f"El auto {num} esta cruzando hay {Hoz} autos en estas direcciones\n")
        time.sleep(5*random.random())
        print(f"El auto {num} ha cruzado sin inconveniente alguno")
        mutex_Hoz.acquire()
        Hoz -=1

        if Hoz==0:
            print("El ultimo automovil en esta direccion ha cruzado. Cambiando Direccion de sentido\n")
            semaforo.release()
        mutex_Hoz.release()



def Autos_Verticales (num):
    global Ver 
    while True:
        time.sleep(5*random.random())
        print(f"Un auto {num} ha llegado al cruce, esta en algun carril horizontal\n")
        alto.acquire()
        mutex_Ver.acquire()
        Ver +=1
        if Ver==1:
            semaforo.acquire()
            print(f'El auto{num} es el primero en llegar al cruce\n')
        mutex_Ver.release()
        alto.release()

        print(f"El auto {num} esta cruzando hay {Ver} autos en estas direcciones\n")
        time.sleep(5*random.random())
        print(f"El auto {num} ha cruzado sin inconveniente alguno")
        mutex_Ver.acquire()
        Ver -=1

        if Ver==0:
            print("El ultimo automovil en esta direccion ha cruzado. Cambiando Direccion de sentido\n")
            semaforo.release()
        mutex_Ver.release()



for i in range (autos_Hoz):
    threading.Thread(target=Autos_Horizontales,args=[i]).start()

for i in range (autos_Ver):
    threading.Thread(target=Autos_Verticales,args=[i]).start()
