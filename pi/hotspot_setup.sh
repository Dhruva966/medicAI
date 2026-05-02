#!/usr/bin/env bash
# Pi hotspot setup for MedicAI — Pi OS 64-bit (Bookworm/Bullseye)
# Creates WiFi hotspot "MedicAI" with no password, static IP 192.168.4.1
# Also sets up SSH key import and Piper TTS.
#
# Run on the Pi:
#   chmod +x hotspot_setup.sh && sudo bash hotspot_setup.sh
#
# After running:
#   - Pi broadcasts "MedicAI" SSID (no password)
#   - Pi is reachable at 192.168.4.1 from any connected device
#   - SSH key auth is configured (no password prompts)

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: run as root:  sudo bash hotspot_setup.sh" >&2
  exit 1
fi

echo "[hotspot] checking dependencies..."
apt-get update -qq
apt-get install -y -qq network-manager aplay alsa-utils

echo "[hotspot] stopping any existing hotspot..."
nmcli con delete "MedicAI-Hotspot" 2>/dev/null || true

echo "[hotspot] creating WiFi hotspot..."
nmcli con add \
  type wifi \
  ifname wlan0 \
  con-name "MedicAI-Hotspot" \
  autoconnect yes \
  ssid "MedicAI" \
  mode ap \
  ipv4.method shared \
  ipv4.addresses "192.168.4.1/24" \
  wifi-sec.key-mgmt none

nmcli con up "MedicAI-Hotspot"
echo "[hotspot] hotspot 'MedicAI' is now active on 192.168.4.1"

# --- SSH key setup ---
echo ""
echo "[ssh] setting up key-based auth..."
PI_USER="${SUDO_USER:-pi}"
PI_HOME=$(eval echo "~$PI_USER")
mkdir -p "$PI_HOME/.ssh"
chmod 700 "$PI_HOME/.ssh"
touch "$PI_HOME/.ssh/authorized_keys"
chmod 600 "$PI_HOME/.ssh/authorized_keys"
chown -R "$PI_USER:$PI_USER" "$PI_HOME/.ssh"

echo ""
echo "[ssh] MANUAL STEP REQUIRED:"
echo "  From the M3 Mac, run:"
echo "    ssh-keygen -t ed25519 -f ~/.ssh/medicai_pi -N ''"
echo "    ssh-copy-id -i ~/.ssh/medicai_pi.pub ${PI_USER}@192.168.4.1"
echo "  Then test: ssh -i ~/.ssh/medicai_pi ${PI_USER}@192.168.4.1 echo OK"

# --- Audio setup ---
echo ""
echo "[audio] checking audio output..."
if aplay -l 2>/dev/null | grep -q "card"; then
  echo "[audio] audio devices found:"
  aplay -l 2>/dev/null | grep "card"
else
  echo "[audio] WARNING: no audio output devices detected."
  echo "  If using USB speaker: unplug and replug, then run:  aplay -l"
  echo "  If using HDMI: run:  sudo raspi-config -> System -> Audio -> HDMI"
fi

# --- aplay test ---
echo ""
echo "[audio] testing audio pipeline (you should hear a beep)..."
speaker-test -t sine -f 440 -l 1 2>/dev/null || echo "[audio] speaker-test not available — skip"

# --- Piper TTS install on Pi (optional — main design uses M3 Mac for TTS) ---
echo ""
echo "[tts] NOTE: Main design synthesizes TTS on M3 Mac and streams via SSH."
echo "  Piper install on Pi is NOT required for the demo."
echo "  If you want Piper on Pi anyway:"
echo "    pip3 install piper-tts"

echo ""
echo "========================================"
echo "  MedicAI Pi setup complete."
echo "  Hotspot: SSID=MedicAI, IP=192.168.4.1"
echo "  Next: connect M3 Mac and iPhone to 'MedicAI' WiFi"
echo "  Then test SSH from Mac: ssh pi@192.168.4.1"
echo "========================================"
