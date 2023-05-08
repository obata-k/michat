FROM python:3.10

ARG USERNAME=michat
ARG GROUPNAME=michat
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $GROUPNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    software-properties-common \
    git \
    portaudio19-dev python3-pyaudio \
    libcairo2-dev libgirepository1.0-dev \
    ffmpeg \
    flac \
    && rm -rf /var/lib/apt/lists/* /tmp/*

USER $USERNAME
WORKDIR /app

COPY --chown=$USERNAME:$USERNAME . .
## if you want to build the main branch, please uncomment the bellow line
#RUN git clone -b main --depth 1 https://github.com/obata-k/michat.git /app

ARG PYTHON_PKG=/app/pkg

# download libraries
ARG VOICEVOX_WHL_URL="https://github.com/VOICEVOX/voicevox_core/releases/download/0.14.3/voicevox_core-0.14.3+cpu-cp38-abi3-linux_aarch64.whl"
ARG ONNXRUNTIME_URL="https://github.com/microsoft/onnxruntime/releases/download/v1.13.1/onnxruntime-linux-aarch64-1.13.1.tgz"
ARG OPEN_JTALK_URL="http://sourceforge.net/projects/open-jtalk/files/Dictionary/open_jtalk_dic-1.11/open_jtalk_dic_utf_8-1.11.tar.gz"
RUN wget $VOICEVOX_WHL_URL \
    && wget $ONNXRUNTIME_URL \
    && wget $OPEN_JTALK_URL \
    && tar -xzvf ${ONNXRUNTIME_URL##*/} \
    && tar -xzvf ${OPEN_JTALK_URL##*/} \
    && cp $(basename $ONNXRUNTIME_URL | sed 's/.[^.]*$//')/lib/libonnxruntime.so* . \
    && pip install ${VOICEVOX_WHL_URL##*/} --upgrade --target $PYTHON_PKG \
    && rm ${ONNXRUNTIME_URL##*/} ${OPEN_JTALK_URL##*/} ${VOICEVOX_WHL_URL##*/}

RUN pip3 install -r requirements.txt --upgrade --target $PYTHON_PKG
ENV PATH $PATH:$PYTHON_PKG/bin
ENV PYTHONPATH $PYTHONPATH:$PYTHON_PKG

# streamlit default port
EXPOSE 8501

HEALTHCHECK --interval=1m --timeout=3s \
    CMD curl --fail http://localhost:8501 || exit 1

ENTRYPOINT ["streamlit", "run", "michat/app.py", "--global.developmentMode=false", "--server.port=8501", "--server.address=0.0.0.0"]
# ENTRYPOINT ["/bin/bash", "-c"]
