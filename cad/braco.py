"""
Suspensão própria: braço arrastado (trailing arm) independente, mola helicoidal + amortecedor.

Cada roda pendura num braço que gira num pivô transversal à frente dela. Como o pivô é
perpendicular ao chassi, a roda sobe e desce sem mudar câmber nem convergência (só anda um
pouco para trás/frente no arco). Os parafusos do pivô em furo oblongo/excêntrico ajustam a
convergência no alinhamento.

Ponta de eixo: cubo com rolamento integrado de carro (Toro/Compass, 5x110) aparafusado num
flange soldado na ponta do braço -> mesma roda e estepe do carro, peças de reposição comuns.
Freio a disco do mesmo cubo (Ø278 Toro diesel).

Cinemática: "dz" = deslocamento vertical da roda a partir da posição estática carregada (+ sobe).
Coordenadas do chassi: X da traseira para a frente, Y lateral, Z do chão (mm).

ATENÇÃO: cargas e molas são pré-dimensionamento p/ escolher peças e espaço; braço, pivô e suportes
precisam de cálculo estrutural (cargas de impacto off-road ~3 g) por engenheiro.
"""
import math

import veiculo
from comum import Perfil, tubo

# ---------------------------------------------------------------- cargas de projeto (kg)
PBT = veiculo.REBOQUE_COM_FREIO     # carreta carregada no limite do Compass
CARGA_BOLA = veiculo.CARGA_BOLA     # parte do peso que vai para o carro (alivia o eixo)
TARA = 900                          # ESTIMATIVA da carreta vazia (atualizar com o orçamento de peso)
NAO_SUSPENSA = 50                   # por roda: pneu+roda ~25, cubo/disco/pinça ~14, ~meio braço — ESTIMADO
FREQ_ALVO = 1.5                     # Hz carregada (off-road/conforto: 1,3-1,8; carro de passeio ~1,2)
G = 9.81

# ---------------------------------------------------------------- curso (mm, na roda)
CURSO_COMPRESSAO = 100              # acima da posição estática carregada
CURSO_EXTENSAO = 110                # abaixo

# ---------------------------------------------------------------- geometria
PERFIL = Perfil(75, 120, 5)         # braço: RHS 120x75x5
COMPR = 500                         # pivô -> centro da roda (horizontal, estático)
Z_PIVO = 480
Y_BRACO = 545.5                     # centro do braço (por fora da longarina, por dentro do pneu)
PONTA_ATRAS = 60                    # braço passa do centro da roda p/ trás
CHAPA_E = 8                         # chapas cortadas a laser
BUCHA_D, BUCHA_L = 60, 120          # bucha do pivô (tipo bucha de bandeja, poliuretano/borracha)
MOLA_D, MOLA_DX, Y_MOLA = 140, 50, 430   # mola: Ø externo, à frente do eixo, centro (por dentro do braço)
AMORT_INF_DX = -80                  # olhal inferior: em cima do braço, atrás do eixo
AMORT_SUP = (250, 680)              # olhal superior: (à frente do eixo, Z) — na lateral da longarina, abaixo do assoalho
AMORT_D = 50
CUBO_FLANGE = 75                    # do flange soldado até a face de apoio da roda (cubo de carro)
DISCO_D, DISCO_E, DISCO_RECUO = 278, 12, 45   # disco e recuo da pista em relação à face da roda


class Cinematica:
    """Giro do braço em torno do pivô (plano XZ)."""

    def __init__(self, x_eixo, z_roda):
        self.px, self.pz = x_eixo + COMPR, Z_PIVO
        self.x_eixo, self.z_roda = x_eixo, z_roda
        self.R = math.hypot(x_eixo - self.px, z_roda - self.pz)
        self.a0 = math.atan2(z_roda - self.pz, x_eixo - self.px)

    def phi(self, dz):
        """Ângulo (rad) que o braço gira p/ a roda subir dz. Sentido: aumenta o ângulo medido de +X p/ +Z."""
        a = math.pi - math.asin((self.z_roda + dz - self.pz) / self.R)
        a = a - 2 * math.pi if a - self.a0 > math.pi else a
        return a - self.a0

    def ponto(self, x, z, phi):
        dx, dz = x - self.px, z - self.pz
        c, s = math.cos(phi), math.sin(phi)
        return self.px + dx * c - dz * s, self.pz + dx * s + dz * c


