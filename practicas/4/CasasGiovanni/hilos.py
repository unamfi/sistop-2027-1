import threading
import time

def desayunar():
    print('Iniciando desayunar')
    time.sleep(3)
    print('finalizado')

def estudiar():
    print('Iniciando estudiar')
    time.sleep(4)
    print('finalizado')

def ducharse():
    print('Iniciando ducharse')
    time.sleep(5)
    print('finalizado')

inicio = time.perf_counter()

x=threading.Thread(target=desayunar, args=())
x.start()

y=threading.Thread(target=estudiar, args=())
y.start()

z=threading.Thread(target=ducharse, args=())
z.start()



    

print(threading.active_count()) 
print(threading.enumerate())

fin = time.perf_counter()
tiempo = fin - inicio
print(tiempo)

with open("hola.txt", "w") as f:
    f.write("Archivo Generado.\n")