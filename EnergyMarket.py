"""EnergyMarket.py

A multi-independant-processes simulation about the energy market."""

from multiprocessing import Array, Process
from signal import signal, SIGUSR1, SIGUSR2
from sysv_ipc import IPC_CREAT, MessageQueue
from os import kill, getpid
from random import random
from time import sleep
from queue import Queue

marketKey = 221
nMarketThreads = 5
externalEvents = [0, 0]

def weather(weatherAttributes):
    print("[%d] Weather : Init" % getpid())
    type(weatherAttributes)
    weatherAttributes[0] = 0
    weatherAttributes[1] = 0
    while True:
        sleep(4)
        weatherAttributes[0] = 20 + 5*random()      # Temperature
        weatherAttributes[1] = 10 + 30*random()     # Rain
        print("[%d] Weather update : T = %.2f and R = %.2f" % (getpid(), weatherAttributes[0], weatherAttributes[1]))

def external(marketPID):
    print("[%d] External : Init" % getpid())
    while True:
        sleep(6)
        if int(2*random()):
            signal(marketPID, SIGUSR1)
            print("[%d] External event : SIGUSR1 sent." % getpid())
        if int(2*random()):
            signal(marketPID, SIGUSR2)
            print("[%d] External event : SIGUSR2 sent." % getpid())

def market_handler(sig, frame):
    global externalEvents
    if sig == SIGUSR1:
        externalEvents[0] = 1
    elif sig == SIGUSR2:
        externalEvents[1] = 1

def market(weatherAttributes):
    print("[%d] Market (main) : Init" % getpid())
    global marketKey, nMarketThreads, externalEvents

    # launch external process
    print("[%d] Market (main) : launching external process" % getpid())
    externalProcess = Process(target=external, args=(getpid(),))
    externalProcess.start()
    signal(SIGUSR1, market_handler)
    signal(SIGUSR2, market_handler)

    # weatherAttributes is already set and ready to use
    # externalEvents is already set and ready to use

    # launch nMarketThreads queues and threads associated
    queueToSon = [ Queue() for k in range(nMarketThreads)]
    marketThreads = [ Thread(target=marketThread, args=(marketKey+k, queueToSon[k])) for k in range(nMarketThreads)]
    homesValues = [ 0 for k in range(nMarketThreads) ]

    while True:
        sleep(2)
        homesValues = [ queueToSon(k).get for k in range(nMarketThreads) ]
        print("[%d] On the market we have e1 = %d\te2 = %d\tT = %.2f \tR = %.2f" % (getpid(), externalEvents[0], externalEvents[1], weatherAttributes[0], weatherAttributes[1]))

def marketThread(marketKey, queueToMother):
    queueToHome = MessageQueue(marketKey, IPC_CREAT)
    try:
        message, t = queueToHome.receive(block=False)
        value = message.decode()
        value = int(value)
    except NotAttachedError as e:
        value = -1
    queueToMother.put(value)
    # after some time
    queueToHome.remove()

if __name__ == '__main__':
    print("[%d] Main process : Init" % getpid())
    # creating shared memory
    weatherAttributes = Array('d', range(2))

    marketProcess = Process(target=market, args=(weatherAttributes,))
    weatherProcess = Process(target=weather, args=(weatherAttributes,))

    marketProcess.start()
    weatherProcess.start()
    print("[%d] Main process : Done" % getpid())