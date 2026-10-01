"""
Suspensão traseira multilink da Fiat Toro 4x4 (agregado de desmanche) adaptada ao chassi da carreta.

Mesma plataforma do Compass (Small Wide 4x4): furação 5x110, mesmo estepe.

O que veio de fonte publicada (fichas técnicas / catálogos de peças, 2026-10):
  - multilink independente: braços transversais + longitudinal + barra estabilizadora
  - mola helicoidal SEPARADA do amortecedor (amortecedor sai sem compressor de mola)
  - amortecedor traseiro (Monroe 379079SP): 716 aberto / 433 fechado -> curso 283
    superior com 2 parafusos na carroceria (coxim), inferior 1 parafuso no braço
  - mola traseira: Ø externo ~120, arame 12
  - bitola traseira 1575-1579 (4x4)
  - cubo traseiro 4x4: rolamento integrado + ABS, 5 furos, 27 estrias (furo do semieixo a tampar)
  - freio traseiro: disco Ø278 (diesel) ou tambor Ø295 (algumas versões)
  - Toro: PBT 2905 kg, carga útil ~1000 kg -> eixo traseiro bem mais forte que o do Compass

O que é ESTIMADO (não achei publicado): posição dos pontos de articulação, tamanho do
agregado e da manga. Coordenadas relativas ao centro da roda, em mm:
  dx = para a frente, dy = para DENTRO a partir do plano da roda, dz = para cima.
MEDIR NUMA PEÇA REAL e corrigir PONTOS/AGREGADO antes de qualquer decisão definitiva.
"""
import math

BITOLA = 1579
AMORT_ABERTO, AMORT_FECHADO = 716, 433
AMORT_ESTATICO = 0.40       # fração do curso comprimida com a carreta parada (ESTIMADO)
MOLA_D, MOLA_ARAME = 120, 12
DISCO_D, DISCO_E = 278, 12

# pontos de articulação (dx, dy, dz) — ESTIMADO
PONTOS = {
    "manga_inf":      (0, 105, -115),    # rótula/bucha do braço inferior na manga
    "manga_sup":      (0, 95, 150),      # bucha do braço superior na manga
    "manga_conv":     (-130, 105, -60),  # tirante de convergência
    "manga_long":     (55, 150, -20),    # braço longitudinal (puxa a manga para a frente)
    "inf_frente":     (170, 400, -70),   # buchas do braço inferior no agregado
    "inf_tras":       (-170, 400, -70),
    "sup_agregado":   (0, 400, 165),
    "conv_agregado":  (-140, 400, -55),
    "long_carroceria": (430, 195, 30),   # na carroceria do carro -> aqui, suporte soldado na longarina
    "mola_inf":       (-30, 300, -95),   # prato da mola no braço inferior
    "amort_inf":      (-110, 190, -105), # amortecedor no braço inferior
    "amort_incl":     (-80, 70),         # deslocamento (dx, dy p/ dentro) do topo em relação à base
}
# agregado (berço): 2 travessas + 2 laterais em chapa estampada (~caixa 90x80) — ESTIMADO
AGREGADO = dict(x_frente=230, x_tras=-230, y_lateral=400, dz=50, secao=(90, 80), massa=28)

# massas por lado (kg) — ordem de grandeza de peças de reposição, ESTIMADO
MASSAS = {"manga": 7.5, "cubo c/ rolamento": 3.0, "disco": 7.0, "pinça": 4.0, "braço inferior": 6.0,
          "braço superior": 1.5, "tirante convergência": 1.2, "braço longitudinal": 2.5,
          "mola": 3.5, "amortecedor": 3.0}


def _haste(p0, p1, r):
    import Part
    d = p1 - p0
    return Part.makeCylinder(r, d.Length, p0, d)


def _bucha(p, eixo, r=22, L=50):
    import Part
    e = eixo.normalize()
    return Part.makeCylinder(r, L, p - e * (L / 2), e)


