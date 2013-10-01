#!/bin/bash
for i in {1..1000}
do
  echo "Launch T2 Madeira Machico$i 600"
done | python client.py u p Beiras

for i in {1..1000}
do
  echo "Launch T2 Madeira Monte$i 600"
done | python client.py u p Beiras

for i in {1..1000}
do
  echo "Launch T2 Madeira Funchal$i 600"
done | python client.py u p Beiras

for i in {1..1000}
do
  echo "Launch T2 Aveiro Eixo$i 600"
done | python client.py u p Ilhas

for i in {1..1000}
do
  echo "Launch T2 Viseu Campo$i 600"
done | python client.py u p Beiras
