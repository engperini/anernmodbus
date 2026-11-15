#!/usr/bin/env bash
# Installs the Anern RWB1 BLE -> MQTT bridge as a persistent service.
# Tested on Raspberry Pi OS (Bookworm/Trixie). Run it as a normal user (not root).
#
#   ./install.sh                          # asks for whatever is missing
#   ./install.sh --dtu-id 123... --mqtt-host 192.168.1.10 --mqtt-user mqtt --mqtt-password secret
#   ./install.sh --uninstall
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DIR/rwb1.env"
VENV="$DIR/.venv"
PY="$VENV/bin/python"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT="$UNIT_DIR/rwb1-ble.service"

DTU_ID="" ADDRESS="" MQTT_HOST="" MQTT_PORT="" MQTT_USER="" MQTT_PASSWORD="" INTERVAL=""
NO_SERVICE=0 NO_TEST=0

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m[warning]\033[0m %s\n' "$*"; }
die()  { printf '\033[31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'
  cat <<EOF

Options:
  --dtu-id ID          dongle DTU ID (vendor app: Device PN / Device Name)
  --address MAC        dongle BLE address (empty = scan for SSL_... nearby)
  --mqtt-host HOST     MQTT broker (default 127.0.0.1)
  --mqtt-port PORT     default 1883
  --mqtt-user USER     if the broker needs a login (e.g. the HA OS Mosquitto add-on)
  --mqtt-password PASS
  --interval SECONDS   time between reads (default 30)
  --no-service         prepare everything but do not install the service
  --no-test            skip the test read
  --uninstall          stop and remove the service (keeps rwb1.env and .venv)
EOF
}

uninstall() {
  systemctl --user disable --now rwb1-ble.service 2>/dev/null || true
  rm -f "$UNIT"
  systemctl --user daemon-reload || true
  echo "Service rwb1-ble removed. To delete everything: rm -rf \"$VENV\" \"$ENV_FILE\""
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dtu-id) DTU_ID="$2"; shift 2 ;;
    --address) ADDRESS="$2"; shift 2 ;;
    --mqtt-host) MQTT_HOST="$2"; shift 2 ;;
    --mqtt-port) MQTT_PORT="$2"; shift 2 ;;
    --mqtt-user) MQTT_USER="$2"; shift 2 ;;
    --mqtt-password) MQTT_PASSWORD="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    --no-service) NO_SERVICE=1; shift ;;
    --no-test) NO_TEST=1; shift ;;
    --uninstall) uninstall ;;
    -h|--help) usage; exit 0 ;;
    *) usage; die "unknown option: $1" ;;
  esac
done

[[ $EUID -ne 0 ]] || die "run as a normal user (no sudo); the script asks for sudo only when needed"

