#!/usr/bin/python python
# vim: set fileencoding=utf-8
import logging
import threading
from leilao.client import config
from leilao.client import tcp
from leilao.client import user

def main():
  configs = config.ClientConfig()
  user_input = user.UserInput(configs)
  tcp_thread = threading.Thread(target=tcp.connection, \
                                args=[user_input, configs])
  tcp_thread.daemon = True
  try:
    tcp_thread.start()
    user_input.cmdloop()
  except KeyboardInterrupt:
    print "\nAdeus!"

if __name__ == "__main__":
  main()
