#!/usr/bin/python3


import os
import json
import subprocess as sp
from time import sleep
from dotenv import load_dotenv
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates


class IperfCmd():
    def __init__(self):
        self.ip_address = None
        self.port = None
        self.other = None
        self.interval = None
        self.force_args = None

    def build_cmd(self):
        cmd = ["iperf3"]

        if self.ip_address:
            cmd.append("-c")
            cmd.append(self.ip_address)
        else:
            raise ValueError("Expected ip_address")

        if self.port:
            cmd.append("-p")
            cmd.append(self.port)

        if self.interval:
            interval = int(self.interval)
            if interval < 0.1 or interval > 60:
                raise ValueError(f"Wrong interval: {self.interval}" +
                                 "must be between 0.1 and 60 seconds")
            cmd.append("-i")
            cmd.append(self.interval)
            cmd.append("-t")
            cmd.append(self.interval)

        if self.other:
            cmd += self.other.split()
        if self.force_args:
            cmd += self.force_args.split()

        return cmd


class ProgConfig():
    def __init__(self, outdatafile: str='data.csv',
                 outgraphimage: str='test.png',
                 mavalue: int=0, timeout: int=1):
        self.outdatafile = outdatafile if outdatafile else 'data.csv'
        self.outgraphimage = outgraphimage if outgraphimage else 'test.png'
        self.mavalue = mavalue if mavalue else 0
        self.timeout = timeout if timeout else 1


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
    cfg = IperfCmd()

    cfg.force_args = '-J'
    cfg.ip_address = os.getenv('IPERF_IP_ADDRESS')
    cfg.port = os.getenv('IPERF_PORT')
    cfg.other = os.getenv('IPERF_OTHER')
    cfg.interval = os.getenv('IPERF_INTERVAL')

    cmd = cfg.build_cmd()
    stdout, stderr, interrupted = run_cmd(cmd)

    return stdout, stderr, interrupted

def bits2mbits(bits):
    return bits/1024/1024


def loaddatafromfile(cfg):
    dates, loss, rate_s, rate_r = [], [], [], []

    print('Loading data from file...')
    with open(cfg.outdatafile, "r") as file:
        for line in file.readlines():
            s = line.split(';')
            print(s)
            dates.append(datetime.datetime.fromisoformat(s[0]))
            loss.append(float(s[1]))
            rate_s.append(float(s[2]))
            rate_r.append(float(s[3]))

    return dates, loss, rate_s, rate_r


def append_data(cfg: ProgConfig, data: tuple):
    with open(cfg.outdatafile, "a+") as file:
        s = ''
        for i in range(len(data) - 1):
            s += str(data[i]) + ';'
        s += str(data[len(data) - 1])
        print(f"append: '{s}'")
        file.write(s + '\n')

def iperf_loop(cfg):
    errors = 0
    dates, loss, rate_s, rate_r = [], [], [], []
    
    try:
        while True:
            need_exit = False
            interrupted = False
            error_occured = False
            stdout, stderr = "", ""

            try:
                stdout, stderr, interrupted = iperf_run()
                errors = 0
            except KeyboardInterrupt:
                need_exit = True
            except ValueError as e:
                print(f"[ERROR]: {e}")
                error_occured = True
                errors += 1

            if interrupted or need_exit or errors == 10:
                return dates, loss, rate_s, rate_r

            now = datetime.datetime.now()
            # now = now.strftime('%H:%M:%S')
            closs, crate_s, crate_r = 0, 0, 0
            if not error_occured:
                data = json.loads(stdout)    
                closs = bits2mbits(int(data['end']['sum_sent']['bytes']) -
                                   int(data['end']['sum_received']['bytes']))
                stream = data['end']['streams'][0]
                crate_s = bits2mbits(int(stream['sender']['bits_per_second']))
                crate_r = bits2mbits(int(stream['receiver']['bits_per_second']))

            dates.append(now)
            loss.append(closs)
            rate_s.append(crate_s)
            rate_r.append(crate_r)
            append_data(cfg, (now, closs, crate_s, crate_r))

            sleep(cfg.timeout)
    except KeyboardInterrupt:
        return dates, loss, rate_s, rate_r


def loadprogconfig():
    outdatafile = os.getenv('OUTPUT_DB_FILENAME')
    outputgraph = os.getenv('OUTPUT_GRAPH')
    mavalue = os.getenv('MA_VALUE')
    timeout = os.getenv('RESTART_TIMEOUT')

    print(mavalue)
    return ProgConfig(outdatafile=outdatafile, outgraphimage=outputgraph,
                      mavalue=mavalue, timeout=timeout)


def plotimage(outname, dates, loss, rate_s, rate_r):
    print(dates)
    print(loss)
    print(rate_s)
    print(rate_r)

    print('plotting...')
    plt.figure(figsize=(19.20, 10.80), dpi=100)
    plt.plot(dates, loss, label='loss', color='red')
    plt.plot(dates, rate_s, label='send rate', color='blue')
    plt.plot(dates, rate_r, label='recv rate', color='pink')
    plt.legend(loc="upper left")
    plt.grid()
    plt.savefig(outname)


def main():
    load_dotenv()
    cfg = loadprogconfig()

    dates, loss, rate_s, rate_r = iperf_loop(cfg)
    plotimage('prev.png', dates, loss, rate_s, rate_r)
    dates, loss, rate_s, rate_r = loaddatafromfile(cfg)
    plotimage(cfg.outgraphimage, dates, loss, rate_s, rate_r)


if __name__ == "__main__":
    main()
