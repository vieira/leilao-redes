# vim: set fileencoding=utf-8
import asyncore
import asynchat
import logging
import socket
import sys
from leilao.client import user
from leilao.client import command

class TCPClient(asynchat.async_chat):
  """
  Envia mensagens para o servidor e recebe respostas.
  """
  def __init__(self, ip, port, user_input):
    asynchat.async_chat.__init__(self)
    self.set_terminator('\a\b\r\n')
    self.found_terminator = self.handle_reply
    self.cache = ''
    self.user_input = user_input
    self.configs = user_input.configs
    self.pending_requests = user_input.pending_requests
    self.ongoing_bids = user_input.ongoing_bids
    self.winning_bids = user_input.winning_bids
    self.pending_bids = user_input.pending_bids
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.connect((ip, port))

  def collect_incoming_data(self, data):
    self.cache += data

  def handle_connect(self):
    # Autenticação aqui!
    pass
  
  def writable(self):
    if self.user_input.commands:
      return True
    else:
      return False

  def handle_write(self):
    request = self.user_input.commands.popleft()
    self.push(request.__str__() + self.get_terminator())

  def handle_reply(self):
    request = command.Request(self, self.cache)
    request.process()
    self.cache = ''


class FileTransfer(asynchat.async_chat):
  """
  Envia um pedido remoto para transferência de ficheiro e
  no final termina a ligação.
  """
  def __init__(self, ip, port, cidade, morada):
    self.cidade = cidade
    self.morada = morada
    asynchat.async_chat.__init__(self)
    self.set_terminator('\a\b\r\n')
    self.found_terminator = self.save_file
    self.cache = ''
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.connect((ip, port))

  def collect_incoming_data(self, data):
    self.cache += data

  def handle_connect(self):
    request = ' '.join(("View", self.cidade, self.morada))
    self.push(request + self.get_terminator())

  def save_file(self):
    request = command.Request(self, self.cache)
    request.process()
    self.close_when_done()


def connection(user_input, configs):
  ip, port = configs.localserver
  user_input.input_available.acquire()
  while not user_input.commands:
    user_input.input_available.wait()
  user_input.input_available.release()
  tcp_client = TCPClient(ip, port, user_input)
  asyncore.loop(timeout=0.5, use_poll=False)
