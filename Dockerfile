FROM osrg/ryu

RUN \
  apt-get update && \
  apt-get install -qy --no-install-recommends python-pip \
    libyaml-dev libpython2.7-dev

COPY ./ /faucet-src/

RUN \
  pip install /faucet-src

VOLUME ["/etc/ryu/faucet/", "/var/log/ryu/faucet/"]
WORKDIR /usr/local/lib/python2.7/dist-packages/ryu_faucet/org/onfsdn/faucet/

EXPOSE 6633

CMD ["ryu-manager", "--ofp-tcp-listen-port=6633", "faucet"]