def _z_braco(cin, x):
    """Z da linha de centro do braço (estático) na posição x."""
    x0, z0 = cin.x_eixo - PONTA_ATRAS, cin.z_roda - 6
    return z0 + (cin.pz - z0) * (x - x0) / (cin.px - x0)


def pontos(cin, z_chassi, dz=0.0):
    """Pontos-chave (plano XZ) com a roda deslocada dz."""
    f = cin.phi(dz)
    xm = cin.x_eixo + MOLA_DX
    xa = cin.x_eixo + AMORT_INF_DX
    p = {
        "roda": cin.ponto(cin.x_eixo, cin.z_roda, f),
        "mola_inf": cin.ponto(xm, _z_braco(cin, xm) - PERFIL.h / 2, f),
        "amort_inf": cin.ponto(xa, _z_braco(cin, xa) + PERFIL.h / 2 + 45, f),
        "ponta": cin.ponto(cin.x_eixo - PONTA_ATRAS, cin.z_roda - 6, f),
    }
    p["mola_sup"] = (xm, z_chassi - CHAPA_E)
    p["amort_sup"] = (cin.x_eixo + AMORT_SUP[0], AMORT_SUP[1])
    p["L_mola"] = p["mola_sup"][1] - p["mola_inf"][1]
    p["L_amort"] = math.dist(p["amort_inf"], p["amort_sup"])
    return p


def analise(x_eixo, z_roda, z_chassi, pneu_d):
    """Pré-dimensionamento de mola, amortecedor e batentes. Retorna dict."""
    cin = Cinematica(x_eixo, z_roda)
    est, comp, ext = (pontos(cin, z_chassi, d) for d in (0, CURSO_COMPRESSAO, -CURSO_EXTENSAO))
    h = 1.0
    mr_mola = (pontos(cin, z_chassi, -h)["L_mola"] - pontos(cin, z_chassi, h)["L_mola"]) / (2 * h)
    mr_amort = (pontos(cin, z_chassi, -h)["L_amort"] - pontos(cin, z_chassi, h)["L_amort"]) / (2 * h)

    m_carr = (PBT - CARGA_BOLA) / 2 - NAO_SUSPENSA          # massa suspensa por roda, carregada
    m_vazio = (TARA - CARGA_BOLA * TARA / PBT) / 2 - NAO_SUSPENSA
    k_roda = (2 * math.pi * FREQ_ALVO) ** 2 * m_carr / 1000  # N/mm na roda
    k_mola = k_roda / mr_mola ** 2
    f_mola = m_carr * G / mr_mola                            # força estática na mola (N)
    compressao_est = f_mola / k_mola
    r = dict(
        cin=cin, est=est, comp=comp, ext=ext, mr_mola=mr_mola, mr_amort=mr_amort,
        m_carr=m_carr, m_vazio=m_vazio, k_roda=k_roda, k_mola=k_mola, f_mola=f_mola,
        f_vazio=math.sqrt(k_roda * 1000 / m_vazio) / (2 * math.pi),
        sobe_vazio=(m_carr - m_vazio) * G / k_roda,          # quanto a carreta vazia fica mais alta
        mola_livre=est["L_mola"] + compressao_est,
        mola_bloco_max=comp["L_mola"] - 10,                  # comprimento sólido tem que caber no fim do curso
        f_mola_max=f_mola + k_mola * (est["L_mola"] - comp["L_mola"]),
        amort_fechado_max=comp["L_amort"] - 10,
        amort_aberto_min=ext["L_amort"] + 5,
        topo_pneu_comp=comp["roda"][1] + pneu_d / 2,
    )
    r["amort_curso_min"] = r["amort_aberto_min"] - r["amort_fechado_max"]
    return r


