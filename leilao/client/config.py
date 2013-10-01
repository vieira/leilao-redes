# vim: set fileencoding=utf-8
import commands
import ConfigParser
import logging
import socket
from optparse import OptionParser

class ClientConfig(object):
  def __init__(self):
    # Faz parsing das opções passadas como argumento
    self.usage = "usage: %prog [options] user password server"
    self.parser = OptionParser(usage=self.usage)
    self.parser.add_option("-v", action="store_true", dest="verbose",
                          help="Displays log messages to help debugging.")
    (self.options, self.args) = self.parser.parse_args()
    if len(self.args) != 3:
      self.parser.error("expecting 3 arguments. Use -h for help.")
    try:
      self.user = self.args[0]
      self.password = self.args[1]
      server = self.args[2].lower()
    except IndexError:
      self.parser.error("User, password or server missing.")
    self.timers = dict()

    # Configura as opções de logging
    if self.options.verbose:
      logging.basicConfig(level=logging.DEBUG,
                          format='%(levelname)s %(message)s')
    else:
      logging.basicConfig(level=logging.INFO,
                          format='%(message)s')

    
    # Faz parsing do ficheiro configuração mDBs.dat
    config = ConfigParser.RawConfigParser()
    config.read('mDBs.dat')
    servers = dict()
    try:
      for item in config.items('timers'):
        self.timers[item[0]] = int(item[1])
      for item in config.items('servidores'):
        host, port = item[1].split(' ')
        servers[item[0]] = (host, int(port))
    except ValueError:
      logging.critical("Os timers devem ser números inteiros.")
    if server in servers:
      self.localserver = servers[server]
    else:
      self.parser.error("O servidor inserido não foi encontrado em mDBs.dat")
