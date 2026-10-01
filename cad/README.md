# CAD → corte a laser (DXF)

## Conceito-chave

O laser corta **2D**. O "DXF 3D" não existe na prática para corte: o que o fornecedor
precisa é a **planificação** (peça desdobrada) de cada chapa, em DXF 2D, escala 1:1, em mm.
Fluxo:

```
modelo 3D paramétrico ──► peça dobrada (STEP, p/ conferir montagem)
                     └──► planificação 2D (DXF) ──► laser ──► dobradeira
```

A planificação depende de dois números **da dobradeira do fornecedor**: raio interno (R)
e fator K. Com os valores errados as abas saem com medida errada. Peça a tabela deles
antes de mandar arquivos definitivos.

## Formato de trabalho recomendado

| Opção | Prós | Contras |
|---|---|---|
| **Python + FreeCAD (Part/OCC) + ezdxf** ← usado aqui | Texto (git, diff, IA edita), paramétrico, gera STEP e DXF do mesmo código, já instalado | Precisa escrever a lógica de planificação (simples para dobras retas) |
| FreeCAD GUI + addon SheetMetal | Visual, desdobra automático (`Unfold` → DXF) | Arquivo `.FCStd` binário, difícil de versionar/automatizar |
| build123d / CadQuery (Python puro) | API moderna, exporta STEP/DXF/SVG | Instalação extra; sem desdobra nativa |
| Onshape (grátis, nuvem) | Sheet metal excelente, exporta DXF pronto | Plano grátis = documentos públicos |
| SVG (Inkscape) → DXF | Bom para peças planas decorativas | Sem unidade/escala confiável, sem 3D |

**Recomendação:** peças de chapa descritas em Python (um arquivo por peça ou família),
o que dá 3D + DXF sempre consistentes. Para montagem geral/visualização, importar os STEP
no FreeCAD (`trailer patriot.FCStd`).

## Regras do DXF para o fornecedor

- 2D, unidade **mm**, escala 1:1, versão R2010 (ou R12 se o software deles for antigo).
- Camada `CORTE`: somente contornos **fechados** (polilinhas/círculos), sem linhas duplicadas.
- Camada `DOBRA`: linhas de dobra (tracejadas) — o laser não corta; às vezes gravam uma marca.
- Camada `INFO`: textos/cotas — **não cortar** (ou mandar em arquivo separado).
- Um arquivo por peça + lista: material, espessura, quantidade, sentido da dobra.
- Furos menores que a espessura da chapa costumam não ser viáveis no laser.
- Alívio de canto nas abas (os cantos recortados) evita rasgo na dobra.

## Prova de conceito: `bandeja.py`

Painel 800×600 com abas de 30 mm, chapa 1,5 mm, furos de fixação e recorte central.

```
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" cad\bandeja.py
```

Gera em `cad/out/`: `bandeja.step` (3D dobrada), `bandeja.dxf` (planificação),
`bandeja.png` (preview). Imprime tamanho da planificação, metros de corte (base de
orçamento do laser) e massa. Conferência feita: área líquida da planificação × espessura
bate com o volume do sólido 3D (diferença < 0,1%).

`_pylibs/` contém o `ezdxf` instalado localmente para o Python do FreeCAD:
`"C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pip install --target cad\_pylibs ezdxf`
(depois remover a pasta `numpy` de lá — o FreeCAD já tem a dele).

## Parâmetros gerais: `veiculo.py`

Veículo rebocador (Jeep Compass Trailhawk 2.0 Diesel 2020): largura, pneu, furação da roda,
limites de reboque (1500 kg com freio, 400 kg sem freio, ~75 kg na bola) e medidas do engate.
Os scripts importam daqui — trocar o carro é editar um arquivo só.

## Pneu e roda: `pneu.py`

Gera o pneu a partir da medida (`Medida("235/65R17 108H")`: diâmetro, flanco, tala ideal,
carga e velocidade pelos índices) e a roda de aço com a furação. `pneu_at()` imita o Speedmax
Pangea AT das fotos em `pneu/`: 3 fileiras de blocos escalonados por lado (defasadas meio passo),
lamelas em zigue-zague (opcional, lento), garras no ombro alternando longas/curtas e letras em
relevo no flanco externo (+Y). Rodar sozinho gera `out/pneu_*.step` e imagem sombreada (VTK).

## Chassi, suspensão e rodas: `chassi.py` (v0 conceitual)

