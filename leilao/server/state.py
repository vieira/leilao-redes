# vim: set fileencoding=utf-8

class ServerState(object):
  """
  Esta classe define as variáveis de estado que são utilizadas pelo
  servidor para gerir pedidos que necessitam encaminhamento.

  Detalhes acerca do funcionamento:

  * O estado interno do servidor é mantido através da estrutura de dados
    requests[state][client][command] onde cada estado (new, pending, 
    waiting, confirmed) contém uma lista de clientes que, por sua vez, 
    contém uma lista de pedidos.
  
  * A comunicação entre os módulos TCP e UDP ocorre movendo pedidos 
    entre os vários estados desta estrutura:
    
    * Quando chegam novos pedidos são carimbados imediatamente com new. 
    * Assim que são lidos e processados podem ser movidos para pending 
      (se carecem de confirmação de um servidor remoto) ou imediatamente 
      para confirmed se já foram tratados. 
    * Quando movidos para pending serão tratados pelo módulo UDP 
      que envia o respectivo pedido de confirmação e ao recebê-lo move 
      o request para a lista de confirmados.
    * A lista de confirmados será depois tratada pelo módulo TCP 
      (enviando a resposta apropiada para o cliente).
  """
  #requests = dict({'new': dict(), 'pending': dict(), 'waiting': dict(),
  #                 'confirmed': dict(), 'bids': dict()})
  
  requests = dict({'pending': dict(), 'waiting': dict(),
                   'confirmed': dict(), 'bids': dict()})
