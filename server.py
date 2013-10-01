#!/usr/bin/python python
# vim: set fileencoding=utf-8
import asyncore
import logging
import sys
from leilao.server import config
from leilao.server import request
from leilao.server import tcp
from leilao.server import udp

def main():
  configs = config.ServerConfig()
  tcp_server = tcp.TCPServer('', configs, request.ClientRequestHandler)
  udp_server = udp.UDPServer('', configs)
  try:
    asyncore.loop(timeout=0.5, use_poll=False)
  except KeyboardInterrupt:
    logging.info('Shutting down!')

if __name__ == "__main__":
  main()
