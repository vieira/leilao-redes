# vim: set fileencoding=utf-8

from threading import Timer

class Warehouse(object):
  """
  Base-de-dados que guarda e acede a casas conforme for necessário.
  """
  def __init__(self):
    self.houses = dict()

  def new_house(self, house):
    """
    Coloca uma nova casa na lista de casas conhecidas.
    """
    if house.tipologia in self.houses:
      if house not in self.houses[house.tipologia]:
        self.houses[house.tipologia].append(house)
      else:
        raise IndexError
    else:
      self.houses[house.tipologia] = [house]

  def update_valor(self, house, valor):
    for tipologia in self.houses:
      if house in self.houses[tipologia]:
        i = self.houses[tipologia].index(house)
        casa = self.houses[tipologia][i]
        if int(casa.valor) < int(valor):
          casa.valor = valor
          return True
        else:
          raise ValueError
    raise IndexError

  def arma_timeout(self, server, command, house):
    tlivemax = server.configs.timers['tlivemax']
    for tipologia in self.houses:
      if house in self.houses[tipologia]:
        i = self.houses[tipologia].index(house)
        casa = self.houses[tipologia][i]
        if casa.timer:
          casa.timer.cancel()
        casa.timer = Timer(tlivemax, command.endbid, [server, casa])
        casa.timer.start()

  def remove_house(self, bid):
    """
    Apaga uma casa da lista de casas conhecidas.
    """
    for tipologia in self.houses:
      for house in self.houses[tipologia]:
        if house.cidade == bid.cidade and house.morada == bid.morada:
          self.houses[tipologia].remove(house)


class House(object):
  """
  Estrutura de uma casa e operações básicas que sobre ela podem ser
  executadas.
  """
  def __init__(self, comando):
    self.tipologia = comando.tipologia
    self.cidade = comando.cidade
    self.morada = comando.morada
    self.valor = comando.valor
    self.responsavel_dados = comando.responsavel_dados
    self.timer = None

  def __eq__(self, other):
    return self.cidade == other.cidade \
        and self.morada == other.morada

  def __str__(self):
    return ' '.join((self.cidade, self.morada, self.valor))
