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
from comum import (OUT, ACO, Perfil, tubo, Tubo, TuboDobrado, agrupar_iguais, ListaCorte, novo_dxf, bulge_canto,  # noqa: E402
                   comprimento_corte, preview_vistas)

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
BRACO = Perfil(75, 120, 5)       # braço arrastado

X_TRAVESSAS = [500, 1000, 1450, 2000, 2550]  # posições (centro) entre longarinas
X_BALANCOS = [400, 1550, 2000, 2550]        # balanços até a borda da carroceria (fora da caixa de roda)
X_FIM_CAMBAO = 1450 + 25   # a viga entra no chassi até a travessa do pivô
ESQUADRO = (300, 200)      # esquadros de chapa sob a junção viga/travessa dianteira: ao longo da viga, ao longo da travessa
                           # (diagonais de tubo formariam um "mini-A" e tirariam ~16° de manobra)

# veículo rebocador p/ cálculo do ângulo de manobra (tipo Hilux/Ranger)
LARG_VEICULO = 1855
BOLA_PARACHOQUE = 200      # distância da bola até o para-choque do veículo

# roda e pneu: 33x12.50R17 em roda 17x8, ET0
PNEU_D, PNEU_L = 838, 318
ARO_D, ARO_L = 17 * 25.4, 8 * 25.4
BITOLA = 1540              # centro a centro dos pneus
X_EIXO = 950               # centro da roda a partir da traseira
PCD, N_PINOS, CB = 139.7, 6, 106.1

# suspensão
COMPR_BRACO = 500          # pivô até o centro da roda
Z_PIVO = 480
MOLA_D, X_MOLA = 140, 1000
Y_MOLA = 430               # centro da mola (por dentro do braço)
CHAPA_E = 8                # espessura das chapas cortadas a laser (suportes)

NOME = "chassi"


# ================================================================ derivados
YL = VAO_LONGARINAS / 2 - LONGARINA.b / 2          # centro da longarina
ZL = Z_CHASSI + LONGARINA.h / 2                    # centro da longarina
Z_TOPO = Z_CHASSI + LONGARINA.h                    # topo do chassi = apoio do assoalho
YB = LARG_CARROCERIA / 2 - SECUNDARIO.b / 2        # borda da carroceria
Z_RODA = PNEU_D / 2
Y_RODA = BITOLA / 2
X_PIVO = X_EIXO + COMPR_BRACO
Y_BRACO = Y_RODA - PNEU_L / 2 - 28 - BRACO.b / 2   # 28 mm de folga até o flanco do pneu
X_ENGATE = COMPR_TOTAL - 250                       # início do acoplamento
X_BOLA = COMPR_TOTAL - 50                          # centro de giro do acoplamento


def lados(f):
    """Gera a peça para o lado direito (+Y) e o espelho (-Y)."""
    return [f(+1), f(-1)]


