# $HOME대신 ~은 안된다. HOME은 `echo HOME`을 해보면 나온다. < /Users/jihye >
IDENTITY_FILE="$HOME/.ssh/id_rsa"
USER="pi"
HOST="192.168.0.112"
#HOST="192.168.219.146"
#HOST="122.38.188.152"
PROJECT_DIR="$HOME/CurrentWorks/RaspiStreaming/raspistream/raspi_stream_restful"
SERVER_DIR="/home/pi/raspistream/raspi_stream_restful"
VENV_DIR="/home/pi/raspistream"

# ssh로 서버에 접속하는 명령어/ ssh를 통해 HOST에 접속하는 것까지 실행
CMD_CONNECT="ssh -i ${IDENTITY_FILE} ${USER}@${HOST}"
#CMD_CONNECT="ssh ${USER}@${HOST}"
echo "Start Deploy"

KILLSERVER_CMD="./killserver.sh"
# 서버에서 실행중이던 runserver 프로세스들을 모두 종료
# ${CMD_CONNECT} "ps -ax | grep runserver"
${CMD_CONNECT} "cd ${SERVER_DIR} && ${KILLSERVER_CMD}"
# ${CMD_CONNECT} "ps -ax | grep runserver"
echo "- Kill runserver"

# 서버의 파일을 지움
${CMD_CONNECT} rm -rf ${SERVER_DIR}
echo "${SERVER_DIR} - Delete server files"

# 서버에 프로젝트 파일을 다시 업로드, -q(quiet)옵션을 통해서 올라가는 파일들을 보이지 않게 해준다.
scp -q -i ${IDENTITY_FILE} -r ${PROJECT_DIR} ${USER}@${HOST}:${SERVER_DIR}
echo "- Upload files"

# pipenv에서 --venv를 하면 현재 쓰고 있는 virtualenv가 어디에서 실행되고 있는지를 알 수 있다.
# 서버 접속 후 SERVER_DIR로 이동, pipenv --venv로 가상환경의 경로 가져오기
# CMD_CONNECT명령어를 실행한 다음에 나머지 두 명령어도 한번에 실행할 커멘드 두개를 가져온다. (&&)
# $다음 ()는 $다음의 명령어를 실행하고 실행된 결과를 문자열로 출력해준다.
#VENV_PATH=$(${CMD_CONNECT} "cd ${SERVER_DIR} && pipenv --venv")
#echo "- Get Python virtual env path ${VENV_PATH}"

# 가상환경의 경로에 /bin/python을 붙여 서버에서 사용하는 python의 경로 만들기
#PYTHON_PATH="${VENV_DIR}/bin/python3"
#echo "- Get Python path ${PYTHON_PATH}"

# runserver를 backgroud에서 실행해주는 커멘드(nohup)
# nohup을 사용하면 세션이 종료되어도(로그아웃을 해도) 계속해서 실행이 가능하다.
# 그냥 python이라고 쓰면 시스템에 있는 python이 실행되는데, 우리는 pipenv로 관리되고 있는
# 가상환경에 있는 python을 실행하도록 한다.
#RUNSERVER_CMD="nohup ${PYTHON_PATH} manage.py runserver 0:8000 &>/dev/null &"
RUNSERVER_CMD="./startserver.sh"

# 서버 접속후, 프로젝트의 'app'폴더까지 이동한 후 runserver명령어를 실행
${CMD_CONNECT} "cd ${SERVER_DIR} && ${RUNSERVER_CMD}"
echo "- Excute runserver"

echo "- Deploy Complete"