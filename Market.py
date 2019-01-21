"""EnergyMarket.py

A multi-independant-processes simulation about the energy market."""

from matplotlib import pyplot as plt
from matplotlib import animation
from multiprocessing import Value, Array, Process
from threading import Lock, Thread, current_thread
from signal import signal, SIGINT, SIGUSR1, SIGUSR2
from sysv_ipc import IPC_CREAT, MessageQueue, NotAttachedError, BusyError
from os import kill, getpid
from random import random
from time import sleep
from queue import Queue, Empty

marketKey = 221
period = 2

def weather(weatherAttributes, exitFlag):
    print("[%d] Weather : Init" % getpid())
    type(weatherAttributes)
    weatherAttributes[0] = 0
    weatherAttributes[1] = 0
    while not exitFlag.value:
        sleep(6)
        weatherAttributes[0] = 20 + 5*random()      # Temperature
        weatherAttributes[1] = 10 + 30*random()     # Rain
        # print("[%d] Weather update : T = %.2f and R = %.2f" % (getpid(), weatherAttributes[0], weatherAttributes[1]))
    print("[%d] Weather : Exit" % getpid())


def external(marketPID, exitFlag):
    print("[%d] External : Init" % getpid())
    while not exitFlag.value:
        sleep(8)
        if int(2*random()):
            kill(marketPID, SIGUSR1)
            # print("[%d] External event : SIGUSR1 sent." % getpid())
        if int(2*random()):
            kill(marketPID, SIGUSR2)
            # print("[%d] External event : SIGUSR2 sent." % getpid())
    print("[%d] External : Exit" % getpid())


def marketThread(message, array, lock):
    pid, quantity = message.decode().split(':')
    with lock:
        array.append(int(quantity))
    # print("[%d] Market_request (%s) : value added to array" % (getpid(), current_thread().name))


def market(weatherAttributes, prices, exitFlag):
    print("[%d] Market (main) : Init" % getpid())

    # create handler with a closure, reroute signals, and launch external process
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

    # create lock that will be passed to many threads to treat each request
    sharedLock = Lock()

    # create message queues to Homes
    queueToHome = MessageQueue(marketKey, IPC_CREAT)
    # if queue was not properly deleted, it's still there and we have to do it ourselves
    if queueToHome.current_messages > 0:
        queueToHome.remove()
        queueToHome = MessageQueue(marketKey, IPC_CREAT)

    print("[%d] Market (main) : messageQueue created" % getpid())
    buying = []
    selling = []

    idx = 0
    price = -1
    gamma = 0.90                            # long-term attenuation coefficient
    alpha = [ -0.052, 0.075, 0.23, -0.07]   # modulating coefficient for internal factors: Temperature, Rain, bought, sold
    internalEvents = [ 0, 0, 0 , 0]
    beta = [ -7, 30 ]                       # modulating coefficient for external factors: SIGUSR1, SIGUSR2

    # print("[%d] Market (main) : all external processes launched" % getpid())
    while not exitFlag.value:
        sleep(period)
        # upon receiving a buying message, we launch a thread
        try:
            while queueToHome.current_messages > 0:
                message, _ = queueToHome.receive(block=False, type=1)
                (Thread(target=marketThread, args=(message, buying, sharedLock, ))).start()
        except (NotAttachedError, BusyError):
            pass
        # upon receiving a selling message, we launch a thread
        try:
            while queueToHome.current_messages > 0:
                message, _ = queueToHome.receive(block=False, type=2)
                (Thread(target=marketThread, args=(message, selling, sharedLock, ))).start()
        except (NotAttachedError, BusyError):
            pass

        print("[%d] external = %s \tweather = [ %.2f, %.2f ]\tbuying = %s\tselling = %s" % (getpid(), externalEvents, weatherAttributes[0], weatherAttributes[1], buying, selling))
        internalEvents = [ weatherAttributes[0], weatherAttributes[1], sum(buying), sum(selling) ]
        if price == -1:
            print("[%d] Initiating energy price" % getpid())
            price = sum([alpha[k]*internalEvents[k] for k in range(len(internalEvents))]) + sum([beta[k]*externalEvents[k] for k in range(len(externalEvents))])
        else :
            price = gamma*price +  sum([alpha[k]*internalEvents[k] for k in range(len(internalEvents))]) + sum([beta[k]*externalEvents[k] for k in range(len(externalEvents))])
        if price <= 0:
            price = 0.05
        prices[idx] = price
        idx = (idx+1)%500
        #print("In market : "+str(prices[0:20]))
        print("[%d] Energy price = %.2f €/kWh" % (getpid(), price))
        externalEvents = [0, 0]
        buying = []
        selling = []

    queueToHome.remove()
    print("[%d] Market (main) : messageQueue removed" % getpid())
    print("[%d] Market (main) : Exit" % getpid())


offset = 0
limit = 0
MAX_LIMIT = 20
def gui(prices):
    fig = plt.figure()
    axe = plt.axes(xlim=(0, 20), ylim=(-1,100))
    plt.xlabel("Time (in days)")
    plt.ylabel("Price (in €/kWh)")
    line, = axe.plot([], [], lw=2)

# initialization function: plot the background of each frame
    def gui_init():
        global offset, limit
        line.set_data([], [])
        return line,

# animation function.  This is called sequentially
    def gui_animate(i):
        global offset, limit
        while prices[limit] != -1 and limit < MAX_LIMIT:
            limit+=1
        print("In gui : "+str(prices[offset:limit]))
        line.set_data(range(limit), prices[offset:limit])
        if limit == MAX_LIMIT:
            offset = (offset+1)%500
            limit = (limit+1)%500
            axe.set_xlim(offset, limit)
        return line,

    # call the animator.  blit=True means only re-draw the parts that have changed.
    anim = animation.FuncAnimation(fig, gui_animate, init_func=gui_init, frames=1, interval=period*1000, blit=True)
    plt.show()

if __name__ == '__main__':
    print("[%d] Main process : Init" % getpid())
    # creating shared memory
    weatherAttributes = Array('d', range(2))
    prices = Array('f', [-1 for k in range(500)])

    # proper exit system : shared-variable exitFlag between processes
    # and we use a closure to pass exitFlag to global_handler
    exitFlag = Value('i', 0)
    def global_handler(sig, frame):
        if sig == SIGINT:
            exitFlag.value = 1
    signal(SIGINT, global_handler)

    marketProcess = Process(target=market, args=(weatherAttributes, prices, exitFlag,))
    weatherProcess = Process(target=weather, args=(weatherAttributes,exitFlag,))

    marketProcess.start()
    weatherProcess.start()

    gui(prices)
    print("[%d] Main process : Exit" % getpid())

    # GUI
    #fenetre = Tk()
    #fenetre.title('Market.py')
    #canvas = Canvas(fenetre, width=800, height=800, background='light gray')
    #ligne1 = canvas.create_line(75, 0, 75, 120)
    #ligne2 = canvas.create_line(0, 60, 150, 60)
    #canvas.pack()
    #fenetre.mainloop()
