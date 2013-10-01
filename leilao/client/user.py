# vim: set fileencoding=utf-8
import readline
import threading
import time
from collections import deque
from cmd import Cmd
from leilao.client import command

class UserInput(Cmd):
  def __init__(self, configs):
    self.commands = deque()
    self.pending_requests = []
    self.ongoing_bids = []
    self.winning_bids = []
    self.input_available = threading.Condition()
    self.pending_bids = threading.Condition()
    Cmd.__init__(self, completekey='Tab')
    self.configs = configs
    self.prompt = '' 

  def new_command(self, data):
    self.input_available.acquire()
    request = command.Request(self, data)
    request.preprocess()
    self.input_available.notify()
    self.input_available.release()

  def emptyline(self):
    return

  def do_Launch(self, args):
    """Launch Tipologia Cidade Morada Valor
    Lança uma casa para leilão.
    """
    try:
      tipologia, cidade, morada, valor = args.split(' ')
      ip, port = self.configs.localserver
      data = ' '.join(("Launch", tipologia, cidade, morada, valor))
      pdu = ' '.join((data, ip, str(port)))
      self.new_command(pdu)
    except ValueError:
      print "Utilização: Launch Tipologia Cidade Morada Valor"

  def do_Bid(self, args):
    """Bid Cidade Morada Valor
    Lança um novo Bid sobre a casa dada.
    """
    try:
      cidade, morada, valor = args.split(' ')
      data = ' '.join(("Bid", cidade, morada, valor))
      self.new_command(data)
    except ValueError:
      print "Utilização: Bid Cidade Morada Valor"

  def do_List(self, args):
    """List Tipologia
    Mostra a lista de casas disponíveis na tipologia pedida.
    """
    try:
      tipologia = args
      data = ' '.join(("List", tipologia))
      self.new_command(data)
    except ValueError:
      print "Utilização: List Tipologia"

  def do_View(self, args):
    """View Cidade Morada
    Transfere a imagem da casa em questão, se existir.
    """
    try:
      cidade, morada = args.split(' ')
      data = ' '.join(("View", cidade, morada))
      self.new_command(data)
    except ValueError:
      print "Utilização: View Cidade Morada"

  def do_Quit(self, args):
    """Quit
    Termina a aplicação se não houver bids pendentes.
    """
    self.pending_bids.acquire()
    if self.winning_bids:
      print "Aguarde: Bid em curso..."
    while self.winning_bids:
      self.pending_bids.wait(2)
    self.pending_bids.release()
    return True

  def do_EOF(self, args):
    time.sleep(2) # tempo para enviar os comandos
    return True
