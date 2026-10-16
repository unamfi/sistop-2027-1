import threading
import time
import random 

nombres_ratones = ['Ceviche', 'Lalo', 'El Juan', 'Orlando', 'Empanada', 'Otto', 'Tito Baratito', 'Esponjoso', 'Chesco', 'Mimo', 'Concha',
                  'Abelardo', 'Enrique', 'Gomita', 'Chocorol']

nombres_gatos = ['Quesito', 'Mosquín Gordín', 'Compita', 'Camarada', 'Petunia', 'Ready Fredie', 'Later Aligator', 'Quemonito', 
                   'Casi Merito', 'Kero Bonito']


def pedir_entero(mensaje, minimo, maximo):
    while True:
        try:
            valor = int(input(f'{mensaje} [{minimo} - {maximo}]: '))
            if minimo <= valor <= maximo:
                return valor
            else:
                print(f'Error: el valor debe estar entre {minimo} y {maximo}.')
        except ValueError:
            print('Error: debes ingresar un número entero válido.')



min_gatos, max_gatos = 5, 10
min_ratones, max_ratones = 7, 15
min_platos, max_platos = 3, 7

num_g = pedir_entero('Ingresa el número entero de gatos entre', min_gatos, max_gatos)
num_r = pedir_entero('Ingresa el número entero de ratones entre', min_ratones, max_ratones)
num_p = pedir_entero('Ingresa el número entero de platos entre', min_platos, max_platos)

print(f'\nConfiguración final: {num_g} gatos, {num_r} ratones y {num_p} platos.')

platos_mutex = threading.Semaphore(1)
gatos_mutex = threading.Semaphore(1)
raton_mutex = threading.Semaphore(1)
torniquete = threading.Semaphore(1)
gatos_comiendo = 0
ratones_comiendo = 0
platos_control = threading.Semaphore(num_p)

def gatos(num):
 global gatos_comiendo

 print(f'Un gato está hambriento.')
 time.sleep(5*random.random())
 torniquete.acquire()
 torniquete.release()

 platos_control.acquire()
 gatos_mutex.acquire()
 gatos_comiendo += 1
 if gatos_comiendo == 1:
  platos_mutex.acquire()
  print(f'Un gato comienza a comer, es {nombres_gatos[num]}.')
  print(f'Cat time!')
 elif gatos_comiendo == 5:
  print(f'Llega {nombres_gatos[num]} y, ¡Ya no quedan platos!')
 else:
  print(f'Los gatos siguen llegando, es {nombres_gatos[num]}.')
 print(f'Hay {gatos_comiendo} gatos comiendo')
 gatos_mutex.release()
 

 print(f'"Ruidos de gatos comiendo."')
 time.sleep(2*random.random())
 
 gatos_mutex.acquire()
 gatos_comiendo -= 1
 if gatos_comiendo == 0:
  print(f'Soy {nombres_gatos[num]}, el último gato y ya me voy.')
  platos_mutex.release()
  print(f'Se fueron todos los gatos.')
 else:
  print(f'Se fue {nombres_gatos[num]}.')
 gatos_mutex.release()
 platos_control.release()
 



def raton(num):
 global ratones_comiendo
 
 print(f'Un ratón está hambriento.')
 time.sleep(5*random.random())
 torniquete.acquire()
 torniquete.release()

 platos_control.acquire()
 raton_mutex.acquire()
 ratones_comiendo += 1
 if ratones_comiendo == 1:
   platos_mutex.acquire()
   print(f'Un ratón comienza a comer, es {nombres_ratones[num]}.')
   print(f'Mouse time!')
 elif ratones_comiendo == 5:
   print(f'Llega {nombres_ratones[num]} y, ¡Ya no quedan platos!')
 else:
   print(f'Los ratones siguen llegando, es {nombres_ratones[num]}.')
 print(f'Hay {ratones_comiendo} ratones comiendo.')
 raton_mutex.release()
 
 print(f'"Ruidos de ratones comiendo."')
 time.sleep(2*random.random())

 
 raton_mutex.acquire()
 ratones_comiendo -= 1
 if ratones_comiendo == 0:
   print(f'Soy {nombres_ratones[num]}, el último ratón y ya me voy.')
   platos_mutex.release()
   print(f'Se fueron todos los ratones.')
 else:
   print(f'Se fue {nombres_ratones[num]}.')
 raton_mutex.release()
 platos_control.release()
 
hilos = []

for cat in range(num_g):
 hilos.append(threading.Thread(target=gatos, args=[cat]))

for mouse in range(num_r):
 hilos.append(threading.Thread(target=raton, args=[mouse]))

for h in hilos:
  h.start()

for h in hilos:
  h.join()

input("\nPresione Enter para salir...")