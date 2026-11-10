Use el lenguaje Python , Con el sistema operativo Windowsn 11 , en el editor Visual Studio Code  

Estrategia de sincronización (mecanismo y patron) 
Utilice 2 mutex , uno para cada lado de los cruces ya que puse 2 contadores (autos en direcciones horizontales y en direcciones verticales) , es decir lo que hice fue en lugar de utilizar 4 , solo use 2 porque me base en los semáforos de la vida real , ya que cuando una dirección , por ejmplo de derecha a izquierda esta en verde tmabien el de izquierda a derecha lo esta , mientras los que son perpendiculares a estos están en rojo. Utilice en si un solo "semáforo" para el cruce el cual lo comparten ambos , además de un torniquete . Para el patron utilice el switch para ambos( contador , mutex y semáforo ). y el torniquete para que no se quede esperando por simpre el otro sentido.

Refinamientos:
No se si cuente como refinamiento , pero puse el torniquete para evitar la inanición , que lo plantee desde un inicio y no no hice en 4 sentidos

Dudas: 
La verdad si puedo quedar mucho mejor , en especial por que solo pude implementar 2 sentidos y no 4 :( .

* La verdad en algunos puntos si utilice la IA Claude , primero para ir uniendo un poco el planteamiento inicial que tenia y ver si iba por buen camino. 

*Utilice como plantilla el código de "alumnos y maestro" que presento en la clase , lo adapte . ya que al leer el problema se me hizo muy parecido al del cruce , principalmente por el torniquete.
