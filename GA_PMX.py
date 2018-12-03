import time
import numpy as np
from numpy import genfromtxt
from numpy import random
from random import randint
import xlsxwriter
from xlwt import Workbook

#CARGA DE DATOS BASE (Demanda, Flujos Posibles)
t_inicial=time.asctime( time.localtime(time.time()) )
print(t_inicial)

demanda = genfromtxt('demanda.csv', delimiter=',')  #Matrix de pedidos: (ref flujo, cant programada, t inicio disponible, T total en cola por procesar, t total en planta)
flujos = genfromtxt('flujos.csv', delimiter=',')    #Matrix de flujos posibles (fila referencia universal, columna procesos P (maquina, capMts minuto))

#PARAMETROS DE LA SIMULACIÓN
gen = 5       #Número de generaciones a crear
num = 10      #Cantidad d      e individuos que habra en la poblacion
tot= 12000    #5meses x 30 dias x 24 horas [horas totales]
mbase=4000    #tamaño de lote simulado  mts
m=41          #total de máquinas en el proceso
p=9           #Total de procesos máximo por referencia de tela

# MATRICES AUXILIARES

n=len(demanda)                      # computa el total de pedidos a asignar en el periodo
t_carga=time.asctime( time.localtime(time.time()) )
print(t_carga)

# MÉTODOS REQUERIDOS PARA EL ALGORITMO GENÉTICO

# Calcular los lotes por pedido
def TotLotes(demanda,n,mbase):
    Lotes=np.zeros((n,1))
    desperdicio=0
    for j in range(n):
        aux1=demanda[j][1]
        aux=round(aux1/mbase)
        desperdicio=desperdicio+(mbase*aux-aux1)
        Lotes[j][0]=aux
    return Lotes,desperdicio

#Crear individuos factibles
def individuo(n):
    ind = np.random.permutation(n)
    ind = np.insert(ind,0,0)
    return ind
   
#Crear población de individuos
def crearPoblacion():
    return [individuo(n) for i in range(num)]

# punto de corte para la mutación
def _subsection(item):
    L = list(range(0, len(item)-1))
    left = randint(0, len(L) - 1)
    right = randint(left + 1, len(L))
    return left, right

#reparación de cromosomas cruzados
def _get_replaced_item(left, right, child, gene, relation_map):

    # Hit a base case
    if gene not in relation_map:
        return gene

    mapped = relation_map[gene]
    if mapped not in child[left:right]:
        return mapped
    else:
        return _get_replaced_item(left, right, child, mapped, relation_map)

def _map(left, right, mother, father):
    return dict(zip(father[left:right], mother[left:right]))

def _getIndex(item, child, left, right):

    # Search left
    for i in range(0, left):
        if child[i] == item:
            return i

    # Search right
    for i in range(right, len(child)):
        if child[i] == item:
            return i


def _swap_leftover_genes(left, right, mothers_child, fathers_child):
    father_map = _map(left, right, mothers_child, fathers_child)

    # Swap left versions
    for i in range(0, left):
        gene = fathers_child[i]
        if gene not in father_map:
            continue
        mother_gene = _get_replaced_item(left, right, fathers_child, gene, father_map)

        fathers_child[i] = mother_gene
        m_index = _getIndex(mother_gene, mothers_child, left, right)
        mothers_child[m_index] = gene

    for i in range(right, len(fathers_child)):
        gene = fathers_child[i]
        if gene not in father_map:
            continue
        mother_gene = _get_replaced_item(left, right, fathers_child, gene, father_map)

        fathers_child[i] = mother_gene
        m_index = _getIndex(mother_gene, mothers_child, left, right)
        mothers_child[m_index] = gene

    return fathers_child, mothers_child


def _mate_one(mother, father):
    left, right = _subsection(mother)
    
    # Create copies (children) so we don't effect the original
    mothers_child = list(mother)
    fathers_child = list(father)

    # Step 1, swap the sides
    mothers_child[left:right] = father[left:right]
    fathers_child[left:right] = mother[left:right]


    # Step 2, deal with the leftovers
    child2, child1 = _swap_leftover_genes(left, right,mothers_child, fathers_child)

    return child2, child1






#Función de rendimiento o Fitness para una secuencia dada
Lotes,desperdicio=TotLotes(demanda,n,mbase)
print('El material de desperdicio es ',desperdicio)

