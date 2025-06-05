#!/bin/bash

SYSTEMD_DIR="/etc/systemd"

if ! [ -d $SYSTEMD_DIR ]; then
  echo "Systemd directory does exist."
  exit 19
fi

if ! $(systemctl --version); then
  exit 1
fi

if [ -f "${SYSTEMD_DIR}/system/iperf3-monitor.service" ]; then
  echo "Iperf3 service is already exist."
  exit 1
fi

touch "${SYSTEMD_DIR}/system/iperf3-monitor.service" 
echo "[Unit]
Description=Iperf-monitor
After=default.target

[Service]
Restart=always
ExecStart=/usr/bin/iperf3 -s -p 5001 -i 10

[Install]
WantedBy=default.target" > "${SYSTEMD_DIR}/system/iperf3-monitor.service"

systemctl enable iperf3-monitor.service
systemctl start iperf3-monitor.service
