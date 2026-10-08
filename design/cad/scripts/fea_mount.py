"""FEA of the GoPro-style 2-finger chest mount (FreeCAD FEM + Gmsh + CalculiX).

Load case (design assumption, documented on the slide):
  - pod mass 0.30 kg (CAD + datasheet estimate, rounded up)
  - dynamic factor ~17 g for a bump / snag while walking  ->  F = 50 N, applied downward (-Z)
    on the plate face that joins the shell; the two bolt holes are fixed (the harness buckle).
Material: PETG (E = 2.0 GPa, nu = 0.38, yield ~ 50 MPa; datasheet typical values; printed parts
are weaker between layers, so we require a factor of safety >= 3 on the yield strength).
Design iteration: v1 = sharp finger roots, v2 = 1.5 mm fillet at the finger roots.
Convergence: each version is solved at 5 mesh sizes (2nd-order tetrahedra).
Run: tools/freecad.sh cmd design/cad/scripts/fea_mount.py
"""
import os
import json
import FreeCAD as App
import Part
import ObjectsFem

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
OUT = os.path.join(CAD, 'outputs', 'fea')
TOOLS = os.path.normpath(os.path.join(CAD, '..', '..', 'tools'))
BIN = '/tmp/visionaid-tools/freecad-env/bin'          # space-free link to tools/freecad-env
V = App.Vector
os.makedirs(OUT, exist_ok=True)

p = App.ParamGet('User parameter:BaseApp/Preferences/Mod/Fem/Gmsh')
p.SetBool('UseStandardGmshLocation', False)
p.SetString('gmshBinaryPath', BIN + '/gmsh')
p = App.ParamGet('User parameter:BaseApp/Preferences/Mod/Fem/Ccx')
p.SetBool('UseStandardCcxLocation', False)
p.SetString('ccxBinaryPath', BIN + '/ccx')

T, G, L, R, BOLT = 3.0, 3.2, 10.0, 7.5, 5.2       # same values as the CAD spreadsheet
PLATE = (30.0, 2.5, 30.0)                          # piece of the 2.5 mm back wall under the mount
FORCE_N = 50.0
YIELD_MPA = 50.0


def geometry(root_fillet):
    plate = Part.makeBox(PLATE[0], PLATE[1], PLATE[2], V(-PLATE[0] / 2, 0, -PLATE[2] / 2))
    shape = plate
    for s in (-1, 1):
        x0 = s * (G / 2 + T / 2) - T / 2
        finger = Part.makeBox(T, L, 2 * R, V(x0, -L, -R))
        tip = Part.makeCylinder(R, T, V(x0, -L, 0), V(1, 0, 0))
        shape = shape.fuse(finger).fuse(tip)
    shape = shape.removeSplitter()
    hole = Part.makeCylinder(BOLT / 2, 40, V(-20, -L, 0), V(1, 0, 0))
    shape = shape.cut(hole)
    if root_fillet > 0:
        # edges where the fingers meet the plate (plane y = 0, inside the finger footprint)
        edges = [e for e in shape.Edges
                 if all(abs(v.Point.y) < 1e-6 for v in e.Vertexes)
                 and max(abs(v.Point.x) for v in e.Vertexes) <= G / 2 + T + 1e-6
                 and max(abs(v.Point.z) for v in e.Vertexes) <= R + 1e-6]
        shape = shape.makeFillet(root_fillet, edges)
    return shape


LOADS = {'down50N': ('z', 50.0), 'side20N': ('x', 20.0)}   # downward bump/snag; sideways knock


