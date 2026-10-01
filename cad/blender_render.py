"""
Render realista no Blender (sem interface) a partir do .glb gerado pelo chassi.py.

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background --python cad\\blender_render.py -- \\
        cad\\out\\chassi_braco.glb cad\\out\\render_braco.png [geral|suspensao|tras] [amostras]

Também salva um .blend ao lado da imagem, já com chão, luz e câmera, para abrir e girar à vontade.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
glb, saida = os.path.abspath(args[0]), os.path.abspath(args[1])
vista = args[2] if len(args) > 2 else "geral"
amostras = int(args[3]) if len(args) > 3 else 96

# câmera: (posição, alvo, distância focal) em metros — X = frente da carreta, Z = para cima
VISTAS = {
    "geral": ((6.3, -4.6, 2.3), (1.75, 0.0, 0.45), 50),
    "tras": ((-3.6, -4.2, 1.9), (1.4, 0.0, 0.45), 50),
    "suspensao": ((2.6, -2.9, 0.75), (1.0, -0.55, 0.42), 55),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
cena = bpy.context.scene

# chão: cascalho claro, fosco
bpy.ops.mesh.primitive_plane_add(size=60, location=(1.8, 0, 0))
chao = bpy.context.object
chao.name = "chao"
mat = bpy.data.materials.new("chao")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.42, 0.38, 0.33, 1)
bsdf.inputs["Roughness"].default_value = 0.95
ruido = mat.node_tree.nodes.new("ShaderNodeTexNoise")
ruido.inputs["Scale"].default_value = 900
relevo = mat.node_tree.nodes.new("ShaderNodeBump")
relevo.inputs["Strength"].default_value = 0.6
mat.node_tree.links.new(ruido.outputs["Fac"], relevo.inputs["Height"])
mat.node_tree.links.new(relevo.outputs["Normal"], bsdf.inputs["Normal"])
chao.data.materials.append(mat)

# céu claro uniforme + sol (sombras suaves)
mundo = bpy.data.worlds.new("ceu")
mundo.use_nodes = True
fundo = mundo.node_tree.nodes["Background"]
fundo.inputs["Color"].default_value = (0.62, 0.74, 0.92, 1)
fundo.inputs["Strength"].default_value = 0.9
cena.world = mundo
sol = bpy.data.lights.new("sol", "SUN")
sol.energy = 4.5
sol.angle = math.radians(3)
o_sol = bpy.data.objects.new("sol", sol)
o_sol.rotation_euler = (math.radians(52), 0, math.radians(-35))
cena.collection.objects.link(o_sol)

# câmera apontada para o alvo
pos, alvo, focal = VISTAS[vista]
cam = bpy.data.cameras.new("camera")
cam.lens = focal
o_cam = bpy.data.objects.new("camera", cam)
o_cam.location = pos
o_cam.rotation_euler = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
cena.collection.objects.link(o_cam)
cena.camera = o_cam

# Cycles (GPU se houver, senão CPU) com redução de ruído
cena.render.engine = "CYCLES"
cena.cycles.samples = amostras
cena.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for tipo in ("OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = tipo
            prefs.get_devices()
            if any(d.type == tipo for d in prefs.devices):
                for d in prefs.devices:
                    d.use = True
                cena.cycles.device = "GPU"
                break
        except Exception:
            continue
except Exception:
    pass
cena.render.resolution_x, cena.render.resolution_y = 1920, 1080
cena.render.filepath = saida
cena.render.image_settings.file_format = "PNG"

bpy.ops.wm.save_as_mainfile(filepath=os.path.splitext(saida)[0] + ".blend")
bpy.ops.render.render(write_still=True)
print(f"render: {saida} | motor {cena.render.engine} | dispositivo {cena.cycles.device}")
