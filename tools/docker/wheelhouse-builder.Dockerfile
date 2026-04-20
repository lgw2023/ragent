ARG BASE_IMAGE=ubuntu:latest
FROM ${BASE_IMAGE}

ARG http_proxy
ARG https_proxy
ARG all_proxy
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG ALL_PROXY
ARG no_proxy
ARG NO_PROXY
ARG APT_MIRROR_MAIN=http://mirrors.tuna.tsinghua.edu.cn/ubuntu
ARG APT_MIRROR_PORTS=http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/ragent-wheelhouse-venv/bin:${PATH}"

RUN set -eux; \
    if dpkg --print-architecture | grep -Eq '^(arm64|armhf|ppc64el|s390x|riscv64)$'; then \
      ubuntu_mirror="$APT_MIRROR_PORTS"; \
    else \
      ubuntu_mirror="$APT_MIRROR_MAIN"; \
    fi; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
      sed -i "s|http://archive.ubuntu.com/ubuntu|$ubuntu_mirror|g" /etc/apt/sources.list.d/ubuntu.sources; \
      sed -i "s|http://security.ubuntu.com/ubuntu|$ubuntu_mirror|g" /etc/apt/sources.list.d/ubuntu.sources; \
      sed -i "s|http://ports.ubuntu.com/ubuntu-ports|$ubuntu_mirror|g" /etc/apt/sources.list.d/ubuntu.sources; \
    fi; \
    apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=30 update; \
    apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=30 install -y --fix-missing --no-install-recommends \
      ca-certificates \
      build-essential \
      python3 \
      python3-dev \
      python3-venv \
      python3-pip; \
    python3 -m venv /opt/ragent-wheelhouse-venv; \
    /opt/ragent-wheelhouse-venv/bin/python -m pip install --upgrade pip; \
    rm -rf /var/lib/apt/lists/*
