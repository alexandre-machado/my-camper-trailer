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