def construir(lista):
    import Part
    from FreeCAD import Vector as V

    chassi, susp, comprados, rodas = [], [], [], []

    # ---- tubos do chassi com encaixe macho-fêmea (laser tubular)
    tubos = []

    def T(nome, perfil, p0, p1):
        t = Tubo(nome, perfil, p0, p1)
        tubos.append(t)
        return t

    juntas = []  # (tubo que encosta, ponta, tubo que recebe)

    traseira = T("travessa traseira / para-choque", TRAVESSA, (TRAVESSA.b / 2, -LARG_CARROCERIA / 2, ZL),
                 (TRAVESSA.b / 2, LARG_CARROCERIA / 2, ZL))
    longs = {}
    for s in (+1, -1):
        longs[s] = T("longarina", LONGARINA, (SECUNDARIO.b, s * YL, ZL), (COMPR_CHASSI, s * YL, ZL))
        juntas.append((longs[s], 0, traseira))

    yi = VAO_LONGARINAS / 2 - LONGARINA.b
    zc = Z_TOPO - CAMBAO.h / 2
    viga = T("cambão (viga única)", CAMBAO, (X_FIM_CAMBAO, 0, zc), (X_ENGATE, 0, zc))
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
        x0 = X_TRAVESSAS[-1] - TRAVESSA.b / 2
        y0 = sg * CAMBAO.b / 2
        tri = Part.makePolygon([V(x0, y0, 0), V(x0 + ex, y0, 0), V(x0, y0 + sg * ey, 0), V(x0, y0, 0)])
        chassi.append(Part.Face(tri).extrude(V(0, 0, CHAPA_E)).translated(V(0, 0, Z_CHASSI - CHAPA_E)))

    # engate (placa + bloco representando acoplamento tipo DO35 / bola)
    chassi.append(Part.makeBox(12, CAMBAO.b + 40, CAMBAO.h, V(X_ENGATE, -CAMBAO.b / 2 - 20, zc - CAMBAO.h / 2)))
    comprados.append(Part.makeBox(COMPR_TOTAL - X_ENGATE - 12, 80, 90, V(X_ENGATE + 12, -40, zc - 45)))

    # ---- suspensão (braço arrastado + mola + suportes)
    xb0 = X_EIXO - 60                          # braço passa um pouco atrás do eixo
    for s in (+1, -1):
        t, L = tubo(BRACO, (xb0, s * Y_BRACO, Z_RODA - 6), (X_PIVO, s * Y_BRACO, Z_PIVO))
        susp.append(t)
        # bucha do pivô
        comprados.append(Part.makeCylinder(30, BRACO.b + 20, V(X_PIVO, s * Y_BRACO - (BRACO.b + 20) / 2, Z_PIVO), V(0, 1, 0)))
        # suportes do pivô (2 chapas penduradas na longarina/travessa)
        for dy in (-1, 1):
            yp = s * Y_BRACO + dy * (BRACO.b / 2 + 12 + CHAPA_E / 2)
            susp.append(Part.makeBox(120, CHAPA_E, Z_CHASSI - (Z_PIVO - 60),
                                     V(X_PIVO - 60, yp - CHAPA_E / 2, Z_PIVO - 60)))
        # ponta de eixo + cubo + tambor
        y_face = s * (Y_BRACO + BRACO.b / 2)
        y_cubo = s * Y_RODA
        comprados.append(Part.makeCylinder(30, abs(y_cubo - y_face), V(X_EIXO, y_face, Z_RODA), V(0, s, 0)))
        comprados.append(Part.makeCylinder(150, 70, V(X_EIXO, s * (Y_RODA - 80), Z_RODA), V(0, s, 0)))  # tambor 12"
        # mola: prato inferior no braço, prato superior sob longarina/travessa
        z_braco_mola = (Z_RODA - 6) + (Z_PIVO - Z_RODA + 6) * (X_MOLA - xb0) / (X_PIVO - xb0) - BRACO.h / 2
        z_inf, z_sup = z_braco_mola, Z_CHASSI - CHAPA_E
        susp.append(Part.makeBox(180, abs(s * Y_BRACO - s * Y_MOLA) + 90 + BRACO.b / 2, CHAPA_E,
                                 V(X_MOLA - 90, min(s * (Y_MOLA - 90), s * (Y_BRACO + BRACO.b / 2)), z_inf - CHAPA_E)))
        susp.append(Part.makeBox(180, 180, CHAPA_E, V(X_MOLA - 90, s * Y_MOLA - 90, z_sup)))
        mola = Part.makeCylinder(MOLA_D / 2, z_sup - z_inf, V(X_MOLA, s * Y_MOLA, z_inf)).cut(
            Part.makeCylinder(MOLA_D / 2 - 15, z_sup - z_inf, V(X_MOLA, s * Y_MOLA, z_inf)))
        comprados.append(mola)
    lista.add("braço arrastado", BRACO, L, 2, "ver chapas laterais/bucha")
    alt_mola = z_sup - z_inf

    # ---- rodas e pneus
    for s in (+1, -1):
        y0 = s * Y_RODA - s * PNEU_L / 2
        pneu = Part.makeCylinder(PNEU_D / 2, PNEU_L, V(X_EIXO, y0, Z_RODA), V(0, s, 0))
        pneu = pneu.makeFillet(70, pneu.Edges)
        pneu = pneu.cut(Part.makeCylinder(ARO_D / 2, PNEU_L + 2, V(X_EIXO, y0 - s, Z_RODA), V(0, s, 0)))
        aro = Part.makeCylinder(ARO_D / 2, ARO_L, V(X_EIXO, s * Y_RODA - s * ARO_L / 2, Z_RODA), V(0, s, 0)).cut(
            Part.makeCylinder(ARO_D / 2 - 6, ARO_L, V(X_EIXO, s * Y_RODA - s * ARO_L / 2, Z_RODA), V(0, s, 0)))
        disco = Part.makeCylinder(ARO_D / 2 - 6, 10, V(X_EIXO, s * Y_RODA, Z_RODA), V(0, s, 0))
        furos = [Part.makeCylinder(CB / 2, 12, V(X_EIXO, s * Y_RODA - s, Z_RODA), V(0, s, 0))]
        for i in range(N_PINOS):
            a = 2 * math.pi * i / N_PINOS
            furos.append(Part.makeCylinder(7, 12, V(X_EIXO + PCD / 2 * math.cos(a), s * Y_RODA - s,
                                                    Z_RODA + PCD / 2 * math.sin(a)), V(0, s, 0)))
        rodas += [pneu, aro.fuse(disco.cut(furos))]

    return chassi, susp, comprados, rodas, alt_mola, pecas_tubo, juntas, sem_encaixe, tubos


