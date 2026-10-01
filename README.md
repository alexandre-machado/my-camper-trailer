# Trailer Camper

Carretinha de acampamento off-road, inspirada na [Patriot X2 Tourer](https://patriotcampers.com.au/x2n-tourer/)
e na [TerraTrek TTE](https://terratrek.com.au/tte-terra-trek-expedition/), para ser rebocada por um
Jeep Compass Trailhawk 2.0 Diesel 2020.

O projeto é descrito em **Python** e roda no FreeCAD sem interface: cada script gera o modelo 3D,
os arquivos de fabricação para corte a laser (chapa e tubo), a lista de corte e as imagens.

## Vídeo

▶️ [Modelo no FreeCAD (vídeo)](midia/FreeCAD.mp4)

## Estado atual

- **Chassi** em escada, 2600 mm, longarinas RHS 100x50x3 dobradas 90° na frente (corte em V) até o cambão.
- **Cambão de viga única** RHS 150x75x5, sem "A", para dar mais ângulo de manobra (95°).
- **Encaixe macho-fêmea** em todas as 27 juntas de tubo; quadros laterais com cantos dobrados em V.
- **Duas suspensões em estudo**, no mesmo arquivo e em pastas separadas:
  - agregado multilink traseiro da Fiat Toro 4x4 (pontos ainda estimados);
  - braço arrastado próprio, com mola, amortecedor e cubo de carro 5x110.
- **Pneu** Speedmax Prime Pangea AT 235/65R17, o mesmo do carro (estepe comum).
- **Limites do carro**: 1500 kg com freio, 400 kg sem freio, cerca de 75 kg na bola.

Perfis e espessuras são estimativas para estudo de forma e massa, **não dimensionamento estrutural**.

## Como rodar

Requer FreeCAD 1.1 e o `ezdxf` instalado em `cad/_pylibs` (ver [cad/README.md](cad/README.md)).

```
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" cad\chassi.py
```

As saídas vão para `cad/out/` (ignorada pelo git, regenerável): `chassi.FCStd`, `chassi.step`,
`laser_tubular/T*.step`, `dxf/*.dxf`, `chassi_lista_corte.csv`, imagens e os `.glb` para o Blender.

Render realista (opcional, Blender 5.2):

```
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python cad\blender_render.py -- cad\out\chassi_braco.glb cad\out\render_braco.png geral
```

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `cad/veiculo.py` | parâmetros gerais: carro rebocador, pneu, furação, limites de reboque |
| `cad/chassi.py` | chassi, suspensões e rodas; parâmetros no topo |
| `cad/braco.py` | suspensão de braço arrastado: cargas, mola, amortecedor, curso |
| `cad/toro.py` | agregado multilink da Fiat Toro 4x4 |
| `cad/pneu.py` | pneu a partir da medida, com blocos, garras e letras |
| `cad/comum.py` | perfis, tubos com encaixe e dobra em V, lista de corte, DXF, imagens |
| `cad/blender_render.py` | render realista no Blender |
| `cad/bandeja.py` | prova de conceito de chapa dobrada (STEP + DXF planificado) |

Notas técnicas em [cad/README.md](cad/README.md); estado detalhado, decisões e pendências em [CLAUDE.md](CLAUDE.md).