def fitness(n,secuencia,demanda2,flujos,Lotes):
    maquinas = np.zeros((m, tot))       #almacena información sobre ocupación por hora en cada máquina 
    usomaq= np.zeros((m,3))             #almacena información sobre uso de las máquinas, (Tiempo de Uso, tiempo final, tiempo total en espera)
    Tfinlote=0
    TmayorPed=0                                  #tiempo total final para el pedido
    for ii in range(1,n+1):
        i=secuencia[ii]                          #Índice del pedido
        # Tomar los estados iniciales del pedido 
        indexRef=int(demanda2[i][0])             #indice del flujo  de 1 a 73 Posibles
        indexCanT=int(demanda2[i][1])            #cantidad total del pedido en lotes
        #
        Tcola=demanda2[i][3]                     #Tiempo total en espera de este pedido
        
 
        #
        aux2=int(Lotes[i][0])
        for lot in range(aux2):
            Tinicioped=int(demanda2[i][2])            #fecha de entrada para programar en planta, se reinicia por lote    
            for j in range(0,2*p,2):
                #Asignar_tiempos_por_cada_proceso/máquina
                MaqActual=int(flujos[indexRef-1][j])   #Maquina actual de la secuencia
                if MaqActual != 0:              #Voy a asignar a una maquina
                #Calcular horas que durara en la maquina
                   TiempoPro=round(indexCanT/(flujos[indexRef-1][j+1]))     #Tiempo duracion de la operacion esperada en horas
                #buscar si hay tiempos requeridos para el pedido en la maquina
                   Tinilote=Tinicioped             #fecha inicio pedido actual
                   asignada=0                      #el pedido no se ha asignado a la maquina
                   #w=0
                   while asignada==0:
                       Tlote=0                         #tamaño de lote dinamico
                       for l in range(Tinicioped,tot):
                           if maquinas[MaqActual-1][l]==0:
                               Tlote=Tlote+1
                               if Tlote>=TiempoPro: # Puedo asignar hasta ese punto
                                  Tfinlote=l        # El tiempo final es el auxiliar L actual
                                  Tinicioped=l+1    # Tiempo actual para el pedido
                                  for k in range(Tinilote,Tfinlote):
                                      maquinas[MaqActual-1][k]=i
                                      usomaq[MaqActual-1][1]=usomaq[MaqActual-1][1]+1  #tiempos utilizados de la maquina

                                  if Tfinlote>=usomaq[MaqActual-1][2]:
                                     usomaq[MaqActual-1][2]=Tfinlote

                                  # guardar el tiempo mayor usado por algun lote para el pedido
                                  if Tfinlote>TmayorPed:
                                      TmayorPed=Tfinlote

                                  asignada=1
                                  demanda2[i][4]=TmayorPed
                                  break
                           else:  #hasta ahí llego el lote, y no cabe para programarla
                                 Tcola=Tlote+Tcola+1
                                 Tlote=0
                                 Tinicioped=l+1
                                 Tinilote=Tinicioped
           
        demanda2[i][3]=Tcola
    for ty in range(m):
      usomaq[ty][2]=usomaq[ty][1]-usomaq[ty][0]
    
    return TmayorPed,maquinas,demanda2

 


#valuar las secuencias en la función objetivo
def EvalSecuencias(secuencia,num,n,demanda,flujos,Lotes):
    for i in range(num):
        print(i)
        Sec=secuencia[i][:]
        secuencia[i][0],maquinas,demanda2=fitness(n,Sec,demanda,flujos,Lotes)
    
    return secuencia,maquinas,demanda2



## ALGORITMO EVOLUTIVO - GENÉTICO SECUENCIADO

# Iniciar población inicial
secuencia=crearPoblacion()

# PROCESO DE EVOLUCIÓN
for e in range(gen):
    print(e)
    secuencia,maquinas,demanda2 = EvalSecuencias(secuencia,num,n,demanda,flujos,Lotes)

    # Ordenar de Menor a Mayor las soluciones
    secuencia.sort(key=lambda secuencia: secuencia[0])
    
    #imprimir mejor valor de la generación actual
    print(secuencia[0][0])
    
    
   # ESTRATEGIA EVOLUTIMA DE MUTACIÓN Y ALEATORIZACIÓN

   # Se conservan el mejor cromosomas para pasar a la próxima generación

   # Se copian el primero y segundo cromosoma para su cruzamiento
    mother=secuencia[0][:]
    father=secuencia[1][:]

   # copiar los 2 primeros padres y replicar para mutar estos ultimos.

    for y in range(2):
        secuencia[y+2][:]=secuencia[y][:]
  # Mutar los cromosomas 2 al 3
    for i in range(1,3):
        #Numero de posiciones a mutar
        k=randint(3,15)
        for l in range(k):
            kk=randint(1,n)
            kj=randint(1,n)
            # Alerta: posibilidad de que caiga la misma posición pero no se corrige aca
            aux=secuencia[i][kk]
            secuencia[i][kk]=secuencia[i][kj]
            secuencia[i][kj]=aux

  # Generar cruzamiento de los cromosomas  4 y 5
    child1, child2 = _mate_one(mother, father)
    secuencia[3][:]=child1
    secuencia[4][:]=child2
    
  # Aleatorizar los ultimos 5 cromosomas
    for y in range(5,num):
        ind = np.random.permutation(n)
        ind = np.insert(ind,0,0)
        secuencia[y][:]=ind

print(secuencia)

print()


t_final_Algoritmo=time.asctime( time.localtime(time.time()) )
print(t_final_Algoritmo)

#Calcular T-promedio terminacion de pedidos
PromFin=0
for i in range(n):
    PromFin=PromFin+demanda2[i][4]
PromFin=(PromFin/n)
print('El tiempo promedio en horas de los pedidos en planta es: ',PromFin)

#Calcular T-promedio en cola por iniciar pedido
PromFin2=0
for i in range(n):
    PromFin2=PromFin2+demanda2[i][3]
PromFin2=(PromFin2/n)
print('El tiempo promedio en horas de los pedidos en cola es: ',PromFin2)


# EXPORTAR SECUENCIA OPTIMA
wb=Workbook()
sheet1=wb.add_sheet('Sheet 1')
for i in range(n):
    data=secuencia[0][i+1]
    sheet1.write(i,0,int(data))
wb.save('xlwt example.xls')

# EXPORTAR A EXCEL PLAN DE ASIGNACIÓN OPTIMA
#secuencia, maquinas,demanda2 = fitness(n,secuencia[0][:],demanda,flujos,Lotes)
workbook = xlsxwriter.Workbook('array.xlsx')
worksheet = workbook.add_worksheet()
array = maquinas
row = 0
for col, data in enumerate(array):
    worksheet.write_column(row, col, data)
workbook.close()
