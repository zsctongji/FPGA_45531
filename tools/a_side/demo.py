"""One-window localhost demonstration. All generated messages are SYNTHETIC."""
import argparse
import threading
import time
from receiver import run
from send_demo import send

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True)
    p.add_argument('--seconds',type=float,default=0)
    p.add_argument('--port',type=int,default=39003)
    p.add_argument('--web-port',type=int,default=39004)
    a=p.parse_args()
    def sender():
        time.sleep(.5)
        send(port=a.port)
    threading.Thread(target=sender,daemon=True).start()
    run(port=a.port,web_port=a.web_port,output=a.output,seconds=a.seconds)
