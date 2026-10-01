"""
Prova de conceito: peça de chapa paramétrica -> 3D (STEP) + planificação (DXF p/ corte a laser).

Peça: "bandeja" (painel com abas dobradas a 90° nos 4 lados, cantos com alívio),
típica de portas/tampas de caixa lateral de camper.

Rodar com o Python do FreeCAD (já tem OpenCascade):
    "C:\\Program Files\\FreeCAD 1.1\\bin\\freecadcmd.exe" cad\\bandeja.py
Saída em cad/out/: bandeja.step, bandeja.dxf, bandeja.png
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "_pylibs"))  # ezdxf local (append: numpy do FreeCAD tem prioridade)

import ezdxf  # noqa: E402

# ---------------------------------------------------------------- parâmetros
# Dimensões EXTERNAS da peça dobrada (mm)
W = 800.0   # largura (X)
H = 600.0   # altura (Y)
F = 30.0    # altura da aba (Z)
T = 1.5     # espessura da chapa
R = 1.5     # raio interno de dobra  -> CONFIRMAR com o fornecedor (depende do punção/matriz)
K = 0.44    # fator K                -> CONFIRMAR com o fornecedor (tabela de dobra deles)

FURO_D = 6.5         # furos de fixação nas abas
FURO_PASSO = 150.0   # espaçamento máximo entre furos
RECORTE = (200.0, 80.0, 10.0)  # recorte de ventilação no centro: largura, altura, raio de canto

NOME = "bandeja"
OUT = os.path.join(HERE, "out")

# ---------------------------------------------------------------- geometria de dobra
S = R + T                                   # recuo externo (setback) de uma dobra de 90°
BA = (math.pi / 2) * (R + K * T)            # comprimento desenvolvido da dobra (bend allowance)
ABA = F - S                                 # trecho reto da aba
A = ABA + BA                                # distância da borda plana até a área da base
BW, BH = W - 2 * S, H - 2 * S               # trecho reto da base
FW, FH = BW + 2 * A, BH + 2 * A             # tamanho total da planificação


def furos_aba(comprimento):
    """Posições (ao longo da aba) dos furos, centrados e com passo <= FURO_PASSO."""
    n = max(2, math.ceil((comprimento - 60) / FURO_PASSO) + 1)
    margem = 30.0
    passo = (comprimento - 2 * margem) / (n - 1)
    return [margem + i * passo for i in range(n)]


FURO_Z = S + ABA / 2   # altura do furo na aba (a partir do fundo externo)


# ---------------------------------------------------------------- 2D: planificação
def planificacao_dxf(caminho):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.layers.add("CORTE", color=1)                        # vermelho: contorno + furos
    doc.layers.add("DOBRA", color=2, linetype="DASHED")     # amarelo: linhas de dobra
    doc.layers.add("INFO", color=8)                         # cinza: textos (não cortar)
    msp = doc.modelspace()

    # contorno em cruz (cantos removidos = alívio de canto)
    a, bw, bh = A, BW, BH
    contorno = [
        (a, 0), (a + bw, 0), (a + bw, a), (FW, a), (FW, a + bh), (a + bw, a + bh),
        (a + bw, FH), (a, FH), (a, a + bh), (0, a + bh), (0, a), (a, a),
    ]
    msp.add_lwpolyline(contorno, close=True, dxfattribs={"layer": "CORTE"})

    # linhas de dobra (no centro da zona de dobra)
    d0, d1 = a - BA / 2, a + bw + BA / 2
    e0, e1 = a - BA / 2, a + bh + BA / 2
    for p, q in [((a, e0), (a + bw, e0)), ((a, e1), (a + bw, e1)),
                 ((d0, a), (d0, a + bh)), ((d1, a), (d1, a + bh))]:
        msp.add_line(p, q, dxfattribs={"layer": "DOBRA"})

    # furos nas abas: distância da borda plana = F - FURO_Z
    dist = F - FURO_Z
    r = FURO_D / 2
    for s in furos_aba(bw):
        msp.add_circle((a + s, dist), r, dxfattribs={"layer": "CORTE"})
        msp.add_circle((a + s, FH - dist), r, dxfattribs={"layer": "CORTE"})
    for s in furos_aba(bh):
        msp.add_circle((dist, a + s), r, dxfattribs={"layer": "CORTE"})
        msp.add_circle((FW - dist, a + s), r, dxfattribs={"layer": "CORTE"})

    # recorte central com cantos arredondados (bulge = tan(90°/4) em cada arco)
    rw, rh, rr = RECORTE
    cx, cy = FW / 2, FH / 2
    x0, x1, y0, y1 = cx - rw / 2, cx + rw / 2, cy - rh / 2, cy + rh / 2
    b = math.tan(math.pi / 8)
    msp.add_lwpolyline([
        (x0 + rr, y0, 0), (x1 - rr, y0, b), (x1, y0 + rr, 0), (x1, y1 - rr, b),
        (x1 - rr, y1, 0), (x0 + rr, y1, b), (x0, y1 - rr, 0), (x0, y0 + rr, b),
    ], format="xyb", close=True, dxfattribs={"layer": "CORTE"})

    msp.add_text(
        f"{NOME}  chapa {T} mm  R{R} K{K}  planif. {FW:.2f} x {FH:.2f}",
        height=8, dxfattribs={"layer": "INFO"},
    ).set_placement((a + 10, a + 10))

    doc.saveas(caminho)
    return doc


def conferir_dxf(caminho):
    """Relê o DXF e calcula comprimento de corte (base p/ orçamento do laser)."""
    doc = ezdxf.readfile(caminho)
    msp = doc.modelspace()
    corte = 0.0
    n_furos = 0
    for e in msp.query('*[layer=="CORTE"]'):
        if e.dxftype() == "CIRCLE":
            corte += 2 * math.pi * e.dxf.radius
            n_furos += 1
        elif e.dxftype() == "LWPOLYLINE":
            assert e.closed, "contorno aberto!"
            corte += _len(e)
    return corte, n_furos


def _len(pl):
    total = 0.0
    for s in pl.virtual_entities():
        if s.dxftype() == "LINE":
            total += (s.dxf.end - s.dxf.start).magnitude
        elif s.dxftype() == "ARC":
            ang = (s.dxf.end_angle - s.dxf.start_angle) % 360
            total += math.radians(ang) * s.dxf.radius
    return total


def preview_png(doc, caminho):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_axes([0, 0, 1, 1])
    Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace())
    fig.savefig(caminho, dpi=120)


# ---------------------------------------------------------------- 3D: peça dobrada
def solido_3d():
    import Part
    from FreeCAD import Vector as V

    def caixa(x0, x1, y0, y1, z0, z1):
        return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))

    def dobra(eixo_pos, direcao, comprimento, quadrante):
        """Quarto de tubo (raios R..R+T) ao longo de 'direcao', recortado no quadrante."""
        tubo = Part.makeCylinder(S, comprimento, eixo_pos, direcao).cut(
            Part.makeCylinder(R, comprimento, eixo_pos, direcao))
        return tubo.common(quadrante)

    partes = [caixa(S, W - S, S, H - S, 0, T)]                       # base
    partes += [caixa(0, T, S, H - S, S, F), caixa(W - T, W, S, H - S, S, F),   # abas X
               caixa(S, W - S, 0, T, S, F), caixa(S, W - S, H - T, H, S, F)]   # abas Y
    partes += [
        dobra(V(S, S, S), V(0, 1, 0), BH, caixa(0, S, S, H - S, 0, S)),
        dobra(V(W - S, S, S), V(0, 1, 0), BH, caixa(W - S, W, S, H - S, 0, S)),
        dobra(V(S, S, S), V(1, 0, 0), BW, caixa(S, W - S, 0, S, 0, S)),
        dobra(V(S, H - S, S), V(1, 0, 0), BW, caixa(S, W - S, H - S, H, 0, S)),
    ]
    solido = partes[0].multiFuse(partes[1:]).removeSplitter()

    furos = []
    for s in furos_aba(BW):
        for y in (-1, H - T - 1):
            furos.append(Part.makeCylinder(FURO_D / 2, T + 2, V(S + s, y, FURO_Z), V(0, 1, 0)))
    for s in furos_aba(BH):
        for x in (-1, W - T - 1):
            furos.append(Part.makeCylinder(FURO_D / 2, T + 2, V(x, S + s, FURO_Z), V(1, 0, 0)))
    rw, rh, rr = RECORTE
    rec = Part.makeBox(rw, rh, T + 2, V(W / 2 - rw / 2, H / 2 - rh / 2, -1))
    rec = rec.makeFillet(rr, [e for e in rec.Edges if abs(e.tangentAt(0).z) > 0.99])
    solido = solido.cut(furos + [rec])
    return solido


if __name__ in ("__main__", "bandeja"):
    os.makedirs(OUT, exist_ok=True)
    dxf_path = os.path.join(OUT, f"{NOME}.dxf")
    doc = planificacao_dxf(dxf_path)
    corte, n = conferir_dxf(dxf_path)
    preview_png(doc, os.path.join(OUT, f"{NOME}.png"))

    try:
        s = solido_3d()
        s.exportStep(os.path.join(OUT, f"{NOME}.step"))
        bb = s.BoundBox
        info3d = f"3D: {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm, " \
                 f"volume {s.Volume / 1e3:.1f} cm3, valido={s.isValid()}"
    except ImportError:
        info3d = "3D: pulado (rode com freecadcmd para gerar o STEP)"

    print(f"Planificacao: {FW:.2f} x {FH:.2f} mm  (BA={BA:.3f}, setback={S})")
    print(f"Corte: {corte / 1000:.2f} m lineares, {n} furos")
    print(info3d)
    if "valido" in info3d:
        v = s.Volume / 1e6  # dm3
        print(f"Massa: aco {v * 7.85:.2f} kg | aluminio {v * 2.7:.2f} kg")
