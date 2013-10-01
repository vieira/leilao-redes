# vim: set fileencoding=utf-8
import asyncore
import logging
import socket
import sys
from collections import deque
from leilao.server import command
from leilao.server.state import ServerState

class UDPServer(asyncore.dispatcher):
  """
  Os datagramas UDP são também geridos de forma assíncrona mas, pela sua
  natureza, não lhes está associada nenhuma classe para gestão de ligação.
  Cada datagrama é tratado de forma independente: quando é recebido é lido
  e baseado no estado interno do servidor uma acção é executada (e.g., este 
  datagrama vem confirmar algum pedido na lista de pendentes? Se sim esse 
  pedido é movido para a lista de confirmados).
  """
  def __init__(self, ip, configs):
    self.ip = ip
    self.configs = configs
    self.port = configs.port
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.set_reuse_addr()
    self.bind((ip, self.port))
    self.cache = deque()
    self.pending_requests = ServerState.requests['pending']
    self.waiting_requests = ServerState.requests['waiting']
    self.confirmed_requests = ServerState.requests['confirmed']
    self.open_bids = ServerState.requests['bids']

  def handle_connect(self):
    """
    Este método não está implementado no servidor UDP pois este
    protocolo não é orientado à ligação.
    """
    pass
  
  def handle_read(self):
    """
    Quando é recebido um datagrama UDP este método é executado
    e verifica se a mensagem se trata ou não de uma confirmação
    a um pedido anteriormente efectuado e move-o para a lista
    apropriada baseando-se nessa informação.
    """
    try:
      data, addr = self.recvfrom(1024)
      request = command.Request(self, data)
      outro_responsavel = request.responsavel()
    except socket.error:
      logging.error("Erro ao receber dados UDP: %s" % socket.error.value)
      return
    except ValueError:
      logging.warning("O pedido '%s' recebido por UDP é inválido." % data)
      return
    if outro_responsavel:
      # Recebe notificação de responsável, processa-a.
      try:
        request.process(self)
      except ValueError:
        logging.warning("O valor proposto não é superior ao actual.")
      except IndexError:
        logging.warning("Launch repetido ou bid numa casa desconhecida.")
      
      for client in self.waiting_requests:
        # Verifica se a notificação é confirmação de algum
        # pedido feito por um cliente deste servidor.
        if request in self.waiting_requests[client]:
          # Se for confirma ao cliente.
          if client in self.confirmed_requests:
            self.confirmed_requests[client].append(request)
          else:
            self.confirmed_requests[client] = deque([request])
          waiting_requests = list(self.waiting_requests[client])
          waiting_requests.remove(request)
          self.waiting_requests[client] = deque(waiting_requests)
          logging.debug("Received confirmation for %s!" % request)
          break
      else:
        # Se não for é uma mera notificação, não faz mais nada.
        logging.debug("Received notification %s" % request)
    else:
      logging.debug("Received request for confirmation for %s." % request)
      try:
        request.process(self, rfc=True)
        self.cache.append((request, addr))
      except ValueError:
        logging.warning("O valor proposto não é superior ao actual.")
      except IndexError:
        logging.warning("Launch repetido ou bid numa casa desconhecida.")

  def writable(self):
    """
    Devolve true se houver dados prontos para ser enviados por UDP,
    sejam pedidos de confirmação ou confirmação de pedidos.
    """
    if self.cache:
      return True
    for client in self.pending_requests:
      if self.pending_requests[client]:
        return True
    else:
      return False

  def handle_write(self):
    """
    Envia datagramas UDP com base no estado interno do servidor.
    Confirma pedidos recebidos que estejam á espera de confirmação,
    envia pedidos de confirmação de pedidos recebidos do cliente ou
    envia notificações para outros servidores.
    """
    # Servidor responsável notifica todos os outros
    while self.cache:
      try:
        request, addr = self.cache.popleft()
        servers = set(self.configs.router.values())
        ### Responde mesmo se endereço não está na lista mDBs.dat
        #if addr and addr not in servers:
        #  self.sendto(request.__str__(), addr)
        #  logging.warning("Unknown server %s." % addr[0])
        #  logging.debug("Sent notification %s to %s." % (request, addr[0]))
        for server in servers:
          if server != ("localhost", self.port):
            self.sendto(request.__str__(), server)
            logging.debug("Sent notification %s to %s." % (request, server[0]))
      except socket.error:
        logging.error("Erro ao enviar dados UDP: %s" % socket.error.value)
        pass

    # Servidor local recebe pedido de cliente
    for client in self.pending_requests:
      while self.pending_requests[client]:
        request = self.pending_requests[client].popleft()
        outro_responsavel = request.responsavel()
        if outro_responsavel:
          # Se não é responsável, envia para o responsável
          try:
            self.sendto(request.__str__(), outro_responsavel)
            logging.debug("O responsável é %s." % outro_responsavel[0])
            logging.debug("Enviando %s para o responsável." % request)
          except socket.error:
            logging.error("Erro ao enviar dados UDP.")
            pass
          # Coloca o pedido em lista de espera.
          if client in self.waiting_requests:
            self.waiting_requests[client].append(request)
          else:
            self.waiting_requests[client] = deque([request])
        else:
          # Se é responsável agenda notificação para todos
          try:
            request.process(self, client=client)
            self.confirmed_requests[client].append(request)
            self.cache.append((request, None))
            logging.debug("Este servidor é o responsável. Pedido aceite.")
          except ValueError:
            logging.warning("O valor proposto não é superior ao actual.")
          except IndexError:
            logging.warning("Launch repetido ou bid numa casa desconhecida.")
