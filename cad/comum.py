"""Utilitários compartilhados: perfis tubulares (3D), chapas (DXF) e previews."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
sys.path.append(os.path.join(HERE, "_pylibs"))  # ezdxf local (append: numpy do FreeCAD tem prioridade)

import ezdxf  # noqa: E402

ACO = 7.85e-6  # kg/mm3


# ---------------------------------------------------------------- perfis
class Perfil:
    """Tubo retangular (RHS/metalon). b = largura (lateral), h = altura, e = parede (mm)."""

    def __init__(self, b, h, e):
        self.b, self.h, self.e = b, h, e

    @property
    def nome(self):
        return f"RHS {self.h:g}x{self.b:g}x{self.e:g}"

    @property
    def area(self):  # mm2, ignorando raio de canto
        return self.b * self.h - (self.b - 2 * self.e) * (self.h - 2 * self.e)

    def kg_m(self):
        return self.area * ACO * 1000


def tubo(perfil, p0, p1, deitado=False):
    """Sólido do tubo com a linha de centro de p0 a p1.
    A altura h fica no eixo Z (ou no Y lateral se deitado=True)."""
    import Part
    from FreeCAD import Placement, Rotation, Vector as V

    p0, p1 = V(*p0), V(*p1)
    d = p1 - p0
    L = d.Length
    b, h = (perfil.h, perfil.b) if deitado else (perfil.b, perfil.h)
    e = perfil.e
    ext = Part.makeBox(L, b, h, V(0, -b / 2, -h / 2))
    inn = Part.makeBox(L + 2, b - 2 * e, h - 2 * e, V(-1, -b / 2 + e, -h / 2 + e))
    s = ext.cut(inn)
    s.Placement = Placement(p0, Rotation(V(1, 0, 0), d))
    return s, L


class Tubo:
    """Tubo horizontal (altura h em Z) com encaixes macho-fêmea para laser tubular.

    A geometria fica no referencial local (eixo do tubo = +X, de 0 a L, centrado em Y/Z)
    e a posição no chassi em `pl`. Assim cada peça pode ser exportada "deitada" para a máquina.
    """

    FOLGA = 0.25   # folga por lado do rasgo em relação à lingueta (mm)
    SALTO = 2.0    # quanto a lingueta passa da parede do outro tubo (mm, fica por dentro)

    def __init__(self, nome, perfil, p0, p1):
        import Part
        from FreeCAD import Placement, Rotation, Vector as V

        self.nome, self.perfil = nome, perfil
        self.p0, self.p1 = V(*p0), V(*p1)
        d = self.p1 - self.p0
        assert abs(d.z) < 1e-6, "Tubo: só tubos horizontais"
        self.L = d.Length
        self.pl = Placement(self.p0, Rotation(V(1, 0, 0), d))
        b, h, e = perfil.b, perfil.h, perfil.e
        self.loc = Part.makeBox(self.L, b, h, V(0, -b / 2, -h / 2)).cut(
            Part.makeBox(self.L + 2, b - 2 * e, h - 2 * e, V(-1, -b / 2 + e, -h / 2 + e)))
        self.machos, self.femeas = 0, 0
        self.nota = ""

    @property
    def shape(self):
        s = self.loc.copy()
        s.Placement = self.pl
        return s

    def encaixar(self, ponta, outro):
        """Linguetas na ponta (0 = p0, 1 = p1) deste tubo + rasgos na parede do `outro`.
        Uma lingueta por parede lateral; a que cairia na ponta aberta do outro tubo é omitida.
        Retorna o nº de linguetas (0/False = solda de topo simples)."""
        import Part
        from FreeCAD import Vector as V

        a, b = self.perfil, outro.perfil
        za, zb = self.p0.z, outro.p0.z
        # faixa de altura plana comum às duas paredes (descontando o raio de canto ~2e)
        lo = max(za - (a.h / 2 - 2 * a.e), zb - (b.h / 2 - 2 * b.e))
        hi = min(za + (a.h / 2 - 2 * a.e), zb + (b.h / 2 - 2 * b.e))
        alt = min(0.4 * a.h, 0.6 * (hi - lo))
        if alt < 10:
            return False
        zc = (lo + hi) / 2 - za
        comp = b.e + self.SALTO
        x0 = self.L if ponta == 1 else -comp

        linguetas, rasgos = [], []
        f = self.FOLGA
        for lado in (+1, -1):
            y0 = a.b / 2 - a.e if lado > 0 else -a.b / 2
            rasgo = Part.makeBox(comp + 1, a.e + 2 * f, alt + 2 * f,
                                 V(x0 - (0 if ponta == 1 else 1), y0 - f, zc - alt / 2 - f))
            # rasgo no referencial do outro tubo; precisa ficar longe das pontas dele
            rasgo.Placement = outro.pl.inverse().multiply(self.pl)
            bb = rasgo.BoundBox
            if bb.XMin < 2 * b.e or bb.XMax > outro.L - 2 * b.e:
                continue
            linguetas.append(Part.makeBox(comp, a.e, alt, V(x0, y0, zc - alt / 2)))
            rasgos.append(rasgo)
        if not linguetas:
            return False
        self.loc = self.loc.fuse(linguetas).removeSplitter()
        outro.loc = outro.loc.cut(rasgos)
        self.machos += len(linguetas)
        outro.femeas += len(rasgos)
        return len(linguetas)


class TuboDobrado:
    """Tubo com cantos de 90° feitos por corte em V + dobra (notch and bend).

    `pontos` = linha de centro (vértices nos cantos, todas as curvas para o mesmo lado).
    Cada trecho é um `Tubo` (para receber/fazer encaixes macho-fêmea). A peça para o laser
    (`loc`) é o tubo reto planificado: o V corta as paredes de cima, de baixo e a interna,
    e a parede externa fica inteira e é dobrada.
    """

    K = 0.33  # posição da linha neutra na parede dobrada -> CALIBRAR com peça de teste

    def __init__(self, nome, perfil, pontos):
        self.nome, self.perfil = nome, perfil
        self.segs = [Tubo(f"{nome} [{i}]", perfil, pontos[i], pontos[i + 1]) for i in range(len(pontos) - 1)]
        giros = set()
        for s1, s2 in zip(self.segs, self.segs[1:]):
            d1, d2 = (s1.p1 - s1.p0).normalize(), (s2.p1 - s2.p0).normalize()
            assert abs(d1.dot(d2)) < 1e-6, "TuboDobrado: só cantos de 90°"
            giros.add(1 if d1.cross(d2).z > 0 else -1)
        assert len(giros) == 1, "TuboDobrado: todas as dobras para o mesmo lado"
        self.t = giros.pop()                      # +1 = vira à esquerda (lado interno = +y local)
        self.d = perfil.b / 2 - perfil.e          # linha de centro -> face interna da parede externa
        self.BA = math.pi / 2 * self.K * perfil.e  # comprimento desenvolvido da parede dobrada
        self.n_dobras = len(self.segs) - 1
        self.nota = f"{self.n_dobras} dobra(s) em V a 90°"

    @property
    def machos(self):
        return sum(s.machos for s in self.segs)

    @property
    def femeas(self):
        return sum(s.femeas for s in self.segs)

    def _origens(self):
        o, res = 0.0, []
        for s in self.segs:
            res.append(o)
            o += s.L + 2 * self.d + self.BA
        return res

    @property
    def L(self):
        return self._origens()[-1] + self.segs[-1].L

    def _feicoes(self, seg):
        """Linguetas (a somar) e rasgos (a subtrair) do trecho, no referencial dele."""
        lisa = Tubo("_", self.perfil, (0, 0, 0), (seg.L, 0, 0)).loc
        return seg.loc.cut(lisa), lisa.cut(seg.loc)

    def _prisma(self, pts):
        import Part
        from FreeCAD import Vector as V
        h = self.perfil.h / 2 + 1
        poly = Part.makePolygon([V(x, y, -h) for x, y in pts] + [V(pts[0][0], pts[0][1], -h)])
        return Part.Face(poly).extrude(V(0, 0, 2 * h))

    @property
    def loc(self):
        """Tubo reto planificado com os V, linguetas e rasgos (o que vai para o laser tubular)."""
        p, t, B = self.perfil, self.t, self.perfil.b
        s = Tubo("_", p, (0, 0, 0), (self.L, 0, 0)).loc
        for o, seg in zip(self._origens(), self.segs):
            mais, menos = self._feicoes(seg)
            s = s.fuse(mais.translated(_v(o, 0, 0))).cut(menos.translated(_v(o, 0, 0)))
        ya, yi = -t * (B / 2 - p.e), t * (B / 2 + 1)
        w = abs(yi - ya)  # V de 90°: abertura de 45° para cada lado
        for o, seg in zip(self._origens()[:-1], self.segs[:-1]):
            xc = o + seg.L + self.d + self.BA / 2
            s = s.cut(self._prisma([(xc - self.BA / 2, ya), (xc + self.BA / 2, ya),
                                    (xc + self.BA / 2 + w, yi), (xc - self.BA / 2 - w, yi)]))
        return s.removeSplitter()

    @property
    def shape(self):
        """Peça dobrada na posição do chassi (trechos em meia-esquadria no canto)."""
        import Part
        p, t, B, n = self.perfil, self.t, self.perfil.b, len(self.segs)
        partes = []
        for i, seg in enumerate(self.segs):
            xa = -B / 2 if i > 0 else 0
            xb = seg.L + B / 2 if i < n - 1 else seg.L
            s = Tubo("_", p, (xa, 0, 0), (xb, 0, 0)).loc.translated(_v(xa, 0, 0))
            mais, menos = self._feicoes(seg)
            s = s.fuse(mais).cut(menos)
            if i > 0:
                s = s.common(self._prisma([(-t * B, -B), (1e4, -B), (1e4, B), (t * B, B)]))
            if i < n - 1:
                L = seg.L
                s = s.common(self._prisma([(-1e4, -B), (L + t * B, -B), (L - t * B, B), (-1e4, B)]))
            s.Placement = seg.pl
            partes.append(s)
        return Part.makeCompound(partes)


def _v(x, y, z):
    from FreeCAD import Vector
    return Vector(x, y, z)


def agrupar_iguais(tubos):
    """Agrupa peças idênticas (inclusive girando 180° no próprio eixo). Retorna [[Tubo, ...], ...]."""
    from FreeCAD import Placement, Rotation, Vector as V

    giro = Placement(V(0, 0, 0), Rotation(V(1, 0, 0), 180))

    def igual(t1, t2):
        if t1.perfil.nome != t2.perfil.nome or abs(t1.L - t2.L) > 0.5 \
                or abs(t1.loc.Volume - t2.loc.Volume) > 1:
            return False
        for pl in (None, giro):
            s = t2.loc.copy()
            if pl:
                s.Placement = pl
            if abs(t1.loc.common(s).Volume - t1.loc.Volume) < 1:
                return True
        return False

    grupos = []
    for t in tubos:
        for g in grupos:
            if igual(g[0], t):
                g.append(t)
                break
        else:
            grupos.append([t])
    return grupos


class ListaCorte:
    def __init__(self):
        self.itens = []  # (peca, perfil, comprimento, qtd, obs)

    def add(self, peca, perfil, comprimento, qtd=1, obs=""):
        self.itens.append((peca, perfil, comprimento, qtd, obs))

    def salvar_csv(self, caminho):
        total = 0.0
        with open(caminho, "w", encoding="utf-8-sig") as f:
            f.write("peca;perfil;comprimento_mm;qtd;massa_kg;obs\n")
            for peca, p, L, q, obs in self.itens:
                m = p.kg_m() * L / 1000 * q
                total += m
                f.write(f"{peca};{p.nome};{L:.0f};{q};{m:.1f}".replace(".", ",") + f";{obs}\n")
        return total

    def resumo_barras(self, barra=6000, serra=4):
        """Metros por perfil e nº de barras (encaixe first-fit decreasing, com perda da serra)."""
        por = {}
        for _, p, L, q, _ in self.itens:
            por.setdefault(p.nome, []).extend([L] * q)
        res = {}
        for nome, pecas in por.items():
            sobras = []
            for L in sorted(pecas, reverse=True):
                for i, s in enumerate(sobras):
                    if s >= L + serra:
                        sobras[i] -= L + serra
                        break
                else:
                    sobras.append(barra - L - serra)
            res[nome] = (sum(pecas) / 1000, len(sobras))
        return res


# ---------------------------------------------------------------- DXF
def novo_dxf():
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.layers.add("CORTE", color=1)
    doc.layers.add("DOBRA", color=2, linetype="DASHED")
    doc.layers.add("INFO", color=8)
    return doc


def bulge_canto(rr, x0, y0, x1, y1):
    """Vértices xyb de um retângulo com cantos arredondados (raio rr)."""
    b = math.tan(math.pi / 8)
    return [
        (x0 + rr, y0, 0), (x1 - rr, y0, b), (x1, y0 + rr, 0), (x1, y1 - rr, b),
        (x1 - rr, y1, 0), (x0 + rr, y1, b), (x0, y1 - rr, 0), (x0, y0 + rr, b),
    ]


def comprimento_corte(msp):
    total, furos = 0.0, 0
    for e in msp.query('*[layer=="CORTE"]'):
        if e.dxftype() == "CIRCLE":
            total += 2 * math.pi * e.dxf.radius
            furos += 1
        elif e.dxftype() == "LWPOLYLINE":
            assert e.closed, "contorno aberto!"
            for s in e.virtual_entities():
                if s.dxftype() == "LINE":
                    total += (s.dxf.end - s.dxf.start).magnitude
                elif s.dxftype() == "ARC":
                    total += math.radians((s.dxf.end_angle - s.dxf.start_angle) % 360) * s.dxf.radius
    return total, furos


# ---------------------------------------------------------------- preview
def preview_vistas(grupos, caminho, titulo=""):
    """Desenha arestas dos sólidos em vista superior, lateral e traseira (sem GUI)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 3, figsize=(20, 6.5), gridspec_kw={"width_ratios": [3.8, 3.8, 2]})
    vistas = [("Superior (X, Y)", 0, 1), ("Lateral (X, Z)", 0, 2), ("Traseira (Y, Z)", 1, 2)]
    for ax, (nome, i, j) in zip(axs, vistas):
        for cor, solidos in grupos:
            for s in solidos:
                for ed in s.Edges:
                    pts = ed.discretize(12)
                    ax.plot([p[i] for p in pts], [p[j] for p in pts], color=cor, lw=0.5)
        ax.set_title(nome)
        ax.set_aspect("equal")
        ax.grid(alpha=0.3)
    axs[1].axhline(0, color="k", lw=1)
    axs[2].axhline(0, color="k", lw=1)
    fig.suptitle(titulo)
    fig.tight_layout()
    fig.savefig(caminho, dpi=110)
