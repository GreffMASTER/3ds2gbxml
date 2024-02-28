import logging
import math
import xml.etree.ElementTree as ET
from modules.threedees import FacesDescription, TriangularMesh, VerticesList, FacesMaterial, ObjectBlock
from CPlugErrors import NoTrimeshError, NoVerticesError, NoFacesError
import numpy

SURF_DICT = {
    'Concrete': 0,
    'Pavement': 1,
    'Grass': 2,
    'Ice': 3,
    'Metal': 4,
    'Sand': 5,
    'Dirt': 6,
    'Turbo': 7,
    'DirtRoad': 8,
    'Rubber': 9,
    'SlidingRubber': 10,
    'Test': 11,
    'Rock': 12,
    'Water': 13,
    'Wood': 14,
    'Danger': 15,
    'Asphalt': 16,
    'WetDirtRoad': 17,
    'WetAsphalt': 18,
    'WetPavement': 19,
    'WetGrass': 20,
    'Snow': 21,
    'ResonantMetal': 22,
    'GolfBall': 23,
    'GolfWall': 24,
    'GolfGround': 25,
    'Turbo2': 26,
    'Bumper': 27,
    'NotCollidable': 28,
    'FreeWheeling': 29,
    'TurboRoulette': 30
}

GBX_XML_HEADER = {
    'version': '6',
    'unknown': 'R',
    'class': '0900D000',
    'complvl': '1'
}

GBX_XML_HEADER_GEOM = {
    'version': '6',
    'unknown': 'R',
    'class': '0900F000',
    'complvl': '1'
}


def _set_multiple(node: ET.Element, attrib: dict):
    for key, value in attrib.items():
        node.set(key, value)


def _set_value(node: ET.Element, v_type: str, value: str):
    new_node = ET.Element(v_type)
    new_node.text = value
    node.append(new_node)


def _isnumber(text: str):
    try:
        int(text)
        return True
    except Exception:
        return False


def create_xml(objects: list) -> ET.ElementTree:
    # Prepare objects

    logging.info(f'Converting all objects to one Surface...')

    vert_count = 0
    face_count = 0
    vertices_all = []
    triangles_all = []
    materials_all = {}

    

    for model_object in objects:
        new_vert_count = 0
        new_face_count = 0

        trimesh: TriangularMesh = model_object.children[0]
        if not trimesh or not isinstance(trimesh, TriangularMesh):
            raise NoTrimeshError
        
        tris = None

        for child in trimesh.children:
            if isinstance(child, VerticesList):
                new_vert_count = len(child.vertices)
                vertices_all = vertices_all + child.vertices

            if isinstance(child, FacesDescription):
                tris = child
                temp = child.polygons.copy()
                for i in range(len(temp)):  # Update vertex references
                    poly = temp[i]
                    new_poly = (poly[0] + vert_count, poly[1] + vert_count, poly[2] + vert_count)
                    temp[i] = new_poly
                new_face_count = len(temp)
                triangles_all = triangles_all + temp
                

        if child:
            for child in tris.children:
                if isinstance(child, FacesMaterial):
                    name = child.material_name
                    temp = child.applied_faces.copy()
                    for i in range(len(temp)):  # Update vertex references
                        temp[i] = temp[i] + vert_count
                        materials_all[temp[i]] = name

        vert_count = vert_count + new_vert_count
        face_count = face_count + new_face_count

    if len(triangles_all) == 0:
        raise NoFacesError
    if len(vertices_all) == 0:
        raise NoVerticesError

    logging.info(f'Vertex: {len(vertices_all)}')
    logging.info(f'Polygons: {len(triangles_all)}')

    # Do the thing

    gbx = ET.Element('gbx')

    _set_multiple(gbx, GBX_XML_HEADER)

    body = ET.Element('body')

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugSurface', 'id': '000'})
    chunk.append(ET.Element('node'))
    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugSurface', 'id': '001'})
    _set_value(chunk, 'uint32', '1')
    body.append(chunk)


    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': '0900D000', 'id': '002'})
    _set_value(chunk, 'uint32', '2')  # version

    lst = ET.Element('list')

    for vertex in vertices_all:
        le = ET.Element('element')
        _set_value(le, 'vec3', f'{vertex.pos[0]} {vertex.pos[1]} {vertex.pos[2]}')
        lst.append(le)

    chunk.append(lst)

    lst = ET.Element('list')

    i = 0
    for polygon in triangles_all:
        le = ET.Element('element')
        v_a = numpy.array(vertices_all[polygon[0]].pos)
        v_b = numpy.array(vertices_all[polygon[1]].pos)
        v_c = numpy.array(vertices_all[polygon[2]].pos)
        direct = numpy.cross(v_b - v_a, v_c - v_a)
        direct = direct / numpy.linalg.norm(direct)
        _set_value(le, 'vec4', f'{direct[0]} {direct[1]} {direct[2]} {-vertices_all[polygon[0]].pos[1]}')
        _set_value(le, 'uint32', str(polygon[0]))
        _set_value(le, 'uint32', str(polygon[1]))
        _set_value(le, 'uint32', str(polygon[2]))

        # SurfaceType

        value = ET.Element('uint16')
        mat = materials_all.get(i)
        if mat:
            surf_type = SURF_DICT.get(mat)
            if surf_type:
                value.text = str(surf_type)
            elif _isnumber(mat):
                value.text = mat
            else:
                value.text = '0'
        else:
            value.text = '0'
        le.append(value)
        _set_value(le, 'uint8', '0')
        _set_value(le, 'uint8', '0')
        lst.append(le)
        i += 1

    chunk.append(lst)

    _set_value(chunk, 'uint32', '2')  # MeshOctreeCellVersion

    max_x, max_y, max_z = 0, 0, 0
    min_x = vertices_all[1].pos[0]
    min_y = vertices_all[1].pos[1]
    min_z = vertices_all[1].pos[2]
    for v in vertices_all:
        if v.pos[0] > max_x: max_x = v.pos[0]
        if v.pos[1] > max_y: max_y = v.pos[1]
        if v.pos[2] > max_z: max_z = v.pos[2]
        if v.pos[0] < min_x: min_x = v.pos[0]
        if v.pos[1] < min_y: min_y = v.pos[1]
        if v.pos[2] < min_z: min_z = v.pos[2]

    cen_x = (max_x - abs(min_x)) / 2
    cen_y = (max_y - abs(min_y)) / 2
    cen_z = (max_z - abs(min_z)) / 2
    siz_x = (max_x + abs(min_x)) / 2
    siz_y = (max_y + abs(min_y)) / 2
    siz_z = (max_z + abs(min_z)) / 2

    lst = ET.Element('list')
    ole = ET.Element('element')

    _set_value(ole, 'int32', '1')
    _set_value(ole, 'vec3', f'{cen_x} {cen_y} {cen_z}')
    _set_value(ole, 'vec3', f'{siz_x} {siz_y} {siz_z}')
    _set_value(ole, 'int32', '-1')

    lst.append(ole)

    # TODO properly implement MeshOctreeCells

    chunk.append(lst)
    body.append(chunk)

    # Pack it up to ElementTree
    gbx.append(body)
    tree = ET.ElementTree(gbx)

    return tree
