#!/usr/bin/python3


import os
import json
import subprocess as sp
from time import sleep
from dotenv import load_dotenv
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib import animation


class Config():
    def __init__(self):
        self.ip_address = None
        self.other = None
        self.force_args = None

    def build_cmd(self):
        cmd = ["iperf3"]

        if self.ip_address:
            cmd.append("-c")
            cmd.append(self.ip_address)
        else:
            raise ValueError("Expected ip_address")

        if self.other:
            cmd += self.other.split()
        if self.force_args:
            cmd += self.force_args.split()

        return cmd


def run_cmd(cmd):
    keyboard_interrupted = False

    print(f"Running cmd: '{" ".join(cmd)}'")
    pr = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    try:    
        pr.wait()
    except KeyboardInterrupt:
        pr.kill()
        keyboard_interrupted = True
    
    stderr = pr.stderr.read().decode()
    stdout = pr.stdout.read().decode()
    
    if pr.returncode != 0 and not keyboard_interrupted:
        j = json.loads(stdout)
        raise ValueError("Running cmd failed\n" +
                         f"stdout: {j['error']}\n" +
                         f"stderr: {stderr}")
    
    return stdout, stderr, keyboard_interrupted


def iperf_run():
    cfg = Config()

    cfg.force_args = '-k 1 -J'
    cfg.ip_address = os.getenv('IPERF_IP_ADDRESS')
    cfg.other = os.getenv('IPERF_OTHER')

    cmd = cfg.build_cmd()
    stdout, stderr, interrupted = run_cmd(cmd)

    return stdout, stderr, interrupted

def init(lines, dates, loss,
         rate_s, rate_r):
    for line in lines:
        line.set_data([], [])

def update(frame, lines, dates,
           loss, rate_s, rate_r):
    stdout, stderr = "", ""

    try:
        stdout, stderr, interrupted = iperf_run()
    except ValueError as e:
        print(f"[ERROR]: {e}")
        os._exit(1)

    data = json.loads(stdout)    
    dates.append(datetime.datetime.now())
    loss.append(int(data['end']['sum_sent']['bytes']) -
                int(data['end']['sum_received']['bytes']))
    rate_s.append(int(data['end']['streams'][0]['sender']['bits_per_second']))
    rate_r.append(int(data['end']['streams'][0]['receiver']['bits_per_second']))
 
    x = matplotlib.dates.date2num(dates)

    lines[0].set_data(x, loss)
    lines[1].set_data(x, rate_s)
    lines[2].set_data(x, rate_r)

    return lines


def main():
    load_dotenv()

    fig = plt.figure()
    ax1 = plt.axes(xlim=(-108, -104), ylim=(31,34))

    lines, dates, loss, rate_s, rate_r = [], [], [], [], []
    for i in range(3):
        lines.append(ax1.plot([],[],lw=2)[0])
    anim = animation.FuncAnimation(fig, update,
                                   fargs=(lines, dates, loss, rate_s,
                                          rate_r))
    plt.show()    


if __name__ == "__main__":
    main()
