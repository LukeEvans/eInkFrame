#!/bin/bash

echo "Enabling SPI interface..."
sudo sed -i 's/^dtparam=spi=.*/dtparam=spi=on/' /boot/config.txt
sudo sed -i 's/^#dtparam=spi=.*/dtparam=spi=on/' /boot/config.txt
sudo raspi-config nonint do_spi 0
sudo sed -i 's/^dtparam=i2c_arm=.*/dtparam=i2c_arm=on/' /boot/config.txt
sudo sed -i 's/^#dtparam=i2c_arm=.*/dtparam=i2c_arm=on/' /boot/config.txt
sudo raspi-config nonint do_i2c 0

echo "Installing system dependencies for HEIC support..."
sudo apt-get update
sudo apt-get install -y libheif-dev libffi-dev libssl-dev python3-dev python3-pip python3-venv

echo "Creating virtual environment..."
VENV_DIR="$(pwd)/venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

echo "Installing Python dependencies into venv..."
"$VENV_DIR/bin/pip" install -r requirements.txt

echo "Setting up python script epaper service..."
SERVICE_NAME="epaper.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
CURRENT_USER=${SUDO_USER:-$(whoami)}

sudo tee "$SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=ePaper Display Service
After=network.target

[Service]
ExecStart=$(pwd)/venv/bin/python $(pwd)/frame_manager.py
WorkingDirectory=$(pwd)
Restart=always
User=$CURRENT_USER

[Install]
WantedBy=multi-user.target
EOF

echo "Setting up Web Interface service..."
WEB_SERVICE_NAME="web_interface.service"
WEB_SERVICE_PATH="/etc/systemd/system/${WEB_SERVICE_NAME}"

# Note: Running as root to bind to port 80.
# If security is a concern, consider running on port 5000 and proxying,
# or using authbind/capabilities. For this local home project, root is simpler.
sudo tee "$WEB_SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=eInk Frame Web Interface
After=network.target

[Service]
ExecStart=$(pwd)/venv/bin/python $(pwd)/web_manager.py
WorkingDirectory=$(pwd)
Restart=always
User=root
Environment=SUDO_USER=$CURRENT_USER

[Install]
WantedBy=multi-user.target
EOF

echo "Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl enable "$WEB_SERVICE_NAME"

# Allow the web interface (running as root) to restart the epaper service
# (Already root, so no sudoers change needed for the service itself, 
# but good to ensure permissions are clean).

echo "Starting services..."
sudo systemctl start "$WEB_SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo "Setup complete! Web Interface running on Port 80."
read -p "Reboot requried. Reboot now? (y/n): " REBOOT_CHOICE
if [[ "$REBOOT_CHOICE" == "y" || "$REBOOT_CHOICE" == "Y" ]]; then
    echo "Rebooting now..."
    sudo reboot
else
    echo "Reboot skipped. Please remember to reboot at a later time."
fi