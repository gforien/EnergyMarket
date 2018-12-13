"""EnergyMarket.py

A multi-independant-processes simulation about the energy market."""

from multiprocessing import Array, Process
from signal import signal, SIGUSR1, SIGUSR2
from sysv_ipc import IPC_CREAT, MessageQueue, NotAttachedError
from os import kill, getpid
from random import random
from time import sleep
from queue import Queue, Empty
from threading import Thread, current_thread

marketKey = 221
nMarketThreads = 5
externalEvents = [0, 0]

def weather(weatherAttributes):
    print("[%d] Weather : Init" % getpid())
    type(weatherAttributes)
    weatherAttributes[0] = 0
    weatherAttributes[1] = 0
    while True:
        sleep(6)
        weatherAttributes[0] = 20 + 5*random()      # Temperature
        weatherAttributes[1] = 10 + 30*random()     # Rain
        print("[%d] Weather update : T = %.2f and R = %.2f" % (getpid(), weatherAttributes[0], weatherAttributes[1]))

def external(marketPID):
    print("[%d] External : Init" % getpid())
    while True:
        sleep(8)
        if int(2*random()):
            kill(marketPID, SIGUSR1)
            print("[%d] External event : SIGUSR1 sent." % getpid())
        if int(2*random()):
            kill(marketPID, SIGUSR2)
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
    externalProcess = Process(target=external, args=(getpid(),))
    externalProcess.start()
    signal(SIGUSR1, market_handler)
    signal(SIGUSR2, market_handler)
    # weatherAttributes is already set and ready to use
    # externalEvents is already set and ready to use

    # launch nMarketThreads queues and threads associated
    queueToSon = [ Queue() for k in range(nMarketThreads)]
    marketThreads = [ Thread(target=marketThread, args=(marketKey+k, queueToSon[k],)) for k in range(nMarketThreads)]
    for thread in marketThreads:
        thread.start()
    homesValues = [ 0 for k in range(nMarketThreads) ]

    print("[%d] Market (main) : all external processes launched" % getpid())
    while True:
        sleep(2)
        for i in range(nMarketThreads):
            try:
                homesValues[i] = queueToSon[i].get(block=False)
            except Empty:
                homesValues[i] = -1
        print("[%d] On the market we have external = %s \tweather = [ %.2f, %.2f ]\thomes = %s" % (getpid(), externalEvents, weatherAttributes[0], weatherAttributes[1], homesValues))
        externalEvents = [0, 0]

def marketThread(marketKey, queueToMother):
    print("[%d] Market (%s): Init" % (getpid(), current_thread().name))
    #queueToHome = MessageQueue(marketKey, IPC_CREAT)
    #try:
    #    message, t = queueToHome.receive(block=False)
    #    value = message.decode()
    #    value = int(value)
    #except NotAttachedError as e:
    #    value = -1
    while True:
        sleep(2)
        value = -1
        queueToMother.put(value)
        # print("[%d] Market (%s): value -1 put in queue" % (getpid(), current_thread().name))
    # after some time
    # queueToHome.remove()

if __name__ == '__main__':
    print("[%d] Main process : Init" % getpid())
    # creating shared memory
    weatherAttributes = Array('d', range(2))

    marketProcess = Process(target=market, args=(weatherAttributes,))
    weatherProcess = Process(target=weather, args=(weatherAttributes,))

    marketProcess.start()
    weatherProcess.start()
    print("[%d] Main process : Done" % getpid())
