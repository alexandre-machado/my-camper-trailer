# Trailer Camper — contexto para novas sessões

Carretinha de acampamento off-road inspirada na **Patriot X2 Tourer** (3,70 x 1,86 x 1,70 m)
e na **TerraTrek TTE** (cambão de viga única). Conversa em português.
Refs: https://patriotcampers.com.au/x2n-tourer/ · https://terratrek.com.au/tte-terra-trek-expedition/
Imagens: `X2 tourer/` (specs com cotas), `pneu/` (fotos do pneu).

## Fluxo de CAD

Peças descritas em **Python** (texto, versionável) rodando no FreeCAD 1.1 sem GUI.
Cada script gera 3D (STEP/FCStd), arquivos de fabricação (DXF chapa / STEP laser tubular),
lista de corte (CSV) e imagens. `cad/out/` e `cad/_pylibs/` são ignorados pelo git (regeneráveis).

```
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" cad\chassi.py   # ~1 min
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" cad\pneu.py     # ~4 min (com lamelas)
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" cad\bandeja.py  # PoC chapa dobrada
```

- `ezdxf` fica em `cad/_pylibs` (instalar: `"...\FreeCAD 1.1\bin\python.exe" -m pip install --target cad\_pylibs ezdxf`
  e apagar a pasta `numpy` de lá).
- freecadcmd dá ao script `__name__` = nome do arquivo → usar `executado_direto(__name__, __file__)` (comum.py).
- Imagens: `render_3d` usa o VTK embutido no FreeCAD (offscreen). Conferir resultados olhando os PNG.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `cad/veiculo.py` | **parâmetros gerais**: carro rebocador, pneu, furação, limites de reboque, engate |
| `cad/comum.py` | `Perfil`, `Tubo` (encaixe macho-fêmea), `TuboDobrado` (V + dobra), `ListaCorte`, DXF, `render_3d` |
| `cad/chassi.py` | chassi + suspensão + rodas; parâmetros no topo do arquivo; gera as 2 suspensões no mesmo `chassi.FCStd`/`.step`, cada uma numa pasta com as suas rodas; `SUSPENSAO` = a que abre visível ("toro") |
| `cad/toro.py` | agregado multilink traseiro da Fiat Toro 4x4 adaptado (dados publicados + pontos ESTIMADOS) |
| `cad/pneu.py` | `Medida("235/65R17 108H")`, `pneu_at()` detalhado (blocos, garras, letras), `roda()` |
| `cad/bandeja.py` | PoC painel de chapa dobrada → STEP + DXF planificado |
| `cad/README.md` | notas técnicas (DXF p/ laser, encaixes, dobras) |
| `trailer patriot.FCStd` | modelo manual antigo do usuário (tubo RHS 50x30x2.9 + roda) |

## Parâmetros atuais (mm, kg)

- **Veículo**: Jeep Compass Trailhawk 2.0 Diesel 2020 — largura 1819; reboque **1500 c/ freio / 400 s/ freio**;
  carga na bola **~75** (depende do engate, CONFIRMAR); furação 5x110 CB 65,1 (CONFIRMAR);
  ALTURA_BOLA 450 e BOLA_PARACHOQUE 200 são chutes — MEDIR.
- **Pneu**: Speedmax Prime Pangea AT **235/65R17 108H** (o mesmo do Compass → estepe comum) — Ø737, 1000 kg/pneu, roda 17x7.
- **Chassi**: escada, longarinas RHS 100x50x3 a 1000 de vão externo, 2600 de comprimento; travessas 100x50x3
  em X = 500/1000/1450/2000/2550; carroceria 1780 de largura; topo do chassi (assoalho) a 700 do chão.
- **Cambão**: **viga única** RHS 150x75x5 (de X=1475 até o engate em 3450; total 3700) + 2 esquadros de chapa 8 mm.
  Ângulo de manobra 96° (cambão em A daria 77°).
- **Suspensão (em estudo, 2 opções)**:
  - **"toro"** (padrão): agregado multilink traseiro da **Fiat Toro 4x4** de desmanche (ideia do usuário/Gemini):
    mesma furação 5x110 do Compass, eixo de picape (carga útil ~1000 kg), mola Ø120 separada do amortecedor,
    amortecedor 716/433, bitola 1579, disco Ø278. Pontos de articulação/agregado são **ESTIMADOS** → medir peça real.
    Resultado: largura nos pneus 1814 (> carroceria 1780), topo do amortecedor **157 mm acima do assoalho** (torre na caixa
    se não inclinar/trocar amortecedor), calço agregado→longarina 106, vão livre 229, ~106 kg de peças compradas.
  - **"braco"**: independente, braço arrastado RHS 120x75x5 (500 do pivô ao eixo), mola helicoidal Ø140, tambor 12".
  Bitola 1540, eixo em X=950. Vão livre 219, folga braço↔pneu ~64.
- **Quadros laterais 50x50x3**: "L" traseiro e "U" dianteiro com cantos dobrados (corte em V), K=0,33 (calibrar).
- Encaixe macho-fêmea em todas as 29 juntas (folga 0,25/lado). 17 tubos, 10 peças diferentes. Estrutura ~171 kg.

## Decisões do usuário

- Cambão **viga única rígida**, sem "A" (prioridade: manobra). Não triangular perto do engate.
- Encaixes **macho-fêmea** nos tubos; **cantos dobrados em V** onde der.
- Não furar tubos estruturais p/ aliviar peso (fadiga/torção); alívio só em chapas/peças leves.
- Mesmo pneu do carro.

## Pendências / próximos passos

1. **Orçamento de peso e posição do eixo** — restrição central: PBT ≤ 1500 kg, carga na bola ≤ ~75 kg
   (X2 tem 800 kg de tara e 140 kg na bola). Carreta precisa de **freio próprio**.
2. Confirmar com o usuário: medidas do engate. Medir num agregado de Toro 4x4 real: pontos dos braços,
   agregado (largura, fixações), topo do amortecedor, peso → corrigir `toro.PONTOS`/`AGREGADO`.
   Freio: Toro tem disco (diesel) ou tambor Ø295 (algumas versões) — tambor combina melhor com freio de inércia.
3. Modelar: amortecedores, batentes/curso da suspensão, estepe, roda de apoio do cambão, freio, ganchos.
4. Carroceria (caixa sobre o chassi, caixas de roda: topo do pneu 737 > assoalho 700).
5. Validar com fornecedores: R e fator K de dobra (chapa), folga dos rasgos e K da dobra em V (laser tubular).
6. Dimensionamento estrutural por engenheiro + exigências do Detran (reboque fabricado sob encomenda).