```
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" cad\chassi.py
```

Chassi escada (longarinas RHS 100x50x3), cambão de viga única RHS 150x75x5 (entra no
chassi até a travessa do pivô; sem "A" para não limitar a manobra — o script calcula o
ângulo máximo carreta x veículo), balanços até a largura da carroceria (1780), suspensão independente por braço arrastado + mola helicoidal,
pneus 33x12.50R17, furação 6x139,7, bitola 1540. Medidas tiradas por escala do
desenho do X2. Coordenadas: X da traseira para o engate, Y lateral, Z do chão.

Saídas em `cad/out/`: `chassi.FCStd` (peças nomeadas em grupos), `chassi.step`,
`chassi.png` (3 vistas), `chassi_lista_corte.csv` (tubos) e `dxf/` (chapas do laser).
Módulo `comum.py`: perfis, lista de corte, DXF e preview, reaproveitados pelos scripts.

**Perfis são estimativas para estudo de forma e massa, não dimensionamento estrutural.**

### Suspensão: agregado da Fiat Toro 4x4 (`toro.py`)

O `chassi.FCStd` (e o `chassi.step`) traz as **duas suspensões em pastas separadas**, cada uma com
as suas rodas (a bitola muda): "Suspensao Toro 4x4" e "Suspensao braco arrastado", com subpastas
soldado / peças compradas / rodas. Só a opção `SUSPENSAO` abre visível; para alternar, selecionar a pasta
e apertar espaço. Imagens de detalhe: `chassi_suspensao_toro.png` e `chassi_suspensao_braco.png`.

A opção Toro monta o agregado multilink traseiro da Toro 4x4 sob as longarinas
(4 coxins + calços de chapa), com mola separada sob a longarina, amortecedor, braço longitudinal
preso em suporte soldado e cubo/disco 5x110. Dados publicados no cabeçalho de `toro.py`; posições dos
pontos são estimativas a medir.
As chapas só da opção braço saem como `dxf/braco_*.dxf`, e o braço aparece na lista de corte marcado.

### Encaixe macho-fêmea (laser tubular)

Todo tubo que encosta em outro ganha **linguetas** nas paredes laterais (largura = parede,
altura ≈ 40% do perfil, comprimento = parede do outro tubo + 2 mm), e o tubo que recebe ganha
**rasgos** com 0,25 mm de folga por lado (`Tubo.FOLGA`). As peças se posicionam sozinhas
no gabarito antes da solda. Linguetas que cairiam perto da ponta aberta do outro tubo são omitidas.

- `out/laser_tubular/Txx.step`: um STEP por peça diferente, no eixo X (formato que o
  software de laser tubular importa); códigos e quantidades em `chassi_lista_corte.csv`.
- `out/chassi_encaixes.png`: vista explodida de algumas juntas para conferência.
- Peças espelhadas (longarina direita/esquerda) têm códigos diferentes.

### Cantos dobrados (corte em V + dobra)

Os quadros laterais em 50x50 são peças únicas dobradas (`TuboDobrado`): "L" traseiro
(borda + balanço, 1 dobra) e "U" dianteiro (balanço + borda + balanço, 2 dobras).
O laser corta um V de 90° nas paredes de cima, de baixo e na interna; a parede externa fica
inteira, é dobrada e o V fecha numa costura soldada. O STEP é o tubo reto planificado com os V.
Comprimento planificado = soma dos trechos de centro + 2×(b/2 − e) + BA por dobra,
com BA = π/2·K·e e K = 0,33 (`TuboDobrado.K`) — **calibrar dobrando uma peça de teste**.
Só cantos de 90° entre tubos do mesmo perfil, todas as dobras para o mesmo lado.

Confirmar com o fornecedor: folga do rasgo, se querem as linguetas com chanfro de entrada,
e o raio de canto real do tubo (o modelo usa canto vivo e mantém os rasgos afastados ~2×parede dos cantos).

## Próximos passos

1. Pegar R e K reais com o fornecedor de corte/dobra (e material: aço carbono, galvanizado, alumínio 5052?).
2. Mandar `bandeja.dxf` como teste para validar se o software deles lê sem ajuste.
3. Definir a lista de peças do trailer (painéis laterais, caixas, para-lamas, suportes, reforços do chassi).
4. Generalizar o script: biblioteca com primitivas (aba, dobra em U, furação, recortes) e peças como dados.
