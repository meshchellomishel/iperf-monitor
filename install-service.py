#!/usr/bin/python3


import os
import subprocess as sp
from dotenv import load_dotenv


class SshCmd():
    def __init__(self, **kwargs):
        self.user = kwargs.get('user', None)
        self.host = kwargs.get('host', None)
        self.hostname = kwargs.get('hostname', None)
        self.params = kwargs.get('params', None)

    def build_cmd(self):
        if self.user and self.host:
            return ['ssh', f"{self.user}@{self.host}", self.params]

        if self.hostname:
            return ['ssh', self.hostname, self.params]

        raise ValueError("Not enouth env varibles" +
                         "for ssh connection")

    def __str__(self):
        return f"'{self.user}' '{self.host}' '{self.hostname}' '{self.params}'"




def build_install_script(iperf_cmd):
    return '''
echo "[Unit]
Description=Iperf-monitor
After=default.target

[Service]
Restart=always
ExecStart=/usr/bin/''' + iperf_cmd + '''

[Install]
WantedBy=default.target" > "/etc/systemd/system/iperf3-monitor.service"

systemctl enable iperf3-monitor.service
systemctl start iperf3-monitor.service
    '''


def run_cmd(cmd):
    print('--> cmd: ', " ".join(cmd))

    pr = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    try:    
        pr.wait()
    except KeyboardInterrupt:
        pr.kill()
        os._exit(1)

    stderr = pr.stderr.read().decode()
    stdout = pr.stdout.read().decode()
   
    print(f"<-- stdout: '{stdout}'")
    print(f"<-- stderr: '{stderr}'")

    if pr.returncode != 0:
        raise ValueError("Running cmd failed\n" +
                         f"stdout: {stdout}\n" +
                         f"stderr: {stderr}")
    
    return stdout, stderr


def main():
    load_dotenv()
    
    user = os.getenv('SSH_USER')
    host = os.getenv('SSH_HOST')
    hostname = os.getenv('SSH_HOSTNAME')
    envparams = os.getenv('SSH_PARAMS') or ''

    check_cmds = [
        ("[ ! -d /etc/systemd ]",
         "Cannot find systemd directory"),
        ("[ -f \"/etc/systemd/system/iperf3-monitor.service\" ]",
         "Service is already exist."),
        ("! (which systemctl &>/dev/null)",
         "Systemctl command does not exist.")
    ]

    print("Check if we could install service")
    for check_cmd in check_cmds:
        params = envparams + check_cmd[0] + "; echo $?"
        cmd = SshCmd(user=user, host=host,
                     hostname=hostname, params=params)
        cmd = cmd.build_cmd()
        out, err = run_cmd(cmd)
        if out != '1\n':
            raise ValueError(f"Failed to install service: {check_cmd[1]}")
    
    print("Install service")
    iperf_cmd = 'iperf3 -s -i 59 '
    if port := os.getenv('IPERF_PORT'):
        iperf_cmd += '-p ' + port

    params = envparams + build_install_script(iperf_cmd)
    cmd = SshCmd(user=user, host=host,
                 hostname=hostname, params=params)
    cmd = cmd.build_cmd()
    out, err = run_cmd(cmd)


if __name__ == "__main__":
    main()
