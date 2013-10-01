# vim: set fileencoding=utf-8
import logging
import sys
from collections import deque
from threading import Timer
from leilao import client

class Command(object):
  """
  Estrutura Base de um comando e operações genéricas que sobre ele
  podem ser efectuadas.
  """
  def __init__(self, handler):
    self.handler = handler

  def __eq__(self, other):
    return self.__str__() == other.__str__()

  def preprocess(self):
    self.handler.commands.append(self)
    self.handler.pending_requests.append(self)


class Launch(Command):
  """
  Launch Tipo Cidade Morada Valor
  """
  def __init__(self, handler, args):
    self.tipologia = args[1]
    self.cidade = args[2]
    self.morada = args[3]
    self.valor = args[4]
    self.responsavel_dados = (args[5], args[6])
    self.timer = Timer(handler.configs.timers['tconfirmmax'], self.fail)
    super(Launch, self).__init__(handler)

  def __str__(self):
    return ' '.join(('Launch', self.tipologia, self.cidade, \
                      self.morada, self.valor, self.responsavel_dados[0], \
                      self.responsavel_dados[1]))

  def preprocess(self):
    self.handler.commands.append(self)
    self.handler.pending_requests.append(self)
    self.timer.start()

  def process(self):
    if self in self.handler.pending_requests:
      i = self.handler.pending_requests.index(self)
      request = self.handler.pending_requests.pop(i)
      request.timer.cancel()
      print "Confirmação recebida: %s." % self
      send_file = File(self.handler, (self.cidade, self.morada))
      send_file.process()

  def fail(self):
    self.handler.pending_requests.remove(self)
    print "Incucesso na realização de Launch"

  @classmethod
  def is_command_for(cls, request):
    return request.startswith('Launch')


class Bid(Command):
  """
  Bid Cidade Morada Valor
  """
  def __init__(self, server, args):
    self.cidade = args[1]
    self.morada = args[2]
    self.valor = args[3]
    self.timer = Timer(server.configs.timers['tconfirmmax'], self.fail)
    super(Bid, self).__init__(server)

  def __str__(self):
    return ' '.join(('Bid', self.cidade, self.morada, self.valor))

  def preprocess(self):
    self.handler.commands.append(self)
    self.handler.pending_requests.append(self)
    self.timer.start()
  
  def process(self):
    if self in self.handler.pending_requests:
      i = self.handler.pending_requests.index(self)
      request = self.handler.pending_requests.pop(i)
      request.timer.cancel()
      for bid in self.handler.ongoing_bids:
        if bid.morada == self.morada and bid.cidade == self.cidade:
          self.handler.ongoing_bids.remove(bid)
          break
      self.handler.ongoing_bids.append(self)
      for bid in self.handler.winning_bids:
        if bid.morada == self.morada and bid.cidade == self.cidade:
          self.handler.winning_bids.remove(bid)
          break
      self.handler.winning_bids.append(self)
      print "Confirmação recebida: %s." % self
    else:
      for bid in self.handler.winning_bids:
        if bid.morada == self.morada and bid.cidade == self.cidade:
          self.handler.pending_bids.acquire() 
          self.handler.winning_bids.remove(bid)
          self.handler.pending_bids.notify()
          self.handler.pending_bids.release()
          break
      print "Notificação novo Bid: %s." % self

  def fail(self):
    self.handler.pending_requests.remove(self)
    print "Falha em %s" % self

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

  def process(self):
    for bid in self.handler.ongoing_bids:
      if bid.cidade == self.cidade and bid.morada == self.morada:
        if bid.valor == self.valor:
          print "Ganhou o bid %s por %s." % (self.morada, self.valor)
        else:
          print "Perdeu o bid %s. Acabou a %s." % (self.morada, self.valor)
        self.handler.pending_bids.acquire() 
        self.handler.ongoing_bids.remove(bid)
        try:
          self.handler.winning_bids.remove(bid)
        except ValueError:
          pass
        self.handler.pending_bids.notify()
        self.handler.pending_bids.release()
        return

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
      self.flag = int(args[2])
      self.casas = ' '.join(args[3:])
    except IndexError:
      pass
    super(List, self).__init__(server)
  
  def __str__(self):
    return ' '.join(('List', self.tipologia))

  def process(self):
    if self in self.handler.pending_requests:
      self.handler.pending_requests.remove(self)
    ## Debug
    if self.flag:
      logging.debug("Recebido um bloco de List %s" % self.tipologia)
    else:
      logging.debug("Recebido último bloco de List %s" % self.tipologia)
    ####
    print self.casas.replace(',', '\n')


  @classmethod
  def is_command_for(cls, request):
    return request.startswith('List')


class File(Command):
  """
  File Cidade Morada Tamanho Imagem
  """
  def __init__(self, server, args):
    self.cidade, self.morada = args
    self.header = ' '.join(("File", self.cidade, self.morada, '0 '))
    self.imagem = None
    super(File, self).__init__(server)

  def __str__(self):
    return ' '.join(("File", self.cidade, self.morada))

  def process(self):
    try:
      self.imagem = open(self.cidade + self.morada + '.bmp', 'r')
      self.handler.push(self.header)
      while True:
        data = self.imagem.read(1)
        if data:
          self.handler.push(data)
        else:
          self.handler.push(self.handler.get_terminator())
          self.imagem.close()
          print "Ficheiro enviado."
          return
    except IOError:
      print "Não há imagem disponível para %s." % self.morada

  @classmethod
  def is_command_for(cls, request):
    return request.startswith('File')


class View(Command):
  """
  View Cidade Morada Imagem
  """
  def __init__(self, server, args):
    self.cidade = args[1]
    self.morada = args[2]
    try:
      self.flag = int(args[3])
      self.imagem = ' '.join(args[4:])
    except IndexError:
      pass
    super(View, self).__init__(server)

  def __str__(self):
    return ' '.join(("View", self.cidade, self.morada))

  def process(self):
    if self.flag == 2:
      f = open(self.cidade + self.morada + '.bmp', 'w')
      f.write(self.imagem)
      f.close()
      logging.debug("Ficheiro recebido.")
    else:
      print "Falha no acesso a %s" % self.cidade + self.morada + '.bmp'
    
  @classmethod
  def is_command_for(cls, request):
    return request.startswith('View')


class Redirect(Command):
  """
  Redirect Cidade Morada IP Porta
  """
  def __init__(self, server, args):
    self.cidade = args[1]
    self.morada = args[2]
    self.ip = args[3]
    self.port = int(args[4])
    super(Redirect, self).__init__(server)

  def __str__(self):
    return ' '.join(("Redirect", self.cidade, self.morada, \
                      self.ip, self.port))

  def process(self):
    for request in self.handler.pending_requests:
      if request.__str__().startswith("View"):
        if request.cidade == self.cidade and request.morada == self.morada:
          rconn = client.tcp.FileTransfer(self.ip, self.port, self.cidade, \
                                   self.morada)
          self.handler.pending_requests.remove(request)

  @classmethod
  def is_command_for(cls, request):
    return request.startswith('Redirect')


def Request(handler, request):
  for cls in Command.__subclasses__():
    if cls.is_command_for(request):
      return cls(handler, request.split(' '))
  raise ValueError
