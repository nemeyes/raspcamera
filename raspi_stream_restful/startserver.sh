#!/bin/bash

PROJ_DIR=/home/pi/raspistream/raspi_stream_restful
cd $PROJ_DIR

#LOC=$(pipenv --venv)
LOC=/home/pi/raspistream/
source ${LOC}/bin/activate

nohup python3 manage.py runserver 0:8000 &>/dev/null &