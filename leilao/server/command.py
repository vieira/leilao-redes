# vim: set fileencoding=utf-8
import logging
from collections import deque
from leilao.server import house

class Command(object):
  """
  Estrutura Base de um comando e operações genéricas que sobre ele
  podem ser efectuadas.
  """
  def __init__(self, server):
    self.server = server

  def __eq__(self, other):
    return self.__str__() == other.__str__()

  def post_process(self):
    pass


class Launch(Command):
  """
  Launch Tipo Cidade Morada Valor
  """
  def __init__(self, server, args):
    self.tipologia = args[1]
    self.cidade = args[2]
    self.morada = args[3]
    self.valor = args[4]
    self.responsavel_dados = (args[5], args[6])
    super(Launch, self).__init__(server)

  def __str__(self):
    return ' '.join(('Launch', self.tipologia, self.cidade, \
                      self.morada, self.valor, self.responsavel_dados[0], \
                      self.responsavel_dados[1]))

  def recursive(self):
    return True
  
  def responsavel(self):
    router = self.server.configs.router
    if self.cidade in router:
      if router[self.cidade] == ('localhost', self.server.port):
        return None
      else:
        return router[self.cidade]
    else:
      logging.warning("A cidade de %s não é conhecida." % self.cidade)

  def process(self, server, client=None, rfc=False):
    casa = house.House(self)
    server.configs.warehouse.new_house(casa)
    logging.debug("Nova casa guardada.")

  def post_process(self):
    for tipologia in self.server.configs.warehouse.houses:
      for house in self.server.configs.warehouse.houses[tipologia]:
        if house.cidade == self.cidade and house.morada == self.morada:
          house.responsavel_dados = None

  @classmethod
  def is_command_for(cls, request):
    return request.startswith('Launch')


class Bid(Command):
  """
  Bid Cidade Morada Valor
  """
  def __init__(self, server, args):
    self.tipologia = None
    self.cidade = args[1]
    self.morada = args[2]
    self.valor = args[3]
    self.responsavel_dados = None
    super(Bid, self).__init__(server)

  def __str__(self):
    return ' '.join(('Bid', self.cidade, self.morada, self.valor))

  def recursive(self):
    return True
  
  def responsavel(self):
    router = self.server.configs.router
    if self.cidade in router:
      if router[self.cidade] == ('localhost', self.server.port):
        return None
      else:
        return router[self.cidade]
    else:
      logging.warning("A cidade de %s não é conhecida." % self.cidade)

  def process(self, server, client=None, rfc=False):
    casa = house.House(self)
    server.configs.warehouse.update_valor(casa, self.valor)

    if client and not rfc:
      ### XXX LocalServer é responsável
      server.configs.warehouse.arma_timeout(server, self, casa)
      for each_client in server.open_bids:
        if each_client != client:
          for bid in server.open_bids[each_client]:
            if self.cidade == bid.cidade and self.morada == bid.morada:
              if each_client in server.confirmed_requests:
                server.confirmed_requests[each_client].append(self)
              else:
                server.confirmed_requests[each_client] = deque(self)
    
      if client in server.open_bids:
        for bid in server.open_bids[client]:
          if self.cidade == bid.cidade and self.morada == bid.morada:
            open_bids = list(server.open_bids[client])
            open_bids.remove(bid)
            server.open_bids[client] = deque(open_bids) 
            break
      server.open_bids[client].append(self)
      ###
    elif not client and not rfc:
      ### XXX LocalServer recebeu notificação do responsável
      for each_client in server.open_bids:
        others = []
        for bid in server.open_bids[each_client]:
          if each_client in server.waiting_requests \
            and server.waiting_requests[each_client]:
            for req in server.waiting_requests[each_client]:
              if bid.cidade != req.cidade or bid.morada != req.morada:
                others.append(bid)
          else:
            others.append(bid)
        for bid in others:
          if self.morada == bid.morada and self.cidade == bid.cidade: #XXX
            try:
              server.confirmed_requests[each_client].append(self)
            except KeyError:
              server.confirmed_requests[each_client] = deque([self])

      for each_client in server.waiting_requests:
        for request in server.waiting_requests[each_client]:
          #if request.__class__.__name__ == Bid.__name__:
          for bid in server.open_bids[each_client]:
            if request.cidade == bid.cidade and request.morada == bid.morada:
              open_bids = list(server.open_bids[each_client])
              open_bids.remove(bid)
              server.open_bids[each_client] = deque(open_bids)
              break
          server.open_bids[each_client].append(request)
      ###
    elif not client and rfc:
      ### XXX Responsável recebeu pedido de LocalServer
      server.configs.warehouse.arma_timeout(server, self, casa)
      for each_client in server.open_bids:
        for bid in server.open_bids[each_client]:
          if bid.cidade == self.cidade and bid.morada == self.morada:
            server.confirmed_requests[each_client].append(self)

  def endbid(self, server, house):
    """
    Quando o timer expirar este método será chamado e dará o bid
    que está em curso sobre house como terminado.
    """
    logging.info("O bid sobre %s terminou a %s" % (house.morada, house.valor))
    pdu = ' '.join(("EndBid", house.cidade, house.morada, house.valor))
    for client in server.open_bids:
      for bid in server.open_bids[client]:
        if house.cidade == bid.cidade and house.morada == bid.morada:
          server.confirmed_requests[client].append(pdu)
          server.configs.warehouse.remove_house(bid)
          open_bids = list(server.open_bids[client])
          open_bids.remove(bid)
          server.open_bids[client] = deque(open_bids)
          del open_bids
          break
    server.cache.append((pdu, None))

  @classmethod
  def is_command_for(cls, request):
    return request.startswith('Bid')


