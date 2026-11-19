Tarea 2 - Berumen Valdez Daniel

El programa lo hice en Python 3 sobre Windows 11. Solo usé bibliotecas que ya trae Python: os para leer el directorio y la información de cada archivo, sys para recibir los parámetros desde la línea de comandos y time para manejar las fechas.

Lo primero que hace el programa es revisar que se le pasen la ruta del directorio y el número de días; si falta alguno o los días no son un número, avisa y termina. Luego lee el contenido del directorio con os.listdir(), lo ordena por nombre y a cada archivo le saca sus datos con os.lstat(). Con la fecha de modificación calcula cuántos días tiene y, si entra en el rango pedido, imprime su nombre, fecha, permisos en octal y tamaño.

Me costó trabajo sobre todo la parte de los permisos y darle formato a la salida para que las columnas quedaran alineadas. Me apoyé en IA para entender qué hacía cada función de las bibliotecas y para corregir algunos errores, en especial la parte de los permisos para imprimirlos como aparecen en el ejemplo que proporcionó.