# ------------------------------------------------------------------ 1. system
say "1/6 Checking system packages"
missing=()
command -v python3 >/dev/null || missing+=(python3)
python3 -c "import venv, ensurepip" 2>/dev/null || missing+=(python3-venv)
command -v bluetoothctl >/dev/null || missing+=(bluez)
if ((${#missing[@]})); then
  echo "Missing: ${missing[*]}"
  sudo apt-get update && sudo apt-get install -y "${missing[@]}"
fi
systemctl is-active --quiet bluetooth || sudo systemctl enable --now bluetooth

# ------------------------------------------------------------------ 2. venv
say "2/6 Python environment (.venv)"
[[ -x "$PY" ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$DIR/requirements.txt"
"$PY" -c 'import bleak, paho.mqtt, cryptography' && echo "ok"

# ------------------------------------------------------------------ 3. rwb1.env
say "3/6 Configuration (rwb1.env)"
get() { [[ -f "$ENV_FILE" ]] && grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- || true; }
DTU_ID="${DTU_ID:-$(get RWB1_DTU_ID)}"
ADDRESS="${ADDRESS:-$(get RWB1_BLE_ADDRESS)}"
MQTT_HOST="${MQTT_HOST:-$(get MQTT_HOST)}"; MQTT_HOST="${MQTT_HOST:-127.0.0.1}"
MQTT_PORT="${MQTT_PORT:-$(get MQTT_PORT)}"; MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USER="${MQTT_USER:-$(get MQTT_USER)}"
MQTT_PASSWORD="${MQTT_PASSWORD:-$(get MQTT_PASSWORD)}"
INTERVAL="${INTERVAL:-$(get RWB1_INTERVAL)}"; INTERVAL="${INTERVAL:-30}"

if [[ -z "$DTU_ID" ]]; then
  [[ -t 0 ]] || die "pass --dtu-id (vendor app: Device PN / Device Name)"
  read -rp "Dongle DTU ID (vendor app: Device PN / Device Name): " DTU_ID
fi
[[ -n "$DTU_ID" ]] || die "the DTU ID is required"

if [[ -z "$ADDRESS" ]]; then
  echo "Scanning for the dongle over Bluetooth (10 s)... close the phone app if it is connected."
  mapfile -t found < <(RWB1_DTU_ID="$DTU_ID" "$PY" "$DIR/bridge.py" --scan | grep -E '^([0-9A-F]{2}:){5}[0-9A-F]{2}' || true)
  if ((${#found[@]} == 1)); then
    ADDRESS="${found[0]%% *}"; echo "found: ${found[0]}"
  elif ((${#found[@]} > 1)); then
    printf '  %s\n' "${found[@]}"
    [[ -t 0 ]] || die "several dongles found; pass --address"
    read -rp "Address of your dongle: " ADDRESS
  else
    warn "no SSL_ dongle found right now; the bridge will scan by itself every time it starts"
  fi
fi

umask 077
cat > "$ENV_FILE" <<EOF
# RWB1 bridge (written by install.sh on $(date '+%F %T')). Do not publish this file.
RWB1_DTU_ID=$DTU_ID
RWB1_BLE_ADDRESS=$ADDRESS
RWB1_INTERVAL=$INTERVAL
MQTT_HOST=$MQTT_HOST
MQTT_PORT=$MQTT_PORT
MQTT_USER=$MQTT_USER
MQTT_PASSWORD=$MQTT_PASSWORD
EOF
umask 022
echo "saved to $ENV_FILE (mode 600)"

# ------------------------------------------------------------------ 4. tests
say "4/6 Unit tests"
(cd "$DIR" && "$PY" -m unittest -q 2>&1 | tail -1)

# ------------------------------------------------------------------ 5. test read
if ((NO_TEST == 0)); then
  say "5/6 Test read (BLE -> MQTT)"
  if systemctl --user is-active --quiet rwb1-ble.service; then
    systemctl --user stop rwb1-ble.service   # only one BLE connection at a time
    sleep 5
  fi
  (cd "$DIR" && timeout 120 "$PY" bridge.py --once 2>&1 | grep -E "read OK|failed|Error" | tail -3) || true
else
  say "5/6 Test read skipped"
fi

# ------------------------------------------------------------------ 6. service
if ((NO_SERVICE == 1)); then
  say "6/6 Service not installed (--no-service). To run by hand: $PY $DIR/bridge.py"
  exit 0
fi
say "6/6 Persistent service (systemd user unit)"
mkdir -p "$UNIT_DIR"
cat > "$UNIT" <<EOF
[Unit]
Description=Anern RWB1 BLE <-> MQTT bridge (Home Assistant)
After=network-online.target bluetooth.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$DIR
EnvironmentFile=$ENV_FILE
ExecStart=$PY $DIR/bridge.py --interval \${RWB1_INTERVAL}
Restart=always
RestartSec=15
NoNewPrivileges=yes

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now rwb1-ble.service
# Without lingering a user service only runs while someone is logged in; with it, it starts at boot.
loginctl show-user "$USER" -p Linger 2>/dev/null | grep -q yes || sudo loginctl enable-linger "$USER"
sleep 3
systemctl --user --no-pager --lines=0 status rwb1-ble.service | head -3 || true

ID=$(printf '%s' "$DTU_ID" | sha256sum | cut -c1-12)
cat <<EOF

Done. The bridge is running now and will start at every boot.
  MQTT topics:   solar/rwb1_ble/$ID/#
  Logs:          journalctl --user -u rwb1-ble -f
  Restart:       systemctl --user restart rwb1-ble
  Uninstall:     $DIR/install.sh --uninstall

In Home Assistant: the MQTT integration must use the same broker; then add the
package and the dashboard from homeassistant/ (see the README, "Home Assistant").
EOF
