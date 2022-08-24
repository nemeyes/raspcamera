
#!/bin/bash
export TARGET_PATH="raspistream"
export TARGET_PACKAGE_PATH="raspi_stream_restful"

echo "Script executed from: ${PWD}"
BASEDIR=${PWD}

echo "install gstreamer library"
sudo apt-get install libgstreamer1.0 libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer1.0-0-dbg libgstrtspserver-1.0.0
sudo apt-get install gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
sudo apt-get install gstreamer1.0-libav gstreamer1.0-doc gstreamer1.0-tools
sudo apt-get install gstreamer1.0-omx-rpi gstreamer1.0-omx
sudo apt-get install python-gst-1.0 python3-gst-1.0
sudo apt-get install gir1.2-gst-plugins-base-1.0 gir1.2-gst-rtsp-server-1.0
sudo apt-get install python3-gi
sudo apt-get install libgirepository1.0-dev libcairo2-dev

sudo pip3 install virtualenv --quiet

if [ -d "$HOME/$TARGET_PATH/bin" ] 
then
    echo "Directory $HOME/$TARGET_PATH exists." 
else
    echo "Directory $HOME/$TARGET_PATH does not exists."
    virtualenv -q "$HOME/$TARGET_PATH"
    echo "Create Virtualenv $HOME/$TARGET_PATH"
fi

cp $BASEDIR/requirements.txt $HOME/$TARGET_PATH/.
cd $HOME/$TARGET_PATH

echo "rpicamsrc install"
git clone https://github.com/thaytan/gst-rpicamsrc.git
cd gst-rpicamsrc
./autogen.sh
./autogen.sh
make
sudo make install

source ./bin/activate
echo "Start install requirement packages"
pip3 install -r requirements.txt
echo "End install requirement packages"
deactivate
cd $BASEDIR

cp -a $BASEDIR/. $HOME/$TARGET_PATH/
echo "Copy raspistream"

echo "Register raspiStream Service"
sudo cp raspiStreamSrv /etc/init.d/.
cd /etc/init.d/
sudo chmod 755 raspiStreamSrv
sudo update-rc.d raspiStreamSrv defaults
sudo systemctl enable raspiStreamSrv
service raspiStreamSrv start
cd $BASEDIR

echo "start server"
rm *.zip

