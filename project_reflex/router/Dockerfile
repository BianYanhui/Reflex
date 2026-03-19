FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    libelf-dev \
    linux-headers-generic \
    bpfcc-tools \
    libbpfcc-dev \
    netcat \
    tcpdump \
    iproute2 \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --break-system-packages pyyaml

WORKDIR /app

COPY xdp_backpressure.c /app/
COPY router_scheduler.py /app/

RUN chmod +x router_scheduler.py

CMD ["python3", "router_scheduler.py"]
