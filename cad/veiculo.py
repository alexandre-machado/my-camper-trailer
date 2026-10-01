"""
Veículo rebocador — parâmetros gerais do projeto.

Jeep Compass Trailhawk 2.0 Diesel 2020. Fontes: fichas técnicas (webmotors, carrosnaweb)
e catálogos de engate. Itens marcados CONFIRMAR devem ser checados no manual/no carro.
"""

NOME = "Jeep Compass Trailhawk 2.0 Diesel 2020"

LARGURA = 1819             # mm, sem retrovisores
COMPRIMENTO = 4416
ENTRE_EIXOS = 2636

# pneu/roda: mesmo pneu na carreta = estepe compartilhado (a furação também precisa bater)
PNEU = "235/65R17 108H"    # Speedmax Prime Pangea AT, o que o usuário usa (de fábrica: 225/60R17)
PCD, N_PINOS, CB = 110.0, 5, 65.1   # 5x110, furo central 65,1 — CONFIRMAR

# limites de reboque (ficha técnica)
REBOQUE_COM_FREIO = 1500   # kg, peso bruto máximo da carreta com freio próprio
REBOQUE_SEM_FREIO = 400    # kg
CARGA_BOLA = 75            # kg na bola — depende do engate (catálogos: 50 a 75 kg) — CONFIRMAR

# engate — MEDIR no carro
BOLA_PARACHOQUE = 200      # distância horizontal do centro da bola até o para-choque
ALTURA_BOLA = 450          # altura do centro da bola ao chão (carro vazio)
