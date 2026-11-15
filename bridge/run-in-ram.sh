#!/bin/bash
# Roda a ponte BLE -> MQTT inteira na memória RAM (/dev/shm), sem gravar no cartão SD.
# Uso provisório enquanto o cartão está com defeito: tudo some no reboot; basta rodar de novo.
#   curl -fsSL https://raw.githubusercontent.com/engperini/anernmodbus/main/bridge/run-in-ram.sh | bash -s -- <DTU_ID> <MAC_BLE>
set -euo pipefail
DTU="${1:?informe o DTU ID}"; MAC="${2:?informe o endereço BLE}"
W=/dev/shm/anern
mkdir -p "$W"; cd "$W"

echo ">> Baixando a ponte do GitHub para a RAM..."
curl -fsSL https://codeload.github.com/engperini/anernmodbus/tar.gz/main \
  | tar xz --strip-components=2 anernmodbus-main/bridge

echo ">> Instalando dependências na RAM..."
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q --no-cache-dir "bleak>=1,<2" "cryptography>=45,<47" "paho-mqtt>=2,<3"

printf 'RWB1_DTU_ID=%s\nRWB1_BLE_ADDRESS=%s\n' "$DTU" "$MAC" > rwb1.env
chmod 600 rwb1.env

echo ">> Parando a ponte antiga do cartão (se existir)..."
systemctl --user stop rwb1-ble 2>/dev/null || true
sudo systemctl stop rwb1-ble 2>/dev/null || true
pkill -f "$W/.venv/bin/python bridge.py" 2>/dev/null || true

echo ">> Conferindo o MQTT local..."
systemctl is-active --quiet mosquitto || sudo systemctl start mosquitto || echo "!! Mosquitto não está rodando"

set -a; . ./rwb1.env; set +a
echo ">> Leitura de teste..."
.venv/bin/python bridge.py --once

nohup .venv/bin/python bridge.py --interval 30 > bridge.log 2>&1 &
echo ">> Ponte rodando (PID $!). Log: tail -f $W/bridge.log"