def suspensao(x_eixo, y_roda, z_roda, z_chassi, y_long, longarina_b, et=0.0):
    """Monta os dois lados. Retorna (adaptadores_soldados, comprados, info).

    y_long = centro da longarina, z_chassi = face inferior dela (onde o agregado e as molas apoiam)."""
    import Part
    from FreeCAD import Vector as V

    soldado, comprado = [], []
    info = {}

    def P(nome, s):
        dx, dy, dz = PONTOS[nome]
        return V(x_eixo + dx, s * (y_roda - dy), z_roda + dz)

    # ---- agregado (comum aos dois lados)
    a = AGREGADO
    bx, bz = a["secao"]
    za = z_roda + a["dz"]
    ya = a["y_lateral"]
    y_ag = y_roda - ya
    trav = [Part.makeBox(bx, 2 * y_ag + bx, bz, V(x_eixo + x - bx / 2, -y_ag - bx / 2, za - bz / 2))
            for x in (a["x_frente"], a["x_tras"])]
    lat = [Part.makeBox(a["x_frente"] - a["x_tras"], bx, bz, V(x_eixo + a["x_tras"], s * y_ag - bx / 2, za - bz / 2))
           for s in (+1, -1)]
    agregado = trav[0].fuse(trav[1:] + lat).removeSplitter()
    comprado.append(agregado)
    # 4 coxins do agregado + calços soldados sob a longarina (vão entre o topo do agregado e o chassi)
    z_top_ag = za + bz / 2
    for x in (a["x_frente"], a["x_tras"]):
        for s in (+1, -1):
            c = V(x_eixo + x, s * y_ag, z_top_ag)
            comprado.append(Part.makeCylinder(32, 35, c, V(0, 0, 1)))
            h = z_chassi - (z_top_ag + 35)
            if h > 1:
                # calço em chapa dobrada: caixa 100 x (até a longarina) soldada na face inferior
                y0, y1 = sorted((s * (y_ag - 50), s * (y_long + longarina_b / 2)))
                caixa = Part.makeBox(100, y1 - y0, h, V(c.x - 50, y0, z_top_ag + 35))
                vazio = Part.makeBox(100 - 12, y1 - y0 - 12, h - 6, V(c.x - 44, y0 + 6, z_top_ag + 35 + 6))
                soldado.append(caixa.cut(vazio))  # caixa de chapa 6 mm, aberta em cima (solda na longarina)
    info["calco_agregado"] = z_chassi - (z_top_ag + 35)

    for s in (+1, -1):
        ex = V(1, 0, 0)
        # manga: bloco vertical + cubo + disco + pinça
        hub_y = s * y_roda
        manga = Part.makeBox(90, 60, 300, V(x_eixo - 45, s * (y_roda - 125) - 30, z_roda - 140))
        comprado.append(manga)
        comprado.append(Part.makeCylinder(65, 95 + et, V(x_eixo, s * (y_roda - 95), z_roda), V(0, s, 0)))  # cubo até a face da roda (ET)
        comprado.append(Part.makeCylinder(DISCO_D / 2, DISCO_E, V(x_eixo, s * (y_roda - 45), z_roda), V(0, s, 0)).cut(
            Part.makeCylinder(70, DISCO_E, V(x_eixo, s * (y_roda - 45), z_roda), V(0, s, 0))))
        comprado.append(Part.makeBox(110, 70, 60, V(x_eixo + 40, s * (y_roda - 39) - 35, z_roda + DISCO_D / 2 - 75)))
        info["face_cubo"] = abs(hub_y)

        # braço inferior: placa em "A" (bandeja larga, recebe mola e amortecedor)
        mi, f, t = P("manga_inf", s), P("inf_frente", s), P("inf_tras", s)
        tri = Part.makePolygon([mi + V(60, 0, 0), f, t, mi - V(60, 0, 0), mi + V(60, 0, 0)])
        bandeja = Part.Face(tri).extrude(V(0, 0, 12)).translated(V(0, 0, -6))
        comprado.append(bandeja)
        comprado += [_bucha(f, ex), _bucha(t, ex)]

        # braço superior, tirante de convergência, braço longitudinal
        for a_, b_, r in (("manga_sup", "sup_agregado", 14), ("manga_conv", "conv_agregado", 11),
                          ("manga_long", "long_carroceria", 15)):
            pa, pb = P(a_, s), P(b_, s)
            comprado += [_haste(pa, pb, r), _bucha(pb, ex if b_ != "long_carroceria" else V(0, 1, 0), r + 8, 40)]

        # suporte do braço longitudinal: 2 chapas penduradas na longarina (estrutura da carreta)
        pl = P("long_carroceria", s)
        for dyc in (-30, 30):
            yc = pl.y + dyc
            soldado.append(Part.makeBox(120, 8, z_chassi - (pl.z - 40), V(pl.x - 60, yc - 4, pl.z - 40)))
        # chapa de ligação dos suportes até a longarina (o ponto fica por fora dela)
        y0, y1 = sorted((pl.y + s * 34, s * (y_long - longarina_b / 2)))
        soldado.append(Part.makeBox(120, y1 - y0, 8, V(pl.x - 60, y0, z_chassi - 8)))

        # mola: do prato no braço inferior até o prato sob a longarina
        pm = P("mola_inf", s)
        z_sup = z_chassi - 8
        mola = Part.makeCylinder(MOLA_D / 2, z_sup - pm.z, pm, V(0, 0, 1)).cut(
            Part.makeCylinder(MOLA_D / 2 - MOLA_ARAME, z_sup - pm.z, pm, V(0, 0, 1)))
        comprado.append(mola)
        soldado.append(Part.makeBox(150, 150, 8, V(pm.x - 75, pm.y - 75, z_sup)))
        info["mola_altura"] = z_sup - pm.z
        info["mola_y"] = abs(pm.y)

        # amortecedor: comprimento estático; topo inclinado p/ dentro e p/ trás
        pa = P("amort_inf", s)
        L = AMORT_ABERTO - AMORT_ESTATICO * (AMORT_ABERTO - AMORT_FECHADO)
        ddx, ddy = PONTOS["amort_incl"]
        dz = math.sqrt(max(L * L - ddx * ddx - ddy * ddy, 0))
        topo = pa + V(ddx, -s * ddy, dz)
        comprado.append(_haste(pa, topo - (topo - pa).normalize() * 250, 25))   # corpo
        comprado.append(_haste(topo - (topo - pa).normalize() * 260, topo, 10))  # haste
        # torre/suporte do topo do amortecedor (chapa 8 mm)
        soldado.append(Part.makeBox(100, 100, 8, V(topo.x - 50, topo.y - 50, topo.z)))
        info["amort_topo_z"] = topo.z
        info["amort_topo_y"] = abs(topo.y)
        info["amort_L"] = L

    info["massa_comprados"] = AGREGADO["massa"] + 2 * sum(MASSAS.values())
    info["vao_livre"] = min(sh.BoundBox.ZMin for sh in comprado)
    return soldado, comprado, info
