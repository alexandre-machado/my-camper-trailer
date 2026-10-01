"""
Chassi + suspensão + rodas da carretinha (v0, conceitual).

Referência: Patriot X2 Tourer — 3,70 x 1,86 m, pneus 33" aro 17, furação 6x139,7,
suspensão independente por braço arrastado (trailing arm) + mola helicoidal,
chassi escada separado em aço galvanizado. Cambão de viga única central (como a
TerraTrek TTE): sem o "A" junto ao engate, o ângulo de manobra fica bem maior.

Sistema de coordenadas (mm): X = da traseira (0) para a frente (engate),
Y = lateral (0 no centro), Z = para cima (0 no chão).

    "C:\\Program Files\\FreeCAD 1.1\\bin\\freecadcmd.exe" cad\\chassi.py

ATENÇÃO: perfis e espessuras são estimativas para estudo de forma/massa,
NÃO dimensionamento estrutural. Validar com engenheiro antes de fabricar.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veiculo  # noqa: E402
import toro  # noqa: E402
import braco  # noqa: E402
from pneu import Medida, pneu_at, roda  # noqa: E402
from comum import (OUT, ACO, Perfil, tubo, Tubo, TuboDobrado, agrupar_iguais, ListaCorte, novo_dxf, bulge_canto,  # noqa: E402
                   comprimento_corte, preview_vistas, render_3d, executado_direto)

# ================================================================ parâmetros
COMPR_TOTAL = 3700      # traseira até a ponta do engate
LARG_CARROCERIA = 1780  # largura do assoalho/carroceria (sobre as rodas)
COMPR_CHASSI = 2600     # traseira até a travessa dianteira
VAO_LONGARINAS = 1000   # largura externa entre longarinas
Z_CHASSI = 600          # face inferior das longarinas em relação ao chão (estático)

LONGARINA = Perfil(50, 100, 3)   # RHS 100x50x3 em pé
TRAVESSA = Perfil(50, 100, 3)
CAMBAO = Perfil(75, 150, 5)      # viga única do cambão (em pé)
SECUNDARIO = Perfil(50, 50, 3)   # balanços laterais e bordas da carroceria

X_TRAVESSAS = [500, 1000, 1450, 2000]  # posições (centro) entre longarinas; a da frente é a própria
                                       # longarina, dobrada 90° (corte em V) até o cambão
X_BALANCOS = [400, 1550, 2000, 2540]   # balanços até a borda da carroceria (fora da caixa de roda)
X_FIM_CAMBAO = 1450 + 25   # a viga entra no chassi até a travessa do pivô
ESQUADRO = (300, 200)      # esquadros de chapa sob a junção viga/travessa dianteira: ao longo da viga, ao longo da travessa
                           # (diagonais de tubo formariam um "mini-A" e tirariam ~16° de manobra)

# veículo rebocador, pneu e furação vêm de veiculo.py (parâmetros gerais do projeto)
LARG_VEICULO = veiculo.LARGURA
BOLA_PARACHOQUE = veiculo.BOLA_PARACHOQUE
PNEU = veiculo.PNEU        # mesmo pneu do carro -> estepe compartilhado
_m = Medida(PNEU)
PNEU_D, PNEU_L = _m.diametro, _m.largura
PCD, N_PINOS, CB = veiculo.PCD, veiculo.N_PINOS, veiculo.CB
X_EIXO = 950               # centro da roda a partir da traseira

# suspensões em estudo -> bitola (centro a centro dos pneus) de cada uma. As duas vão para o mesmo
# FCStd/STEP, cada uma num grupo próprio (com as suas rodas); SUSPENSAO é a que abre visível.
#   "toro"  = agregado multilink da Fiat Toro 4x4 (toro.py)
#   "braco" = braço arrastado próprio (braco.py)
SUSPENSOES = {"toro": toro.BITOLA, "braco": 1540}
SUSPENSAO = "toro"
BITOLA = SUSPENSOES[SUSPENSAO]

ET_RODA = veiculo.ET       # face de apoio da roda em relação ao centro do pneu
CHAPA_E = 8                # espessura das chapas cortadas a laser (suportes)

NOME = "chassi"


# ================================================================ derivados
YL = VAO_LONGARINAS / 2 - LONGARINA.b / 2          # centro da longarina
ZL = Z_CHASSI + LONGARINA.h / 2                    # centro da longarina
Z_TOPO = Z_CHASSI + LONGARINA.h                    # topo do chassi = apoio do assoalho
YB = LARG_CARROCERIA / 2 - SECUNDARIO.b / 2        # borda da carroceria
Z_RODA = PNEU_D / 2
X_FRENTE = COMPR_CHASSI - LONGARINA.b / 2           # centro do trecho dianteiro (dobrado) das longarinas
X_ENGATE = COMPR_TOTAL - 250                       # início do acoplamento
X_BOLA = COMPR_TOTAL - 50                          # centro de giro do acoplamento


def lados(f):
    """Gera a peça para o lado direito (+Y) e o espelho (-Y)."""
    return [f(+1), f(-1)]


def construir(lista):
    import Part
    from FreeCAD import Vector as V

    chassi, comprados = [], []

    # ---- tubos do chassi com encaixe macho-fêmea (laser tubular)
    tubos = []

    def T(nome, perfil, p0, p1):
        t = Tubo(nome, perfil, p0, p1)
        tubos.append(t)
        return t

    juntas = []  # (tubo que encosta, ponta, tubo que recebe)

    traseira = T("travessa traseira / para-choque", TRAVESSA, (TRAVESSA.b / 2, -LARG_CARROCERIA / 2, ZL),
                 (TRAVESSA.b / 2, LARG_CARROCERIA / 2, ZL))
    yi = VAO_LONGARINAS / 2 - LONGARINA.b
    zc = Z_TOPO - CAMBAO.h / 2
    viga = T("cambão (viga única)", CAMBAO, (X_FIM_CAMBAO, 0, zc), (X_ENGATE, 0, zc))
    # longarina + travessa dianteira numa peça só: dobra 90° na frente (corte em V) e encaixa no cambão.
    # longs[s] = trecho longitudinal (é ele que recebe travessas e balanços).
    longs = {}
    for s in (+1, -1):
        dobrada = TuboDobrado("longarina (dobrada na frente)", LONGARINA,
                              [(SECUNDARIO.b, s * YL, ZL), (X_FRENTE, s * YL, ZL), (X_FRENTE, s * CAMBAO.b / 2, ZL)])
        tubos.append(dobrada)
        longs[s] = dobrada.segs[0]
        juntas += [(longs[s], 0, traseira), (dobrada.segs[-1], 1, viga)]
    travessas = {}
    for x in X_TRAVESSAS:
        if x <= X_FIM_CAMBAO:
            travessas[x] = t = T("travessa", TRAVESSA, (x, -yi, ZL), (x, yi, ZL))
            juntas += [(t, 0, longs[-1]), (t, 1, longs[+1])]
        else:  # cortadas pela viga do cambão
            for s in (+1, -1):
                t = T("meia travessa", TRAVESSA, (x, s * CAMBAO.b / 2, ZL), (x, s * yi, ZL))
                juntas += [(t, 0, viga), (t, 1, longs[s])]
    juntas.append((viga, 0, travessas[max(x for x in travessas)]))

    # quadros laterais em 50x50 com cantos dobrados (corte em V + dobra), topo nivelado com as longarinas:
    #   traseiro "L" = borda + balanço; dianteiro "U" = balanço + borda + balanço.
    # Balanços intermediários encaixam na borda do "U". Sem borda sobre a caixa de roda.
    zs = Z_TOPO - SECUNDARIO.h / 2
    yl, yb = VAO_LONGARINAS / 2, LARG_CARROCERIA / 2 - SECUNDARIO.b
    x_tras, x_fr0, x_fr1 = X_BALANCOS[0], X_BALANCOS[1], X_BALANCOS[-1]
    for s in (+1, -1):
        quadro_l = TuboDobrado("quadro traseiro (L)", SECUNDARIO,
                               [(TRAVESSA.b, s * YB, zs), (x_tras, s * YB, zs), (x_tras, s * yl, zs)])
        quadro_u = TuboDobrado("quadro dianteiro (U)", SECUNDARIO,
                               [(x_fr0, s * yl, zs), (x_fr0, s * YB, zs), (x_fr1, s * YB, zs), (x_fr1, s * yl, zs)])
        tubos += [quadro_l, quadro_u]
        juntas += [(quadro_l.segs[0], 0, traseira), (quadro_l.segs[-1], 1, longs[s]),
                   (quadro_u.segs[0], 0, longs[s]), (quadro_u.segs[-1], 1, longs[s])]
        for x in X_BALANCOS[2:-1]:
            t = T("balanço lateral", SECUNDARIO, (x, s * yl, zs), (x, s * yb, zs))
            juntas += [(t, 0, longs[s]), (t, 1, quadro_u.segs[1])]

    sem_encaixe = [(a.nome, b.nome) for a, ponta, b in juntas if not a.encaixar(ponta, b)]

    grupos = agrupar_iguais(tubos)
    pecas_tubo = []
    for n, g in enumerate(grupos, 1):
        cod = f"T{n:02d}"
        t = g[0]
        lista.add(f"{cod} {t.nome}", t.perfil, t.L, len(g),
                  f"laser tubular {cod}.step, {t.machos} linguetas, {t.femeas} rasgos"
                  + (f", {t.nota}" if t.nota else ""))
        pecas_tubo.append((cod, t, len(g)))
    chassi += [t.shape for t in tubos]

    for sg in (+1, -1):  # esquadros sob a travessa dianteira, soldados na lateral da viga
        ex, ey = ESQUADRO
        x0 = X_FRENTE - TRAVESSA.b / 2
        y0 = sg * CAMBAO.b / 2
        tri = Part.makePolygon([V(x0, y0, 0), V(x0 + ex, y0, 0), V(x0, y0 + sg * ey, 0), V(x0, y0, 0)])
        chassi.append(Part.Face(tri).extrude(V(0, 0, CHAPA_E)).translated(V(0, 0, Z_CHASSI - CHAPA_E)))

    # engate (placa + bloco representando acoplamento tipo DO35 / bola)
    chassi.append(Part.makeBox(12, CAMBAO.b + 40, CAMBAO.h, V(X_ENGATE, -CAMBAO.b / 2 - 20, zc - CAMBAO.h / 2)))
    comprados.append(Part.makeBox(COMPR_TOTAL - X_ENGATE - 12, 80, 90, V(X_ENGATE + 12, -40, zc - 45)))

    return chassi, comprados, pecas_tubo, juntas, sem_encaixe, tubos


def modelos_roda():
    """Pneu AT detalhado + roda, gerados uma vez (sem lamelas, p/ ficar rápido) e copiados em cada opção."""
    borracha, letras = pneu_at(_m, com_lamelas=False)
    return [borracha, roda(_m, PCD, N_PINOS, CB, et=ET_RODA)] + ([letras] if letras else [])


def montar_suspensao(tipo, modelos):
    """Uma opção de suspensão com as suas rodas (a bitola muda com a opção).
    Retorna dict: soldado (aço soldado na carreta), comprados, rodas [borracha, roda, letras]*2,
    alt_mola, info, braco_L."""
    import Part
    from FreeCAD import Vector as V

    y_roda = SUSPENSOES[tipo] / 2
    susp, comprados, rodas = [], [], []
    info, L = {}, None
    if tipo == "toro":
        susp, comprados, info = toro.suspensao(X_EIXO, y_roda, Z_RODA, Z_CHASSI, YL, LONGARINA.b, et=ET_RODA)
        alt_mola = info["mola_altura"]
    else:
        susp, comprados, info, L = braco.suspensao(X_EIXO, y_roda, Z_RODA, Z_CHASSI, YL, LONGARINA.b, et=ET_RODA)
        alt_mola = info["mola_altura"]

    for s in (+1, -1):
        for sh in modelos:
            sh = sh.copy()
            if s < 0:  # lado esquerdo: gira p/ as letras e a face da roda ficarem para fora
                sh.rotate(V(0, 0, 0), V(0, 0, 1), 180)
            sh.translate(V(X_EIXO, s * y_roda, Z_RODA))
            rodas.append(sh)
    return dict(soldado=susp, comprados=comprados, rodas=rodas, alt_mola=alt_mola, info=info, braco_L=L)


# ================================================================ preview dos encaixes
def preview_juntas(tubos, caminho, afastar=70, raio=110):
    """Vistas isométricas "explodidas" de algumas juntas: tubo que encosta afastado do que recebe."""
    import Part
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from FreeCAD import Vector as V

    def achar(nome, x=None, y_sinal=None):
        for t in [seg for t in tubos for seg in getattr(t, "segs", [t])]:
            if t.nome.startswith(nome) and (x is None or abs(t.p0.x - x) < 1) and                     (y_sinal is None or (t.p0.y + t.p1.y) * y_sinal > 0):
                return t

    casos = [
        ("travessa -> longarina", achar("travessa", 1000), 1, achar("longarina", y_sinal=+1)),
        ("meia travessa -> viga do cambão", achar("meia travessa", 2000, +1), 0, achar("cambão (viga única)")),
        ("balanço -> longarina", achar("balanço lateral", 2000, +1), 0, achar("longarina", y_sinal=+1)),
        ("longarina dobrada -> cambão", achar("longarina", X_FRENTE, +1), 1, achar("cambão (viga única)")),
        ("longarina -> para-choque", achar("longarina", y_sinal=+1), 0, achar("travessa traseira / para-choque")),
    ]
    c30, s30 = math.cos(math.radians(30)), math.sin(math.radians(30))
    fig, axs = plt.subplots(1, len(casos), figsize=(5 * len(casos), 5))
    for ax, (titulo, a, ponta, b) in zip(axs, casos):
        centro = a.p1 if ponta == 1 else a.p0
        eixo = (a.p1 - a.p0).normalize()
        desloc = eixo * (afastar if ponta == 0 else -afastar)
        regiao = Part.makeBox(2 * raio, 2 * raio, 2 * raio, centro - V(raio, raio, raio))
        sa = a.shape.common(regiao.translated(-desloc)).translated(desloc)
        sb = b.shape.common(regiao)
        for cor, sh in (("#c0392b", sa), ("#2471a3", sb)):
            for ed in sh.Edges:
                pts = [p - centro for p in ed.discretize(10)]
                ax.plot([(p.x - p.y) * c30 for p in pts], [(p.x + p.y) * s30 + p.z for p in pts],
                        color=cor, lw=0.7)
        ax.set_title(titulo)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.suptitle("Encaixes macho-fêmea (vermelho = linguetas, azul = rasgos), vista explodida")
    fig.tight_layout()
    fig.savefig(caminho, dpi=120)


# ================================================================ manobra
def contorno_frente(tipo):
    """Segmentos (vista superior) da frente da carreta que podem tocar o veículo."""
    xf, yc = COMPR_CHASSI, LARG_CARROCERIA / 2
    segs = [((xf, -yc), (xf, yc))]                              # frente da carroceria
    if tipo == "viga":
        b = CAMBAO.b / 2 + 20
        segs += [((X_FIM_CAMBAO, s * b), (COMPR_TOTAL, s * b)) for s in (+1, -1)]
        x0 = X_FRENTE - TRAVESSA.b / 2
        ex, ey = ESQUADRO
        segs += [((x0, s * (CAMBAO.b / 2 + ey)), (x0 + ex, s * CAMBAO.b / 2)) for s in (+1, -1)]
    else:  # "A" — versão anterior, só para comparação
        segs += [((xf, s * VAO_LONGARINAS / 2), (X_ENGATE, s * 85)) for s in (+1, -1)]
    return segs


def angulo_manobra(tipo, passo=0.25):
    """Maior ângulo carreta x veículo antes de encostar (veículo = retângulo à frente da bola)."""
    pts = []
    for (x0, y0), (x1, y1) in contorno_frente(tipo):
        for i in range(101):
            t = i / 100
            pts.append((x0 + (x1 - x0) * t - X_BOLA, y0 + (y1 - y0) * t))
    a = 0.0
    while a < 120:
        c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
        for x, y in pts:
            xr, yr = x * c - y * s_, x * s_ + y * c
            if xr > BOLA_PARACHOQUE and abs(yr) < LARG_VEICULO / 2:
                return a
        a += passo
    return a


# ================================================================ chapas para laser
def chapas_dxf():
    """Peças planas cortadas a laser, um DXF por peça. Retorna [(nome, qtd, corte_m, furos)]."""
    pecas = []
    d = os.path.join(OUT, "dxf")
    os.makedirs(d, exist_ok=True)

    def salvar(nome, qtd, doc, texto):
        msp = doc.modelspace()
        msp.add_text(texto, height=5, dxfattribs={"layer": "INFO"}).set_placement((0, -12))
        doc.saveas(os.path.join(d, f"{nome}.dxf"))
        c, f = comprimento_corte(msp)
        pecas.append((nome, qtd, c / 1000, f))

    chapas_braco(salvar)   # só usadas na opção "braco"
    return pecas_comuns(salvar, pecas)


def chapas_braco(salvar):
    # orelha do pivô: 140 x altura, base reta (solda na tampa sob a longarina), fundo em arco,
    # furo oblongo p/ o parafuso M20 da bucha: ±6 mm na horizontal = ajuste de convergência
    alt = Z_CHASSI - CHAPA_E - (braco.Z_PIVO - 70)
    doc = novo_dxf()
    msp = doc.modelspace()
    r, folga, aj = 70, 10.5, 6
    msp.add_lwpolyline([(0, alt, 0), (0, r, 1.0), (2 * r, r, 0), (2 * r, alt, 0)],
                       format="xyb", close=True, dxfattribs={"layer": "CORTE"})
    msp.add_lwpolyline([(r - aj, r - folga, 1.0), (r + aj, r - folga, 0), (r + aj, r + folga, 1.0), (r - aj, r + folga, 0)],
                       format="xyb", close=True, dxfattribs={"layer": "CORTE"})
    salvar("braco_orelha_pivo", 4, doc, f"ORELHA PIVO  chapa {CHAPA_E} mm  qtd 4  (oblongo = ajuste de convergencia)")

    # prato da mola (superior e inferior): 180x180 com furo de centragem e 4 furos de fixação
    doc = novo_dxf()
    msp = doc.modelspace()
    msp.add_lwpolyline(bulge_canto(15, 0, 0, 180, 180), format="xyb", close=True, dxfattribs={"layer": "CORTE"})
    msp.add_circle((90, 90), 25, dxfattribs={"layer": "CORTE"})
    for x, y in [(20, 20), (160, 20), (20, 160), (160, 160)]:
        msp.add_circle((x, y), 6.5, dxfattribs={"layer": "CORTE"})
    salvar("braco_prato_mola", 4, doc, f"PRATO MOLA  chapa {CHAPA_E} mm  qtd 4")


def pecas_comuns(salvar, pecas):
    # tampa de tubo 100x50 (fecha pontas de longarina/cambão contra água — chassi galvanizado precisa furo de dreno)
    doc = novo_dxf()
    msp = doc.modelspace()
    msp.add_lwpolyline(bulge_canto(3, 0, 0, 50, 100), format="xyb", close=True, dxfattribs={"layer": "CORTE"})
    msp.add_circle((25, 50), 6, dxfattribs={"layer": "CORTE"})  # furo de dreno/escape p/ galvanização
    salvar("tampa_100x50", 6, doc, "TAMPA 100x50  chapa 3 mm  qtd 6")

    # esquadro do cambão: triângulo com as pontas agudas aparadas
    ex, ey = ESQUADRO
    doc = novo_dxf()
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (ex, 0), (ex, 12), (12, ey), (0, ey)], close=True, dxfattribs={"layer": "CORTE"})
    salvar("esquadro_cambao", 2, doc, f"ESQUADRO CAMBAO  chapa {CHAPA_E} mm  qtd 2")

    return pecas


# ================================================================ main
NOMES_SUSP = {"toro": "Suspensao Toro 4x4 (multilink)", "braco": "Suspensao braco arrastado"}


def resumo_suspensao(tipo, chassi, op):
    import Part
    estrutura = Part.makeCompound(chassi + op["soldado"] + op["comprados"])
    folga = estrutura.distToShape(Part.makeCompound(op["rodas"][0::3]))[0]
    bitola = SUSPENSOES[tipo]
    print(f"--- {NOMES_SUSP[tipo]}{' (visível ao abrir)' if tipo == SUSPENSAO else ''}")
    print(f"  bitola {bitola} | largura nos pneus {bitola + PNEU_L:.0f} (carroceria {LARG_CARROCERIA}, Compass {LARG_VEICULO})")
    print(f"  vão livre {min(s.BoundBox.ZMin for s in op['soldado'] + op['comprados']):.0f} | "
          f"folga mínima estrutura <-> pneu {folga:.1f} | mola estática {op['alt_mola']:.0f}")
    print(f"  aço soldado da suspensão (3D): {sum(s.Volume for s in op['soldado']) * ACO:.0f} kg")
    i = op["info"]
    if tipo == "toro":
        print(f"  pontos ESTIMADOS | topo do amortecedor Z {i['amort_topo_z']:.0f} em Y ±{i['amort_topo_y']:.0f} -> "
              f"{i['amort_topo_z'] - Z_TOPO:+.0f} mm em relação ao assoalho ({Z_TOPO:.0f})")
        print(f"  mola Ø{toro.MOLA_D} sob a longarina (Y ±{i['mola_y']:.0f}) | "
              f"calço agregado->longarina {i['calco_agregado']:.0f} mm")
        print(f"  peças compradas (agregado + 2 lados) ~{i['massa_comprados']:.0f} kg (estimado, sem diferencial)")
    else:
        a = braco.analise(X_EIXO, Z_RODA, Z_CHASSI, PNEU_D)
        print(f"  cargas: PBT {braco.PBT} - bola {braco.CARGA_BOLA} -> {a['m_carr']:.0f} kg suspensos/roda "
              f"(vazio ~{a['m_vazio']:.0f}, tara estimada {braco.TARA})")
        print(f"  curso na roda: +{braco.CURSO_COMPRESSAO} / -{braco.CURSO_EXTENSAO} | "
              f"relação mola {a['mr_mola']:.2f}, amortecedor {a['mr_amort']:.2f}")
        print(f"  MOLA: {a['k_mola']:.0f} N/mm (roda {a['k_roda']:.0f} N/mm -> {braco.FREQ_ALVO} Hz carregada, "
              f"{a['f_vazio']:.1f} Hz vazia) | livre ~{a['mola_livre']:.0f}, montada {a['est']['L_mola']:.0f}, "
              f"bloco <= {a['mola_bloco_max']:.0f} | força estática {a['f_mola'] / 1000:.1f} kN, máx {a['f_mola_max'] / 1000:.1f} kN")
        print(f"  vazia, a carreta fica ~{a['sobe_vazio']:.0f} mm mais alta (mola linear)")
        print(f"  AMORTECEDOR (olhal-olhal): fechado <= {a['amort_fechado_max']:.0f}, aberto >= {a['amort_aberto_min']:.0f} "
              f"(curso >= {a['amort_curso_min']:.0f}); montado {a['est']['L_amort']:.0f}")
        print(f"  batente de borracha dentro da mola: encosta a +{braco.CURSO_COMPRESSAO} | "
              f"topo do pneu na compressão {a['topo_pneu_comp']:.0f} -> caixa de roda até "
              f"{a['topo_pneu_comp'] + 30:.0f} (+{a['topo_pneu_comp'] + 30 - Z_TOPO:.0f} acima do assoalho)")


if executado_direto(__name__, __file__):
    import FreeCAD
    import Import
    import Part

    os.makedirs(OUT, exist_ok=True)
    lista = ListaCorte()
    chassi, comprados_chassi, pecas_tubo, juntas, sem_encaixe, tubos = construir(lista)
    modelos = modelos_roda()
    opcoes = {tipo: montar_suspensao(tipo, modelos) for tipo in SUSPENSOES}
    lista.add("braço arrastado", braco.PERFIL, opcoes["braco"]["braco_L"], 2,
              "SÓ NA OPÇÃO BRAÇO ARRASTADO, ver chapas braco_*")

    # um STEP por peça de tubo, no referencial do próprio tubo (eixo X), p/ a máquina de laser tubular
    dir_tubo = os.path.join(OUT, "laser_tubular")
    os.makedirs(dir_tubo, exist_ok=True)
    for cod, t, q in pecas_tubo:
        t.loc.exportStep(os.path.join(dir_tubo, f"{cod}.step"))
    preview_juntas(tubos, os.path.join(OUT, f"{NOME}_encaixes.png"))

    # documento FreeCAD único: chassi + uma pasta (grupo) por suspensão, cada uma com as suas rodas.
    # Só a opção SUSPENSAO abre visível; para trocar, selecionar a pasta e apertar espaço.
    doc = FreeCAD.newDocument(NOME)
    n = [0]

    def grupo(nome, rotulo, pai=None):
        g = doc.addObject("App::DocumentObjectGroup", nome)
        g.Label = rotulo
        if pai:
            pai.addObject(g)
        return g

    def pecas(g, prefixo, solidos, visivel=True):
        for s in solidos:
            n[0] += 1
            o = doc.addObject("Part::Feature", f"{prefixo}_{n[0]:03d}")
            o.Shape = s
            o.Visibility = visivel
            g.addObject(o)

    g_ch = grupo("Chassi", "Chassi")
    pecas(g_ch, "Chassi", chassi)
    pecas(grupo("Engate", "Engate (comprado)", g_ch), "Engate", comprados_chassi)
    topo = [g_ch]
    for tipo, op in opcoes.items():
        vis = tipo == SUSPENSAO
        g = grupo(f"Susp_{tipo}", NOMES_SUSP[tipo])
        g.Visibility = vis
        pecas(grupo(f"Soldado_{tipo}", f"Soldado na carreta ({tipo})", g), f"Sold_{tipo}", op["soldado"], vis)
        pecas(grupo(f"Comprados_{tipo}", f"Pecas compradas ({tipo})", g), f"Comp_{tipo}", op["comprados"], vis)
        pecas(grupo(f"Rodas_{tipo}", f"Rodas e pneus ({tipo})", g), f"Roda_{tipo}", op["rodas"], vis)
        topo.append(g)
    doc.recompute()
    doc.saveAs(os.path.join(OUT, f"{NOME}.FCStd"))
    Import.export(topo, os.path.join(OUT, f"{NOME}.step"))  # pastas viram montagens no STEP

    massa_tubos = lista.salvar_csv(os.path.join(OUT, f"{NOME}_lista_corte.csv"))
    pecas_laser = chapas_dxf()

    # imagens: geral com a opção visível; detalhe do lado direito de cada opção
    op = opcoes[SUSPENSAO]
    susp, comprados, rodas = op["soldado"], comprados_chassi + op["comprados"], op["rodas"]
    preview_vistas([("#c0392b", chassi), ("#2471a3", susp + comprados), ("#333333", rodas)],
                   os.path.join(OUT, f"{NOME}.png"), f"Chassi + suspensão ({SUSPENSAO}) + rodas (v0)")
    render_3d([("#b03a2e", c) for c in chassi] + [("#2e6da4", c) for c in susp + comprados]
              + [("#2b2b2b", r) for r in rodas[0::3]] + [("#9aa5ad", r) for r in rodas[1::3]]
              + [("#e8e8e8", r) for r in rodas[2::3]],
              os.path.join(OUT, f"{NOME}_3d.png"), vistas=((28, -125), (18, -35)),
              titulo=f"Chassi + suspensão ({SUSPENSAO}) + rodas — pneu {PNEU}", tol=3, tamanho=(9, 6))
    braco.diagrama(os.path.join(OUT, f"{NOME}_braco_curso.png"), X_EIXO, Z_RODA, Z_CHASSI, Z_TOPO, PNEU_D, LONGARINA.h)
    caixa = Part.makeBox(1100, 1100, 1000, FreeCAD.Vector(X_EIXO - 500, -100, 0))

    def recorte(cor, solidos):
        return [(cor, c.common(caixa)) for c in solidos if c.BoundBox.intersect(caixa.BoundBox)]
    for tipo, o in opcoes.items():
        render_3d(recorte("#b03a2e", chassi) + recorte("#e67e22", o["soldado"]) + recorte("#2e6da4", o["comprados"])
                  + recorte("#9aa5ad", o["rodas"][1::3]),
                  os.path.join(OUT, f"{NOME}_suspensao_{tipo}.png"), vistas=((10, -140), (-30, -100)),
                  titulo=f"{NOMES_SUSP[tipo]}, lado direito: laranja = soldado na carreta, azul = peças compradas",
                  tol=1.0, tamanho=(12, 6))

    # ---- conferências
    bb = Part.makeCompound(chassi + susp + comprados + rodas).BoundBox
    print("=" * 60)
    print(f"Envelope ({SUSPENSAO}): {bb.XLength:.0f} x {bb.YLength:.0f} x {bb.ZLength:.0f} mm (ref X2: 3700 x 1860)")
    print(f"Topo do chassi (assoalho): {Z_TOPO:.0f} mm do chão")
    print(f"Pneu: {_m.resumo()}")
    print(f"Massa chassi soldado (3D): {sum(s.Volume for s in chassi) * ACO:.0f} kg | "
          f"tubos da lista (com braços): {massa_tubos:.0f} kg")
    for perfil, (m, barras) in lista.resumo_barras().items():
        print(f"  {perfil}: {m:.1f} m -> {barras} barras de 6 m")
    print(f"Veículo: {veiculo.NOME} | reboque c/ freio {veiculo.REBOQUE_COM_FREIO} kg, "
          f"s/ freio {veiculo.REBOQUE_SEM_FREIO} kg, bola {veiculo.CARGA_BOLA} kg")
    print(f"Ângulo de manobra (veículo {LARG_VEICULO} mm, bola a {BOLA_PARACHOQUE} mm do para-choque): "
          f"viga única {angulo_manobra('viga'):.0f}° | cambão em A {angulo_manobra('A'):.0f}°")
    for tipo, o in opcoes.items():
        resumo_suspensao(tipo, chassi, o)
    print(f"Encaixes macho-fêmea: {len(juntas) - len(sem_encaixe)} de {len(juntas)} juntas")
    for a, b in sem_encaixe:
        print(f"  sem encaixe (solda de topo): {a} -> {b}")
    print(f"Laser tubular: {len(pecas_tubo)} peças diferentes, {sum(q for _, _, q in pecas_tubo)} tubos")
    for nome, q, c, f in pecas_laser:
        print(f"  laser {nome}: qtd {q}, {c:.2f} m de corte/peça, {f} furos")
