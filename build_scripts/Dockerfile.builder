FROM ubuntu:18.04

# Disable interactive questions like Timezone selection
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

# Get all our dependencies
RUN apt-get update && \
    apt-get install -y python git \
    python-dev \
    python-setuptools \
    python-smbus \
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    checkinstall \
    libreadline-gplv2-dev libncursesw5-dev libssl-dev curl xz-utils \
    libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev \
    zlib1g-dev libffi-dev openssl \
    libsnappy-dev \
    cython

# Any version of python outside those supported in our base image
ARG PYTHON3_VER=3.7.2

WORKDIR /tmp
RUN curl --output /tmp/python${PYTHON3_VER}.tar.xz https://www.python.org/ftp/python/${PYTHON3_VER}/Python-${PYTHON3_VER}.tar.xz && \
    tar xf python${PYTHON3_VER}.tar.xz

WORKDIR /tmp/Python-${PYTHON3_VER}
RUN ./configure --enable-optimizations && make altinstall
    
# Install pip to fresh source version
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3.7 get-pip.py

# debian / ubuntu
RUN addgroup --gid 1000 dtkbuilder && \
    adduser --uid 1000 --ingroup dtkbuilder --home /home/dtkbuilder --shell /bin/sh --disabled-password --gecos "" dtkbuilder

RUN USER=dtkbuilder && \
    GROUP=dtkbuilder && \
    curl -SsL https://github.com/boxboat/fixuid/releases/download/v0.4/fixuid-0.4-linux-amd64.tar.gz | tar -C /usr/local/bin -xzf - && \
    chown root:root /usr/local/bin/fixuid && \
    chmod 4755 /usr/local/bin/fixuid && \
    mkdir -p /etc/fixuid && \
    printf "user: $USER\ngroup: $GROUP\n" > /etc/fixuid/config.yml

# Install basic requirements
ADD requirements_dev.txt /tmp/
RUN pip3 install -r /tmp/requirements_dev.txt

ADD pip.conf /etc/pip.conf

RUN mkdir /dtk

WORKDIR /dtk

USER dtkbuilder:dtkbuilder
ENTRYPOINT ["fixuid"]