def solve(doc, part, h, tag, load='down50N'):
    from femtools import ccxtools
    from femmesh.gmshtools import GmshTools
    analysis = ObjectsFem.makeAnalysis(doc, 'Analysis_' + tag)
    try:
        solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, 'Solver_' + tag)
    except Exception:
        solver = ObjectsFem.makeSolverCalculiX(doc, 'Solver_' + tag)
    solver.AnalysisType = 'static'
    try:
        solver.GeometricalNonlinearity = 'linear'
    except TypeError:
        solver.GeometricalNonlinearity = False   # newer FreeCAD: boolean property
    analysis.addObject(solver)
    mat = ObjectsFem.makeMaterialSolid(doc, 'PETG_' + tag)
    mat.Material = {'Name': 'PETG', 'YoungsModulus': '2000 MPa', 'PoissonRatio': '0.38',
                    'Density': '1270 kg/m^3'}
    analysis.addObject(mat)
    sh = part.Shape
    bolt_faces = ['Face%d' % (i + 1) for i, f in enumerate(sh.Faces)
                  if f.Surface.__class__.__name__ == 'Cylinder' and abs(f.Surface.Radius - BOLT / 2) < 1e-3]
    back_face = ['Face%d' % (i + 1) for i, f in enumerate(sh.Faces)
                 if f.Surface.__class__.__name__ == 'Plane' and abs(f.CenterOfMass.y - PLATE[1]) < 1e-6]
    axis, fmag = LOADS[load]
    ax = V(1, 0, 0) if axis == 'x' else V(0, 0, 1)
    dedge = [('Edge%d' % (i + 1)) for i, e in enumerate(sh.Edges)
             if len(e.Vertexes) == 2 and abs((e.Vertexes[1].Point - e.Vertexes[0].Point).normalize().dot(ax)) > 0.999]
    fix = ObjectsFem.makeConstraintFixed(doc, 'Fixed_' + tag)
    fix.References = [(part, bolt_faces)]
    analysis.addObject(fix)
    force = ObjectsFem.makeConstraintForce(doc, 'Load_' + tag)
    force.References = [(part, back_face)]
    force.Force = '%g N' % fmag             # explicit unit (a bare float is read as mN)
    force.Direction = (part, [dedge[0]])
    force.Reversed = True
    analysis.addObject(force)
    mesh = ObjectsFem.makeMeshGmsh(doc, 'Mesh_' + tag)
    mesh.Shape = part
    mesh.CharacteristicLengthMax = h
    mesh.CharacteristicLengthMin = h / 4
    mesh.ElementOrder = '2nd'
    analysis.addObject(mesh)
    doc.recompute()
    GmshTools(mesh).create_mesh()
    doc.recompute()
    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    fea.setup_working_dir(os.path.join(OUT, 'work_' + tag))
    fea.setup_ccx()
    msg = fea.check_prerequisites()
    if msg:
        raise RuntimeError(msg)
    fea.purge_results()
    fea.write_inp_file()
    fea.ccx_run()
    fea.load_results()
    res = [o for o in analysis.Group if o.isDerivedFrom('Fem::FemResultObject')][0]
    fm = mesh.FemMesh
    out = {'tag': tag, 'h_mm': h, 'elements': fm.VolumeCount, 'nodes': fm.NodeCount,
           'max_vonmises_MPa': max(res.vonMises), 'max_disp_mm': max(res.DisplacementLengths)}
    out['FoS'] = YIELD_MPA / out['max_vonmises_MPa']
    # stress at the finger roots (|y| < 2 mm from the plate, inside the finger footprint), away from
    # the fixed bolt-hole faces where a rigid fixture gives an artificial local peak
    ids = list(fm.Nodes.keys())
    root = [vmv for nid, vmv in zip(res.NodeNumbers, res.vonMises)
            if -2.0 <= fm.Nodes[nid].y <= 0.5 and abs(fm.Nodes[nid].x) <= G / 2 + T + 0.01]
    out['root_vonmises_MPa'] = max(root) if root else None
    out['load'] = load
    # keep node coordinates + stress of the finest mesh for the contour plot
    nodes = [(n.x, n.y, n.z) for n in fm.Nodes.values()]
    return out, nodes, list(res.vonMises)


def main():
    doc = App.newDocument('MountFEA')
    results = []
    contour = {}
    for ver, fil in (('v1_sharp', 0.0), ('v2_fillet1p5', 1.5)):
        part = doc.addObject('Part::Feature', 'Mount_' + ver)
        part.Shape = geometry(fil)
        Part.export([part], os.path.join(OUT, 'mount_%s.step' % ver))
        for load, h in [(l, h) for l in LOADS for h in (3.0, 2.0, 1.4, 1.0)]:
            tag = '%s_%s_h%s' % (ver, load, str(h).replace('.', 'p'))
            try:
                r, nodes, vm = solve(doc, part, h, tag, load)
            except Exception as e:
                print('%-12s %-7s h=%.1f  FAILED: %s' % (ver, load, h, e), flush=True)
                continue
            r['version'] = ver
            results.append(r)
            print('%-12s %-7s h=%.1f elems=%6d max vM=%6.2f MPa root vM=%6.2f FoS=%5.2f disp=%.4f mm' % (
                ver, load, h, r['elements'], r['max_vonmises_MPa'], r['root_vonmises_MPa'] or -1, r['FoS'],
                r['max_disp_mm']), flush=True)
            contour[ver + '_' + load] = {'nodes': nodes, 'vm': vm}
            json.dump(results, open(os.path.join(OUT, 'fea_results.json'), 'w'), indent=1)       # save as we go
            json.dump(contour, open(os.path.join(OUT, 'fea_contour_finest.json'), 'w'))
    json.dump(results, open(os.path.join(OUT, 'fea_results.json'), 'w'), indent=1)
    json.dump(contour, open(os.path.join(OUT, 'fea_contour_finest.json'), 'w'))
    doc.saveAs(os.path.join(OUT, 'MountFEA.FCStd'))
    print('done')


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    print("FEA_FAILED", flush=True)
