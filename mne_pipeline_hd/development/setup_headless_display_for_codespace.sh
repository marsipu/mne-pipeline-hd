sudo apt update
sudo apt-get install -y \
    libglx-mesa0 \
    libgl1 \
    xvfb \
    x11-xserver-utils \
    herbstluftwm \
    libdbus-1-3 \
    libegl1 \
    libopengl0 \
    libosmesa6 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xinput0 \
    libxkbcommon-x11-0 \
    mesa-utils \
    x11-utils

export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
echo "Xvfb started on display $DISPLAY"
sleep 3

herbstluftwm &
echo "herbstluftwm started"
sleep 3