def suspensao(x_eixo, y_roda, z_roda, z_chassi, y_long, longarina_b, et=0.0, dz=0.0):
    """Monta os dois lados com a roda deslocada dz. Retorna (soldado, comprados, info, comprimento_braco).
    Peças que giram com o braço são feitas na posição estática e giradas em torno do pivô."""
    import Part
    from FreeCAD import Vector as V

    cin = Cinematica(x_eixo, z_roda)
    f = cin.phi(dz)
    p = pontos(cin, z_chassi, dz)
    piv = V(cin.px, 0, cin.pz)
    soldado, comprados = [], []
    y_face_roda = y_roda + et                               # face de apoio da roda no cubo

    def gira(sh):
        sh.rotate(piv, V(0, -1, 0), math.degrees(f))
        return sh

    for s in (+1, -1):
        yb = s * Y_BRACO
        movel_sold, movel_comp = [], []
        # braço
        t, L = tubo(PERFIL, (x_eixo - PONTA_ATRAS, yb, z_roda - 6), (cin.px, yb, cin.pz))
        movel_sold.append(t)
        # luva do pivô (tubo Ø89x6 atravessado) + bucha
        movel_sold.append(Part.makeCylinder(44.5, BUCHA_L, V(cin.px, yb - BUCHA_L / 2, cin.pz), V(0, 1, 0)).cut(
            Part.makeCylinder(BUCHA_D / 2 + 8, BUCHA_L, V(cin.px, yb - BUCHA_L / 2, cin.pz), V(0, 1, 0))))
        movel_comp.append(Part.makeCylinder(BUCHA_D / 2 + 8, BUCHA_L, V(cin.px, yb - BUCHA_L / 2, cin.pz), V(0, 1, 0)))
        # ponta de eixo: tubo-manga soldado na face externa do braço + flange p/ o cubo de carro
        y_braco_ext = s * (Y_BRACO + PERFIL.b / 2)
        y_flange = s * (abs(y_face_roda) - CUBO_FLANGE)
        Lm = abs(y_flange - y_braco_ext) - 12   # tubo Ø90x10 (ou mecânico usinado)
        movel_sold.append(Part.makeCylinder(45, Lm, V(x_eixo, y_braco_ext, z_roda), V(0, s, 0)).cut(
            Part.makeCylinder(35, Lm, V(x_eixo, y_braco_ext, z_roda), V(0, s, 0))))
        movel_sold.append(Part.makeBox(150, 12, 150, V(x_eixo - 75, y_flange - (12 if s > 0 else 0), z_roda - 75)))
        # cubo (rolamento integrado) + disco com chapéu + pinça (atrás/em cima)
        movel_comp.append(Part.makeCylinder(62, CUBO_FLANGE - 10, V(x_eixo, y_flange, z_roda), V(0, s, 0)))
        movel_comp.append(Part.makeCylinder(70, 10, V(x_eixo, s * (abs(y_face_roda) - 10), z_roda), V(0, s, 0)))
        y_disco = s * (abs(y_face_roda) - DISCO_RECUO)
        movel_comp.append(Part.makeCylinder(DISCO_D / 2, DISCO_E, V(x_eixo, y_disco, z_roda), V(0, s, 0)).cut(
            Part.makeCylinder(80, DISCO_E, V(x_eixo, y_disco, z_roda), V(0, s, 0))))
        movel_comp.append(Part.makeCylinder(82, DISCO_RECUO - 10, V(x_eixo, y_disco, z_roda), V(0, s, 0)).cut(
            Part.makeCylinder(76, DISCO_RECUO - 10, V(x_eixo, y_disco, z_roda), V(0, s, 0))))
        ang = math.radians(135)   # pinça atrás e em cima (longe do chão e de pedras)
        cx, cz = x_eixo + (DISCO_D / 2 - 30) * math.cos(ang), z_roda + (DISCO_D / 2 - 30) * math.sin(ang)
        pin = Part.makeBox(60, 50, 110, V(cx - 30, y_disco + DISCO_E / 2 * s - 25, cz - 55))
        pin.rotate(V(cx, 0, cz), V(0, -1, 0), math.degrees(ang) - 90)
        movel_comp.append(pin)
        # suporte da pinça: chapa do flange até a pinça
        sup_pin = Part.makeBox(60, 10, 120, V(cx - 30, y_flange - (10 if s > 0 else 0), cz - 60))
        sup_pin.rotate(V(cx, 0, cz), V(0, -1, 0), math.degrees(ang) - 90)
        movel_sold.append(sup_pin)
        # prato inferior da mola: chapa em balanço por dentro do braço
        xm = x_eixo + MOLA_DX
        zi = _z_braco(cin, xm) - PERFIL.h / 2
        y0, y1 = sorted((s * (Y_MOLA - 90), s * (Y_BRACO + PERFIL.b / 2)))
        movel_sold.append(Part.makeBox(180, y1 - y0, CHAPA_E, V(xm - 90, y0, zi - CHAPA_E)))
        # orelhas do olhal inferior do amortecedor (em cima do braço)
        xa = x_eixo + AMORT_INF_DX
        za = _z_braco(cin, xa) + PERFIL.h / 2
        for dy in (-1, 1):
            movel_sold.append(Part.makeBox(70, CHAPA_E, 65, V(xa - 35, yb + dy * 30 - CHAPA_E / 2, za - 5)))

        soldado += [gira(sh) for sh in movel_sold]
        comprados += [gira(sh) for sh in movel_comp]

        # ---- fixos no chassi
        # caixa do pivô: tampa sob a longarina (vai até a orelha de fora) + 2 orelhas com furo oblongo
        y_in = s * (y_long - longarina_b / 2)
        y_out = s * (Y_BRACO + BUCHA_L / 2 + 12 + CHAPA_E)
        y0, y1 = sorted((y_in, y_out))
        soldado.append(Part.makeBox(140, y1 - y0, CHAPA_E, V(cin.px - 70, y0, z_chassi - CHAPA_E)))
        for dy in (-1, 1):
            yp = yb + dy * (BUCHA_L / 2 + 4 + CHAPA_E / 2)
            soldado.append(Part.makeBox(140, CHAPA_E, z_chassi - CHAPA_E - (cin.pz - 70),
                                        V(cin.px - 70, yp - CHAPA_E / 2, cin.pz - 70)))
        # prato superior da mola + batente de borracha dentro da mola (encosta no fim do curso)
        soldado.append(Part.makeBox(180, 180, CHAPA_E, V(xm - 90, s * Y_MOLA - 90, z_chassi - CHAPA_E)))
        L_mola = p["L_mola"]
        zi_mov = p["mola_inf"][1]
        comprados.append(Part.makeCylinder(MOLA_D / 2, L_mola, V(p["mola_inf"][0], s * Y_MOLA, zi_mov), V(0, 0, 1)).cut(
            Part.makeCylinder(MOLA_D / 2 - 15, L_mola, V(p["mola_inf"][0], s * Y_MOLA, zi_mov), V(0, 0, 1))))
        info_bat = pontos(cin, z_chassi, CURSO_COMPRESSAO)["L_mola"]
        comprados.append(Part.makeCylinder(32, info_bat, V(xm, s * Y_MOLA, z_chassi - CHAPA_E - info_bat), V(0, 0, 1)))
        # amortecedor (corpo + haste) entre os olhais
        a0 = V(p["amort_inf"][0], yb, p["amort_inf"][1])
        a1 = V(p["amort_sup"][0], yb, p["amort_sup"][1])
        d = a1 - a0
        comprados.append(Part.makeCylinder(AMORT_D / 2, d.Length * 0.55, a0, d))
        comprados.append(Part.makeCylinder(9, d.Length, a0, d))
        # suporte superior do amortecedor: chapa na lateral da longarina + 2 orelhas
        y_lat = s * (y_long + longarina_b / 2)
        y0, y1 = sorted((y_lat, s * (Y_BRACO + 30 + CHAPA_E)))
        soldado.append(Part.makeBox(110, CHAPA_E, 100, V(a1.x - 55, y_lat - (0 if s > 0 else CHAPA_E), z_chassi)))
        for dy in (-1, 1):
            soldado.append(Part.makeBox(80, CHAPA_E, 80, V(a1.x - 40, yb + dy * 30 - CHAPA_E / 2, a1.z - 40)))
        soldado.append(Part.makeBox(80, y1 - y0, CHAPA_E, V(a1.x - 40, y0, a1.z + 40)))

    info = dict(mola_altura=p["L_mola"], amort_L=p["L_amort"], phi=math.degrees(f))
    return soldado, comprados, info, L