# ================================================================ preview dos encaixes
def preview_juntas(tubos, caminho, afastar=70, raio=110):
    """Vistas isométricas "explodidas" de algumas juntas: tubo que encosta afastado do que recebe."""
    import Part
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from FreeCAD import Vector as V

    def achar(nome, x=None, y_sinal=None):
        for t in tubos:
            if t.nome == nome and (x is None or abs(t.p0.x - x) < 1) and                     (y_sinal is None or (t.p0.y + t.p1.y) * y_sinal > 0):
                return t

    casos = [
        ("travessa -> longarina", achar("travessa", 1000), 1, achar("longarina", y_sinal=+1)),
        ("meia travessa -> viga do cambão", achar("meia travessa", 2000, +1), 0, achar("cambão (viga única)")),
        ("balanço -> longarina", achar("balanço lateral", 2000, +1), 0, achar("longarina", y_sinal=+1)),
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
        x0 = X_TRAVESSAS[-1] - TRAVESSA.b / 2
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

    # suporte do pivô: 120 x altura, base reta (solda na longarina), fundo em arco, furo da bucha
    alt = Z_CHASSI - (Z_PIVO - 60)
    doc = novo_dxf()
    msp = doc.modelspace()
    r = 60
    msp.add_lwpolyline([(0, alt, 0), (0, r, 1.0), (2 * r, r, 0), (2 * r, alt, 0)],
                       format="xyb", close=True, dxfattribs={"layer": "CORTE"})
    msp.add_circle((r, r), 31, dxfattribs={"layer": "CORTE"})  # furo p/ parafuso M30 / bucha
    salvar("suporte_pivo", 8, doc, f"SUPORTE PIVO  chapa {CHAPA_E} mm  qtd 8")

    # prato da mola (superior e inferior): 180x180 com furo de centragem e 4 furos de fixação
    doc = novo_dxf()
    msp = doc.modelspace()
    msp.add_lwpolyline(bulge_canto(15, 0, 0, 180, 180), format="xyb", close=True, dxfattribs={"layer": "CORTE"})
    msp.add_circle((90, 90), 25, dxfattribs={"layer": "CORTE"})
    for x, y in [(20, 20), (160, 20), (20, 160), (160, 160)]:
        msp.add_circle((x, y), 6.5, dxfattribs={"layer": "CORTE"})
    salvar("prato_mola", 4, doc, f"PRATO MOLA  chapa {CHAPA_E} mm  qtd 4")

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
if __name__ in ("__main__", "chassi"):
    import FreeCAD
    import Import

    os.makedirs(OUT, exist_ok=True)
    lista = ListaCorte()
    chassi, susp, comprados, rodas, alt_mola, pecas_tubo, juntas, sem_encaixe, tubos = construir(lista)

    # um STEP por peça de tubo, no referencial do próprio tubo (eixo X), p/ a máquina de laser tubular
    dir_tubo = os.path.join(OUT, "laser_tubular")
    os.makedirs(dir_tubo, exist_ok=True)
    for cod, t, q in pecas_tubo:
        t.loc.exportStep(os.path.join(dir_tubo, f"{cod}.step"))
    preview_juntas(tubos, os.path.join(OUT, f"{NOME}_encaixes.png"))

    # documento FreeCAD com peças nomeadas (abre direto e dá p/ medir)
    doc = FreeCAD.newDocument(NOME)
    objs = []
    for grupo, solidos in (("Chassi", chassi), ("Suspensao", susp), ("Comprados", comprados), ("Rodas", rodas)):
        g = doc.addObject("App::DocumentObjectGroup", grupo)
        for i, s in enumerate(solidos):
            o = doc.addObject("Part::Feature", f"{grupo}_{i:02d}")
            o.Shape = s
            g.addObject(o)
            objs.append(o)
    doc.recompute()
    doc.saveAs(os.path.join(OUT, f"{NOME}.FCStd"))
    Import.export(objs, os.path.join(OUT, f"{NOME}.step"))

    massa_tubos = lista.salvar_csv(os.path.join(OUT, f"{NOME}_lista_corte.csv"))
    pecas = chapas_dxf()
    preview_vistas([("#c0392b", chassi), ("#2471a3", susp + comprados), ("#333333", rodas)],
                   os.path.join(OUT, f"{NOME}.png"), "Chassi + suspensão + rodas (v0)")

    # ---- conferências
    import Part
    estrutura = Part.makeCompound(chassi + susp + comprados)
    pneus = Part.makeCompound(rodas[0::2])
    folga = estrutura.distToShape(pneus)[0]
    bb = Part.makeCompound(chassi + susp + comprados + rodas).BoundBox
    massa_aco = sum(s.Volume for s in chassi + susp) * ACO  # estrutura soldada (sem comprados)

    print("=" * 60)
    print(f"Envelope: {bb.XLength:.0f} x {bb.YLength:.0f} x {bb.ZLength:.0f} mm "
          f"(ref X2: 3700 x 1860)")
    print(f"Topo do chassi (assoalho): {Z_TOPO:.0f} mm do chão | vão livre sob a mola: {min(s.BoundBox.ZMin for s in susp + comprados):.0f} mm")
    print(f"Folga mínima estrutura <-> pneu: {folga:.1f} mm")
    print(f"Altura livre da mola (estática): {alt_mola:.0f} mm")
    print(f"Massa estrutura soldada (3D): {massa_aco:.0f} kg | só tubos da lista: {massa_tubos:.0f} kg")
    for perfil, (m, barras) in lista.resumo_barras().items():
        print(f"  {perfil}: {m:.1f} m -> {barras} barras de 6 m")
    print(f"Ângulo de manobra (veículo {LARG_VEICULO} mm, bola a {BOLA_PARACHOQUE} mm do para-choque): "
          f"viga única {angulo_manobra('viga'):.0f}° | cambão em A {angulo_manobra('A'):.0f}°")
    print(f"Encaixes macho-fêmea: {len(juntas) - len(sem_encaixe)} de {len(juntas)} juntas")
    for a, b in sem_encaixe:
        print(f"  sem encaixe (solda de topo): {a} -> {b}")
    print(f"Laser tubular: {len(pecas_tubo)} peças diferentes, {sum(q for _, _, q in pecas_tubo)} tubos")
    for nome, q, c, f in pecas:
        print(f"  laser {nome}: qtd {q}, {c:.2f} m de corte/peça, {f} furos")
