# vim: set fileencoding=utf-8
import asynchat
import logging
import sys
from leilao.server import command
from leilao.server.state import ServerState

class ClientRequestHandler(asynchat.async_chat):
  """
  A cada ligação TCP activa é associada uma instância desta classe. 
  Os métodos que a compõem são responsáveis por verificar se há dados 
  em socket para serem processador (ou encaminhados) pelo servidor ou 
  se há pedidos em espera (que podem ter por e.g. chegado por 
  UDP de outro servidor) que tenham como destino o cliente que 
  lhe está associado.
  """

  def __init__(self, connection, client_address, server):
    asynchat.async_chat.__init__(self, connection)
    self.client_address = client_address
    self.connection = connection
    self.server = server
    self.set_terminator('\a\b\r\n')
    self.found_terminator = self.handle_request
    self.cache = ''
    #self.new_requests = ServerState.requests['new'][client_address]
    self.pending_requests = ServerState.requests['pending'][client_address]
    self.confirmed_requests = ServerState.requests['confirmed'][client_address]
    self.open_bids = ServerState.requests['bids'][client_address]

  def collect_incoming_data(self, data):
    """
    Este método é executado sempre que houver dados em socket provenientes
    do cliente associado à  instância que o contém.
    """
    self.cache += data
  
  def writable(self):
    """
    Este método é executado pelo para determinar que ligações em poll têm
    dados prontos para ser enviados. Se devolver true o controlo é 
    passado para o método handle_write dessa instância, caso contrário
    continua no loop principal do select/poll.
    """
    if self.confirmed_requests:
      return True
    else:
      return False

  def handle_write(self):
    """
    Corre apenas quando o método writable() devolver true, colocando no 
    socket todos os pedidos que se encontram na lista de confirmados 
    associada ao cliente pelo qual esta instância é responsável.
    """
    while self.confirmed_requests:
      request = self.confirmed_requests.popleft()
      try:
        request.post_process()
      except AttributeError:
        pass
      self.push(request.__str__() + self.get_terminator())
      logging.debug("Enviando dados %s..." % request.__str__())

  def handle_request(self):
    """
    Este método é invocado quando chega um pedido de um cliente com
    ligação já activa.
    """
    try:
      request = command.Request(self.server, self.cache)
      logging.debug("Recebeu pedido '%s'." % request)
      if request.recursive():
        self.pending_requests.append(request)
      else:
        request.process(self)
      self.cache = ''
    except ValueError:
      logging.warning("O pedido '%s' não é válido." %self.cache)
      self.cache = ''
    
  def handle_close(self):
    """
    Quando uma ligação com um cliente é terminada por qualquer razão
    este método é executado e trata de remover o cliente e os seus
    pedidos da memória e fechar a ligação no lado do servidor.
    """
    logging.debug("%s gone." % self.client_address[0])
    for state in ServerState.requests:
      if self.client_address in ServerState.requests[state]:
        del ServerState.requests[state][self.client_address]
    self.close()
