"""
Pneu e roda paramétricos a partir da medida (ex.: "235/65R17").

Geometria pela norma da medida: largura de seção, altura do flanco = largura x série,
diâmetro = aro + 2 x flanco. Banda de rodagem com sulcos genéricos de pneu AT
(o desenho real de cada fabricante não é publicado — é só aproximação visual).

Eixo do pneu = Y, centro em (0, 0, 0). Rodar sozinho gera STEP + imagem:
    "C:\\Program Files\\FreeCAD 1.1\\bin\\freecadcmd.exe" cad\\pneu.py
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import OUT, render_3d, executado_direto  # noqa: E402

POL = 25.4

# índice de carga -> kg por pneu (faixa usual de SUV/caminhonete)
CARGA = {100: 800, 102: 850, 104: 900, 106: 950, 108: 1000, 110: 1060, 112: 1120,
         114: 1180, 116: 1250, 118: 1320, 120: 1400, 121: 1450}
VELOC = {"Q": 160, "R": 170, "S": 180, "T": 190, "H": 210, "V": 240}


class Medida:
    def __init__(self, txt):
        m = re.match(r"\s*(\d+)/(\d+)\s*Z?R\s*(\d+)(?:\s+(\d+)([A-Z]))?", txt.upper())
        if not m:
            raise ValueError(f"medida não reconhecida: {txt}")
        self.texto = txt
        self.largura = float(m.group(1))
        self.serie = float(m.group(2)) / 100
        self.aro_pol = float(m.group(3))
        self.carga = int(m.group(4)) if m.group(4) else None
        self.veloc = m.group(5)

    @property
    def flanco(self):
        return self.largura * self.serie

    @property
    def aro_d(self):
        return self.aro_pol * POL

    @property
    def diametro(self):
        return self.aro_d + 2 * self.flanco

    @property
    def tala_ideal_pol(self):
        """Largura de roda recomendada (aprox. 75–80% da seção, arredondada a 0,5")."""
        return round(self.largura * 0.78 / POL * 2) / 2

    def resumo(self):
        s = (f"{self.texto}: Ø {self.diametro:.0f} mm ({self.diametro / POL:.1f}\"), "
             f"largura {self.largura:.0f} mm, flanco {self.flanco:.0f} mm, roda {self.aro_pol:g}x{self.tala_ideal_pol:g}")
        if self.carga in CARGA:
            s += f", carga {CARGA[self.carga]} kg/pneu"
        if self.veloc in VELOC:
            s += f", até {VELOC[self.veloc]} km/h"
        return s


def _secao(m):
    """Seção transversal do pneu (face no plano YZ: y = lateral, z = raio) p/ revolver em Y."""
    import Part
    from FreeCAD import Vector as V

    W, R, Ra = m.largura, m.diametro / 2, m.aro_d / 2
    tala = m.tala_ideal_pol * POL
    banda = 0.82 * W               # largura da banda de rodagem
    r_bojo = Ra + 0.45 * m.flanco  # raio onde o flanco é mais largo
    # meia seção (lado +Y) desenhada em X=y, Z=r
    pts = [
        V(tala / 2, 0, Ra),                    # talão (encosta no flange da roda)
        V(tala / 2 + 6, 0, Ra + 0.12 * m.flanco),
        V(W / 2, 0, r_bojo),                   # bojo do flanco
        V(W / 2 - 4, 0, R - 0.22 * m.flanco),
        V(banda / 2 + 6, 0, R - 0.03 * m.flanco),
        V(banda / 2, 0, R),                    # ombro
    ]
    c1 = Part.BSplineCurve()
    c1.interpolate(pts)
    c2 = Part.BSplineCurve()
    c2.interpolate([V(-p.x, 0, p.z) for p in reversed(pts)])
    face = Part.Face(Part.Wire([c1.toShape(), Part.makeLine(V(banda / 2, 0, R), V(-banda / 2, 0, R)),
                                c2.toShape(), Part.makeLine(V(-tala / 2, 0, Ra), V(tala / 2, 0, Ra))]))
    face.rotate(V(0, 0, 0), V(0, 0, 1), 90)    # x(lateral) -> y
    return face


def _revolver(face):
    import Part
    from FreeCAD import Vector as V
    s = face.revolve(V(0, 0, 0), V(0, 1, 0), 360)
    return Part.Solid(Part.Shell(s.Faces)) if s.ShapeType != "Solid" else s


def _faixa(z0, z1, larg=2000):
    """Retângulo no plano YZ (p/ recortar a seção por faixa de raio)."""
    import Part
    from FreeCAD import Vector as V
    return Part.Face(Part.makePolygon([V(0, -larg, z0), V(0, larg, z0), V(0, larg, z1),
                                       V(0, -larg, z1), V(0, -larg, z0)]))


def pneu(medida, sulcos=True):
    """Pneu simplificado (rápido): seção revolvida + sulcos genéricos."""
    import Part
    from FreeCAD import Vector as V

    m = Medida(medida) if isinstance(medida, str) else medida
    W, R = m.largura, m.diametro / 2
    banda = 0.82 * W
    s = _revolver(_secao(m))
    if sulcos:
        prof = 11.0  # profundidade típica de AT novo (mm)
        cortes = []
        for y in (-0.17 * banda, 0.17 * banda):  # 2 sulcos circunferenciais
            cortes.append(Part.makeCylinder(R + 5, 9, V(0, y - 4.5, 0), V(0, 1, 0)).cut(
                Part.makeCylinder(R - prof, 9, V(0, y - 4.5, 0), V(0, 1, 0))))
        n = 44  # sulcos transversais alternados, entrando pelo ombro
        for i in range(n):
            lado = 1 if i % 2 else -1
            y0 = 0.05 * banda if lado > 0 else -(W / 2 + 10)
            caixa = Part.makeBox(9, W / 2 + 10 - 0.05 * banda, prof + 10, V(-4.5, y0, R - prof))
            caixa.rotate(V(0, 0, 0), V(0, 1, 0), 360 * i / n)
            cortes.append(caixa)
        s = s.cut(Part.makeCompound(cortes))
    return s


def _bloco(u0, u1, y0, y1, d=6):
    """Contorno (u, y) de um bloco escalonado em "Z" (dá o aspecto de blocos que se encaixam)."""
    ym = (y0 + y1) / 2
    return [(u0, y0), (u1 - d, y0), (u1 - d, ym - 2), (u1, ym + 2), (u1, y1),
            (u0 + d, y1), (u0 + d, ym + 2), (u0, ym - 2)]


def _face_letra(wires):
    """Face de uma letra a partir dos contornos da fonte: contornos dentro de outro são furos
    (P, A, R, ...), os demais são partes cheias (o pingo do i, etc.)."""
    import Part
    faces = sorted((Part.Face(Part.Wire(w.Edges)) for w in wires), key=lambda f: -f.Area)
    cheias, furos = [], []
    for f in faces:
        dentro = any(g.BoundBox.isInside(f.BoundBox) and g.Area > f.Area and
                     g.isInside(f.CenterOfMass, 0.01, True) for g in faces if g is not f)
        (furos if dentro else cheias).append(f)
    letra = cheias[0].fuse(cheias[1:]) if len(cheias) > 1 else cheias[0]
    if furos:
        letra = letra.cut(furos)
    return Part.Face(letra.Faces[0].Wires) if len(letra.Faces) == 1 else letra


def pneu_at(medida, n_passos=32, prof=12.0, garra=6.0, letras=True, com_lamelas=True,
            fonte="C:/Windows/Fonts/impact.ttf"):
    """Pneu AT detalhado, inspirado no Speedmax Prime Pangea AT (fotos em pneu/).

    - banda: 3 fileiras de blocos escalonados por lado, alternadas meio passo entre os lados
      (o centro vira um zigue-zague);
    - ombro: blocos que descem pelo flanco (garras laterais), alternando longos e curtos;
    - flanco externo (+Y): letras em relevo "PANGEA / ALL-TERRAIN" e "SPEEDMAX PRIME".
    Retorna (borracha, letras) — letras separadas p/ poder pintar de branco (ou None).
    """
    import Part
    from FreeCAD import Vector as V

    m = Medida(medida) if isinstance(medida, str) else medida
    W, R = m.largura, m.diametro / 2
    sec = _secao(m)
    z_garra = R - 0.36 * m.flanco                   # até onde as garras longas descem

    # corpo = seção sem a camada da banda; envelope = contorno externo + relevo das garras no flanco
    corpo = _revolver(sec.common(_faixa(0, R - prof)))
    env_sec = sec.fuse(sec.makeOffset2D(garra).common(_faixa(z_garra, R))).removeSplitter()
    env_sec = Part.Face(env_sec.Faces[0].OuterWire) if len(env_sec.Faces) == 1 else env_sec
    envelope = _revolver(env_sec)

    p = 2 * math.pi * R / n_passos     # passo na circunferência
    g = 8.0                            # largura dos sulcos
    y_fim = W / 2 + garra + 5
    blocos, lamelas = [], []

    def _lamela(zz, lado, z0, z1, ang_):
        """Corte fino (1,2 mm) seguindo a linha em zigue-zague."""
        partes = []
        for (u0, y0), (u1, y1) in zip(zz, zz[1:]):
            dy, du = y1 - y0, u1 - u0
            L = math.hypot(du, dy)
            nu, ny = -dy / L * 0.6, du / L * 0.6   # meia espessura na normal da linha
            q = [(u0 + nu, y0 + ny), (u1 + nu, y1 + ny), (u1 - nu, y1 - ny), (u0 - nu, y0 - ny)]
            partes.append(prisma([(u, lado * y) for u, y in q], z0, ang_, z1))
        return Part.makeCompound(partes)

    def prisma(contorno, z0, ang, z1=None):
        poly = Part.makePolygon([V(u, y, z0) for u, y in contorno] + [V(contorno[0][0], contorno[0][1], z0)])
        b = Part.Face(poly).extrude(V(0, 0, (z1 if z1 is not None else R + 8) - z0))
        b.rotate(V(0, 0, 0), V(0, 1, 0), ang)
        return b

    for k in range(n_passos):
        for lado in (+1, -1):
            meio_passo = 0.5 if lado < 0 else 0.0
            def ang(desloc):
                return math.degrees((k + desloc + meio_passo) * p / R)
            u0, u1 = -p / 2 + g / 2, p / 2 - g / 2
            linhas = [
                (_bloco(u0, u1, 2, 30), R - prof - 2, ang(0)),          # centro
                (_bloco(u0, u1, 38, 64), R - prof - 2, ang(0.5)),       # intermediária (defasada)
            ]
            z_omb = z_garra if k % 2 == 0 else R - 0.22 * m.flanco   # garras longas/curtas alternadas
            linhas.append((_bloco(u0 + 3, u1 - 3, 72, y_fim, d=5), z_omb, ang(0)))
            for n_l, (cont, z0, a) in enumerate(linhas):
                blocos.append(prisma([(u, lado * y) for u, y in cont], z0, a))
                if com_lamelas and n_l < 2:  # lamela em zigue-zague atravessando o bloco (centro e intermediária)
                    ys = [y for _, y in cont]
                    ya, yb = min(ys) + 4, max(ys) - 4
                    zz = [(-3, ya), (3, ya + (yb - ya) / 3), (-3, ya + 2 * (yb - ya) / 3), (3, yb)]
                    lamelas.append(_lamela(zz, lado, R - 8, R + 8, a))

    relevo = envelope.common(Part.makeCompound(blocos)).cut(Part.makeCompound(lamelas))
    borracha = corpo.fuse(relevo).removeSplitter()

    texto = None
    if letras and os.path.exists(fonte):
        def y_flanco(r):
            linha = Part.makeLine(V(0, 0, r), V(0, W, r)).common(sec)
            return max(v.Point.y for v in linha.Vertexes)

        def arco(txt, alt, r, centro_graus):
            fs = []
            for chars in Part.makeWireString(txt, fonte, alt, 0):
                if chars:
                    fs.append(_face_letra(chars))
            larg = max(f.BoundBox.XMax for f in fs)
            y0 = y_flanco(r) - 8.0  # base dentro do flanco; o relevo sai do recorte abaixo
            solidos = []
            for f in fs:
                cx = (f.BoundBox.XMin + f.BoundBox.XMax) / 2
                c = f.extrude(V(0, 0, 25))
                c.translate(V(-cx, 0, 0))
                c.rotate(V(0, 0, 0), V(1, 0, 0), 90)   # plano XY -> XZ, extrusão p/ -Y
                c.rotate(V(0, 0, 0), V(0, 0, 1), 180)  # lê certo vendo de +Y; extrusão p/ +Y
                c.translate(V(0, y0, r))
                desloc = cx - larg / 2                  # posição ao longo do texto (p/ a direita de quem olha)
                c.rotate(V(0, 0, 0), V(0, 1, 0), centro_graus - math.degrees(desloc / r))
                solidos.append(c)
            return solidos

        # letras na parte lisa do flanco, abaixo das garras; relevo de 1,5 mm acompanhando a curva
        r_txt = z_garra - 4 - 38
        let = (arco("PANGEA", 38, r_txt, -55) + arco("ALL-TERRAIN", 14, r_txt - 20, -55)
               + arco("SPEEDMAX PRIME", 18, r_txt + 8, 80))
        casca = _revolver(sec.makeOffset2D(1.5))
        texto = casca.common(Part.makeCompound(let))
    return borracha, texto


def roda(medida, pcd=139.7, n_pinos=6, cb=106.1, et=0.0):
    """Roda de aço simples: aro + disco com furação. Face de montagem em y = et."""
    import Part
    from FreeCAD import Vector as V

    m = Medida(medida) if isinstance(medida, str) else medida
    Ra, tala = m.aro_d / 2, m.tala_ideal_pol * POL
    aro = Part.makeCylinder(Ra + 12, tala, V(0, -tala / 2, 0), V(0, 1, 0)).cut(
        Part.makeCylinder(Ra - 6, tala + 2, V(0, -tala / 2 - 1, 0), V(0, 1, 0)))
    aro = aro.cut(Part.makeCylinder(Ra + 13, tala - 30, V(0, -tala / 2 + 15, 0), V(0, 1, 0)).cut(
        Part.makeCylinder(Ra, tala - 30, V(0, -tala / 2 + 15, 0), V(0, 1, 0))))   # flanges de 15 mm
    disco = Part.makeCylinder(Ra - 6, 10, V(0, et, 0), V(0, 1, 0))
    furos = [Part.makeCylinder(cb / 2, 12, V(0, et - 1, 0), V(0, 1, 0))]
    for i in range(n_pinos):
        a = 2 * math.pi * i / n_pinos
        furos.append(Part.makeCylinder(7, 12, V(pcd / 2 * math.cos(a), et - 1, pcd / 2 * math.sin(a)), V(0, 1, 0)))
    for i in range(8):  # janelas de ventilação
        a = 2 * math.pi * (i + 0.5) / 8
        rr = (pcd / 2 + Ra) / 2 + 10
        furos.append(Part.makeCylinder(22, 12, V(rr * math.cos(a), et - 1, rr * math.sin(a)), V(0, 1, 0)))
    return aro.fuse(disco.cut(furos))


if executado_direto(__name__, __file__):
    import Part
    MEDIDA = next((a for a in sys.argv if re.match(r"\d+/\d+", a)), "235/65R17 108H")
    m = Medida(MEDIDA)
    p, letras = pneu_at(m)
    r = roda(m)
    os.makedirs(OUT, exist_ok=True)
    nome = "pneu_" + re.sub(r"[^0-9A-Za-z]", "_", MEDIDA)
    Part.makeCompound([x for x in (p, letras, r) if x]).exportStep(os.path.join(OUT, nome + ".step"))
    print(m.resumo())
    print(f"sólido válido: {p.isValid()} | volume borracha {p.Volume / 1e6:.1f} L | "
          f"letras: {len(letras.Solids) if letras else 0}")
    itens = [("#262626", p), ("#9aa5ad", r)] + ([("#e8e8e8", letras)] if letras else [])
    render_3d(itens, os.path.join(OUT, nome + ".png"), vistas=((15, 30), (3, 90), (0, 0)),
              titulo=m.resumo(), tamanho=(6, 6), tol=0.8)