def diagrama(caminho, x_eixo, z_roda, z_chassi, z_topo, pneu_d, longarina_h, an=None):
    """Vista lateral da cinemática: extensão / estática / compressão (matplotlib)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    an = an or analise(x_eixo, z_roda, z_chassi, pneu_d)
    cin = an["cin"]
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.add_patch(Rectangle((x_eixo - 650, z_chassi), 1500, longarina_h, color="#b03a2e", alpha=0.25, lw=0))
    ax.axhline(z_topo, color="#7f8c8d", ls="--", lw=1)
    ax.text(x_eixo - 640, z_topo + 8, f"assoalho {z_topo:.0f}", color="#555", fontsize=8)
    ax.axhline(0, color="k", lw=1)
    caixa = an["topo_pneu_comp"] + 30
    ax.axhline(caixa, color="#8e44ad", ls=":", lw=1)
    ax.text(x_eixo - 640, caixa + 8, f"caixa de roda mín. {caixa:.0f} (+{caixa - z_topo:.0f} acima do assoalho)",
            color="#8e44ad", fontsize=8)
    for nome, p, cor in (("extensão -%d" % CURSO_EXTENSAO, an["ext"], "#2e86c1"), ("estática", an["est"], "#222"),
                         ("compressão +%d" % CURSO_COMPRESSAO, an["comp"], "#c0392b")):
        (xr, zr), (xp, zp) = p["roda"], (cin.px, cin.pz)
        ax.add_patch(Circle((xr, zr), pneu_d / 2, fill=False, color=cor, lw=1.2))
        ax.plot([p["ponta"][0], xp], [p["ponta"][1], zp], color=cor, lw=5, alpha=0.6, solid_capstyle="butt")
        ax.plot([p["mola_inf"][0], p["mola_sup"][0]], [p["mola_inf"][1], p["mola_sup"][1]], color=cor, lw=1, ls="-.")
        ax.plot([p["amort_inf"][0], p["amort_sup"][0]], [p["amort_inf"][1], p["amort_sup"][1]], color=cor, lw=2)
        ax.plot(xr, zr, "o", color=cor, ms=4)
        ax.text(xr - pneu_d / 2, zr + pneu_d / 2 + 10, f"{nome}: mola {p['L_mola']:.0f}, amort. {p['L_amort']:.0f}",
                color=cor, fontsize=8)
    ax.plot(cin.px, cin.pz, "ks", ms=7)
    ax.set_aspect("equal")
    ax.set_xlim(x_eixo - 650, x_eixo + 850)
    ax.set_ylim(-20, max(caixa + 80, z_topo + 120))
    ax.set_title("Braço arrastado — curso da roda (vista lateral, frente à direita)")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Z (mm)")
    fig.tight_layout()
    fig.savefig(caminho, dpi=120)
