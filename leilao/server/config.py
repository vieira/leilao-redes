# vim: set fileencoding=utf-8
import commands
import ConfigParser
import logging
import socket
from optparse import OptionParser
from leilao.server import house

class ServerConfig(object):
  """
  Gere as configuraçoes e opções do servidor, através dos ficheiros
  de configuração e dos argumentos passados.
    
    * options: stores options passed as arguments (like -v)
    * args: stores positional arguments (like port number)
    * router: stores a dict that associate a server to each city.
    * users: stores a list of usernames and corresponding passwords.
    * warehouse: stores a list of houses.
  """
  def __init__(self):
    # Faz parsing das opções passadas como argumento
    self.usage = "usage: %prog [options] port cities users"
    self.parser = OptionParser(usage=self.usage)
    self.parser.add_option("-v", action="store_true", dest="verbose",
                          help="Displays log messages to help debugging.")
    self.timers = dict()
    (self.options, self.args) = self.parser.parse_args()
    if len(self.args) != 3:
      self.parser.error("expecting 3 arguments. Use -h for help.")
    try:
      self.port = int(self.args[0])
    except ValueError:
      self.parser.error("port should be a number")

    # Configura as opções de logging
    if self.options.verbose:
      logging.basicConfig(level=logging.DEBUG,
                          format='%(asctime)s,%(msecs)d %(levelname)s ' + \
                                 '%(message)s',
                          datefmt='%H:%M:%S')
    else:
      logging.basicConfig(level=logging.INFO,
                          format='%(levelname)s %(message)s')

    # Obtém a lista de IPs desta máquina para através do mDBs.dat
    # poder determinar por que cidades deve ser responsável.
    ips = []
    for ip in commands.getoutput("ip -f inet a|awk '/g/&&$0=$2'").split('\n'):
      ips.append(ip.split('/')[0])

    # Faz parsing do ficheiro configuração mDBs.dat
    config = ConfigParser.RawConfigParser()
    config.read('mDBs.dat')
    servers = dict()
    try:
      for item in config.items('timers'):
        self.timers[item[0]] = int(item[1])
    except ValueError:
      logging.critical("Os timers devem ser números inteiros.")

    for item in config.items('servidores'):
      host, port = item[1].split(' ')
      try:
        port = int(port)
      except ValueError:
        logging.critical("mDBs.dat: %s não é um número de porta válido", port)
        exit(1)
      if socket.gethostbyname(host).startswith('127') or \
         socket.gethostbyname(host) in ips:
        servers[item[0]] = ('localhost', int(port))
      else:
        servers[item[0]] = (host, port)
    del ips

    # Faz parsing do ficheiro cities, passado como argumento
    config = ConfigParser.RawConfigParser()
    config.read(self.args[1])
    self.router = dict()
    for item in config.items('cidades'):
      for city in item[1].split(', '):
        self.router[city] = servers[item[0]]
    del servers

    # Faz parsing do ficheiro users, passado como argumento
    config = ConfigParser.RawConfigParser()
    config.read(self.args[2])
    self.users = dict()
    for item in config.items('utilizadores'):
      self.users[item[0]] = item[1]

    # Inicializa um novo armazém de dados
    # TODO(vieira@yubo.be): Guardar dados para o disco?
    self.warehouse = house.Warehouse()
