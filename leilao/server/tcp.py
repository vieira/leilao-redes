# vim: set fileencoding=utf-8
import asyncore
import logging
import socket
from collections import deque
from leilao.server.state import ServerState

class TCPServer(asyncore.dispatcher):
  """
  As ligações TCP são geridas de forma assíncrona e, após estabelecida
  a ligação, são colocadas em poll e é criada uma instância da classe
  ClientRequestHandler associada a cada ligação TCP activa.
  """
  def __init__(self, ip, configs, handler):
    self.ip = ip
    self.configs = configs
    self.port = configs.port
    self.handler = handler
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind((ip, self.port))
    self.listen(1024)

  def handle_accept(self):
    """
    Quando é recebido um pedido de um cliente para establecer ligação
    este método é executado, fazendo accept da ligação, criando espaço
    nas listas de pedidos para o cliente que se está agora a ligar e
    passando o controlo para a classe ClientRequestHandler que tratará
    de gerir a comunicação com o cliente.
    """
    try:
      conn, addr = self.accept()
      logging.debug("%s connected." % addr[0])
    except socket.error:
      logging.error("Erro no accept da ligação: %s" % socket.error.value)
      return
    for state in ServerState.requests:
      if addr not in ServerState.requests[state]:
        ServerState.requests[state][addr] = deque()
    self.handler(conn, addr, self)