class EndBid(Command):
  """
  EndBid Cidade Morada Valor
  """
  def __init__(self, server, args):
    self.cidade = args[1]
    self.morada = args[2]
    self.valor = args[3]
    super(EndBid, self).__init__(server)

  def __str__(self):
    return ' '.join(('EndBid', self.cidade, self.morada, self.valor))

  def recursive(self):
    return True

  def responsavel(self):
    return True

  def process(self, server, client=None, rfc=False):
    for tipologia in server.configs.warehouse.houses:
        for casa in server.configs.warehouse.houses[tipologia]:
          if casa.morada == self.morada and casa.cidade == self.cidade:
            server.configs.warehouse.remove_house(casa)
            break
    for client in server.open_bids:
      for bid in server.open_bids[client]:
        if self.cidade == bid.cidade and self.morada == bid.morada:
          try:
            server.confirmed_requests[client].append(self)
          except KeyError:
            server.confirmed_requests[client] = deque([self])
          open_bids = list(server.open_bids[client])
          open_bids.remove(bid)
          server.open_bids[client] = deque(open_bids)
          break
  
  @classmethod
  def is_command_for(cls, request):
    return request.startswith('EndBid')


class List(Command):
  """
  List Tipo
  """
  def __init__(self, server, args):
    self.tipologia = args[1]
    try:
      self.houses = deque(server.configs.warehouse.houses[self.tipologia])
    except KeyError:
      self.houses = deque()
      logging.warning("Nenhuma casa para tipologia %s." % self.tipologia)
    super(List, self).__init__(server)

  def __str__(self):
    return ' '.join(("List", self.tipologia))

  def recursive(self):
    return False

  def process(self, handler):
    data = ' '.join(("List", self.tipologia))
    emsg = "Não existem casas em leilão para esta tipologia."
    erro = ' '.join((data, '0', emsg))
    if not self.houses:
      handler.confirmed_requests.append(erro)
      return
    while len(self.houses) > 3:
      pacote = ' '.join((data, '1', self.houses.popleft().__str__()))
      pacote = ','.join((pacote, self.houses.popleft().__str__()))
      pacote = ','.join((pacote, self.houses.popleft().__str__()))
      handler.confirmed_requests.append(pacote)
    else:
      pacote = ' '.join((data, '0', self.houses.popleft().__str__()))
      while self.houses:
        pacote = ','.join((pacote, self.houses.popleft().__str__()))
      else:
        handler.confirmed_requests.append(pacote)

  @classmethod
  def is_command_for(cls, request):
    return request.startswith('List')


class File(Command):
  """
  File Cidade Morada Tamanho Imagem
  """
  def __init__(self, server, args):
    self.cidade = args[1]
    self.morada = args[2]
    self.tamanho = args[3]
    self.imagem = ' '.join(args[4:])
    super(File, self).__init__(server)

  def __str__(self):
    return ' '.join(("File", self.cidade, self.morada)) 

  def recursive(self):
    return False

  def process(self, handler):
    f = open(self.cidade + self.morada + '.bmp', 'w')
    f.write(self.imagem)
    f.close()

  @classmethod
  def is_command_for(cls, request):
    return request.startswith('File')


class View(Command):
  """
  View Cidade Morada
  """
  def __init__(self, server, args):
    self.cidade = args[1]
    self.morada = args[2]
    self.header = ' '.join(("View", self.cidade, self.morada))
    self.imagem = None
    super(View, self).__init__(server)

  def __str__(self):
    return ' '.join(("View", self.cidade, self.morada))

  def recursive(self):
    return False 

  def process(self, handler):
    for tipologia in self.server.configs.warehouse.houses:
      for house in self.server.configs.warehouse.houses[tipologia]:
        if self.cidade == house.cidade and self.morada == house.morada:
          if not house.responsavel_dados:
            # Se não tem responsável por dados é porque sou responsável
            try:
              self.imagem = open(self.cidade + self.morada + '.bmp', 'r')
              self.header = ' '.join((self.header, '2 '))
              handler.push(self.header)
              while True:
                data = self.imagem.read(1)
                if data:
                  handler.push(data)
                else:
                  handler.push(handler.get_terminator())
                  self.imagem.close()
                  logging.info("Ficheiro enviado.")
                  return
            except IOError:
              self.header = ' '.join((self.header, '0'))
              handler.confirmed_requests.append(self.header)
          else:
            ip, port = house.responsavel_dados
            pdu = ' '.join(("Redirect", self.cidade, self.morada, ip, port))
            handler.confirmed_requests.append(pdu)
  
  @classmethod
  def is_command_for(cls, request):
    return request.startswith('View')


def Request(handler, request):
  for cls in Command.__subclasses__():
    if cls.is_command_for(request):
      return cls(handler, request.split(' '))
  raise ValueError
