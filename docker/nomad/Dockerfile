# Build a containerized Nomad for use in CI testing.

FROM ubuntu:18.04

RUN : \
 && apt update \
 && apt install -y busybox iproute2 python3 unzip wget \
 && wget -O tmp.zip https://releases.hashicorp.com/nomad/0.9.1/nomad_0.9.1_linux_amd64.zip \
 && unzip -oqq tmp.zip -d /usr/local/bin/

COPY ./start.sh /usr/local/bin/

EXPOSE 4646
ENTRYPOINT ["start.sh", "/var/lib/nomad"]
