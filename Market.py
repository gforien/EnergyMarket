"""EnergyMarket.py

A multi-independant-processes simulation about the energy market."""

from multiprocessing import Value, Array, Process
from signal import signal, SIGINT, SIGUSR1, SIGUSR2
from sysv_ipc import IPC_CREAT, MessageQueue, NotAttachedError, BusyError
from os import kill, getpid
from random import random
from time import sleep
from queue import Queue, Empty
from threading import Thread, current_thread

marketKey = 221

def weather(weatherAttributes, exitFlag):
    print("[%d] Weather : Init" % getpid())
    type(weatherAttributes)
    weatherAttributes[0] = 0
    weatherAttributes[1] = 0
    while not exitFlag.value:
        sleep(6)
        weatherAttributes[0] = 20 + 5*random()      # Temperature
        weatherAttributes[1] = 10 + 30*random()     # Rain
        print("[%d] Weather update : T = %.2f and R = %.2f" % (getpid(), weatherAttributes[0], weatherAttributes[1]))
    print("[%d] Weather : Exit" % getpid())


def external(marketPID, exitFlag):
    print("[%d] External : Init" % getpid())
    while not exitFlag.value:
        sleep(8)
        if int(2*random()):
            kill(marketPID, SIGUSR1)
            print("[%d] External event : SIGUSR1 sent." % getpid())
        if int(2*random()):
            kill(marketPID, SIGUSR2)
            print("[%d] External event : SIGUSR2 sent." % getpid())
    print("[%d] External : Exit" % getpid())



def market(weatherAttributes, exitFlag):
    print("[%d] Market (main) : Init" % getpid())
    global marketKey

    # create handler with a closure, and launch external process
    externalEvents = [0, 0]
    def market_handler(sig, frame):
        if sig == SIGUSR1:
            externalEvents[0] = 1
        elif sig == SIGUSR2:
            externalEvents[1] = 1
    signal(SIGUSR1, market_handler)
    signal(SIGUSR2, market_handler)

    externalProcess = Process(target=external, args=(getpid(),exitFlag))
    externalProcess.start()

    # launch nMarketThreads queues and threads associated
#    queueToSon = [ Queue() for k in range(nMarketThreads)]
#    marketThreads = [ Thread(target=marketThread, args=(marketKey+k, queueToSon[k],)) for k in range(nMarketThreads)]
#    for thread in marketThreads:
#        thread.start()

    queueToHome = MessageQueue(marketKey, IPC_CREAT)
    # if queue was not properly deleted, it's still there and we have to do it ourselves
    if queueToHome.current_messages > 0:
        queueToHome.remove()
        queueToHome = MessageQueue(marketKey, IPC_CREAT)

    print("[%d] Market (main) : messageQueue created" % getpid())
    buying = []
    selling = []

    price = -1
    gamma = 0.78                            # long-term attenuation coefficient
    alpha = [ -0.052, 0.075, 0.23, -0.07]   # modulating coefficient for internal factors: Temperature, Rain, bought, sold
    internalEvents = [ 0, 0, 0 , 0]
    beta = [ -7, 30 ]                       # modulating coefficient for external factors: SIGUSR1, SIGUSR2

    print("[%d] Market (main) : all external processes launched" % getpid())
    while not exitFlag.value:
        sleep(2)
        try:
            # on reçoit une seule valeur, il faut pouvoir recevoir plusieurs valeurs
            message, _ = queueToHome.receive(block=False, type=1)
            pid, quantity = message.decode().split(':')
            buying.append(int(quantity))
            message, _ = queueToHome.receive(block=False, type=2)
            pid, quantity = message.decode().split(':')
            selling.append(int(quantity))
        except (NotAttachedError, BusyError):
            pass
        print("[%d] On the market we have external = %s \tweather = [ %.2f, %.2f ]\tbuying = %s\tselling = %s" % (getpid(), externalEvents, weatherAttributes[0], weatherAttributes[1], buying, selling))
        internalEvents = [ weatherAttributes[0], weatherAttributes[1], sum(buying), sum(selling) ]
        if price == -1:
            print("[%d] Initiating energy price" % getpid())
            price = sum([alpha[k]*internalEvents[k] for k in range(len(internalEvents))]) + sum([beta[k]*externalEvents[k] for k in range(len(externalEvents))])
        else :
            price = gamma*price +  sum([alpha[k]*internalEvents[k] for k in range(len(internalEvents))]) + sum([beta[k]*externalEvents[k] for k in range(len(externalEvents))])
        print("[%d] Energy price = %.2f €/kWh" % (getpid(), price))
        externalEvents = [0, 0]
        buying = selling = []

    queueToHome.remove()
    print("[%d] Market (main) : messageQueue removed" % getpid())
    print("[%d] Market (main) : Exit" % getpid())


# def marketThread(marketKey, queueToMother):
#     print("[%d] Market (%s): Init" % (getpid(), current_thread().name))
#     #queueToHome = MessageQueue(marketKey, IPC_CREAT)
#     #try:
#     #    message, t = queueToHome.receive(block=False)
#     #    value = message.decode()
#     #    value = int(value)
#     #except NotAttachedError as e:
#     #    value = -1
#     while True:
#         sleep(2)
#         value = -1
#         queueToMother.put(value)
#         # print("[%d] Market (%s): value -1 put in queue" % (getpid(), current_thread().name))
#     # after some time
#     # queueToHome.remove()

if __name__ == '__main__':
    print("[%d] Main process : Init" % getpid())
    # creating shared memory
    weatherAttributes = Array('d', range(2))

    # proper exit system : shared-variable exitFlag between processes
    # and we use a closure to pass exitFlag to global_handler
    exitFlag = Value('i', 0)
    def global_handler(sig, frame):
        if sig == SIGINT:
            exitFlag.value = 1
    signal(SIGINT, global_handler)

    marketProcess = Process(target=market, args=(weatherAttributes,exitFlag,))
    weatherProcess = Process(target=weather, args=(weatherAttributes,exitFlag,))

    marketProcess.start()
    weatherProcess.start()
    print("[%d] Main process : Exit" % getpid())
