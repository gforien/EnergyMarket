"""Home.py
Protocole de communication choisi : on envoie dans des messageQueue des messages au format "PID:quantitéDEnergie" avec un type pour spécifier l'action attendue.
    type=1 -> BUY au marché, donc seul le marché fait des receive(type=1)
    type=2 -> SELL au marche, donc seul le marché fait des receive(type=2)
    type=3 -> GIVE aux autres Homes, seules les Homes en besoin d'énergie font des receive(type=3)
    type=PID -> RECEIVED à la home concernée, donc seule une Home qui vient de donner de l'énergie fait un receive(type=getpid())

La bonne communication est assurée par un délai d'attente dt = 0.2s par exemple : 
    à t = 0, les homes ayant trop d'énergie la donnent (GIVE)
    à t = dt, les Homes ayant besoin d'énergie écoutent sur la messageQueue. S'il n'y a pas de message, elles ne bloquent pas
              S'il y a un message, elle prennent l'énergie et notifient la Home émettrice (RECEIVED)
    à t = 2*dt, les Homes qui ont donné de l'énergie écoutent sur la messageQueue. S'il n'y a pas de message, elles ne bloquent pas et vendent au marché (SELL)

ETP est déterminé aléatoirement entre 0, 1 et 2 :
    0 -> toujours donner l'énergie (communiste)
    1 -> toujours vendre au marché (capitaliste)
    2 -> essaye de donner l'énergie, sinon il la vend au marché (libéral)
"""

from multiprocessing import Process
from sysv_ipc import IPC_CREAT, MessageQueue, NotAttachedError, BusyError
from os import getpid
from signal import signal, SIGINT
from random import random
from time import sleep

marketKey = 221
timeDelay = 0.2
exit=False

def global_handler(sig, frame):
    global exit
    if sig == SIGINT:
        exit = True

def home():
    global exit

    CR = int(130*random())
    PR = int(70*random())
    ETP = int(3*random())
    print("[%d] Home : Init, CR = %d\tPR = %d\tETP = %d" % (getpid(), CR, PR, ETP))
    queueToMarket = MessageQueue(marketKey)
    print("[%d] Home : connected to messageQueue" % getpid())

    while not exit:
        sleep(2)

        # besoin d'énergie: il en cherche auprès des maisons, sinon il achète au marché
        if CR>PR:
            energyNeeded = CR-PR

            sleep(timeDelay) # petit délai pour que les receive() arrivent après les send()
            while energyNeeded > 0:
                try:
                    message, _ = queueToMarket.receive(block=False, type=3)
                    pid, quantity = message.decode().split(':')
                    energyNeeded -= int(quantity)
                    print("[%d] Home : received %d of energy" % (getpid(), int(quantity)))

                    response = str(getpid())+":ACK"
                    queueToMarket.send(response.encode(), type=int(pid))
                    print("[%d] Home : ACK sent to %s" % (getpid(), pid))
                except (NotAttachedError, BusyError):
                    break
            if energyNeeded>0:
                message = str(getpid())+':'+str(energyNeeded)
                queueToMarket.send(message.encode(), type=1)
                print("[%d] Home : bought %d of energy to the market" % (getpid(), energyNeeded))
            else :
                print("[%d] Home : got %d of free energy" % (getpid(), -energyNeeded))
                
        # trop d'énergie : il fait selon ETP
        elif PR>CR:
            energyBonus = PR-CR
            if ETP == 0:
                message = str(getpid())+':'+str(energyBonus)
                queueToMarket.send(message.encode(), type=3)
                print("[%d] Home : gave %d of energy" % (getpid(), energyBonus))
            elif ETP == 1:
                message = str(getpid())+':'+str(energyBonus)
                queueToMarket.send(message.encode(), type=2)
                print("[%d] Home : sold %d of energy to the market" % (getpid(), energyBonus))
            else:
                try:
                    message = str(getpid())+':'+str(energyBonus)
                    queueToMarket.send(message.encode(), type=3)
                    print("[%d] Home : gave %d of energy, waiting for response" % (getpid(), energyBonus))
                    sleep(2*timeDelay)
                    message, t = queueToMarket.receive(block=False, type=getpid())
                except (NotAttachedError, BusyError):
                    message = str(getpid())+':'+str(energyBonus)
                    queueToMarket.send(message.encode(), type=2)
                    print("[%d] Home : no response, sold %d of energy to the market" % (getpid(), energyBonus))
        else:
            print("[%d] Home : i'm autonomous !" % getpid())



if __name__ == '__main__':
    print("[%d] Main process : Init" % getpid())
    signal(SIGINT, global_handler)

    # we must implement a shared-variable
    homeProcess = Process(target=home)
    homeProcess.start()

    print("[%d] Main process : Done" % getpid())