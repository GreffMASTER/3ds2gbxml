import logging
import math
import pprint
import xml.etree.ElementTree as ET

import numpy

from CPlugErrors import NoTrimeshError, NoFacesError, NoVerticesError
from modules.threedees import TriangularMesh, VerticesList, FacesDescription, FacesMaterial


def _set_multiple(node: ET.Element, attrib: dict):
    for key, value in attrib.items():
        node.set(key, value)


def _set_value(node: ET.Element, v_type: str, value: str, attrib: dict = None):
    new_node = ET.Element(v_type)
    new_node.text = value
    if attrib:
        _set_multiple(new_node, attrib)
    node.append(new_node)


def _is_number(text: str):
    try:
        int(text)
        return True
    except Exception:
        return False


def _calculate_bounding_box(verts):
    max_x = verts[0].pos[0]
    max_y = verts[0].pos[1]
    max_z = verts[0].pos[2]
    min_x = max_x
    min_y = max_y
    min_z = max_z
    for v in verts:
        # get biggest x y z values
        if v.pos[0] > max_x:
            max_x = v.pos[0]
        if v.pos[1] > max_y:
            max_y = v.pos[1]
        if v.pos[2] > max_z:
            max_z = v.pos[2]
        # get smallest x y z values
        if v.pos[0] < min_x:
            min_x = v.pos[0]
        if v.pos[1] < min_y:
            min_y = v.pos[1]
        if v.pos[2] < min_z:
            min_z = v.pos[2]
    # calculate center of the mesh
    cen_x = (max_x + min_x) / 2
    cen_y = (max_y + min_y) / 2
    cen_z = (max_z + min_z) / 2
    # calculate size of the mesh
    siz_x = (max_x - min_x) / 2
    siz_y = (max_y - min_y) / 2
    siz_z = (max_z - min_z) / 2
    return cen_x, cen_y, cen_z, siz_x, siz_y, siz_z


def generate_cell_inter(verts, tris, size_x, size_y, size_z):
    box = _calculate_bounding_box(verts)
    mesh_size_x = box[3] * 2
    mesh_size_y = box[4] * 2
    mesh_size_z = box[5] * 2

    cell_size_x = math.ceil(mesh_size_x / size_x)
    cell_size_y = math.ceil(mesh_size_y / size_y)
    cell_size_z = math.ceil(mesh_size_z / size_z)

    print(cell_size_x, cell_size_y, cell_size_z)

    cells = [[[0 for _ in range(cell_size_z)] for _ in range(cell_size_y)] for _ in range(cell_size_x)]

    for polygon in tris:
        p_x1 = verts[polygon[0]].pos[0]
        p_x2 = verts[polygon[1]].pos[0]
        p_x3 = verts[polygon[2]].pos[0]

        p_y1 = verts[polygon[0]].pos[1]
        p_y2 = verts[polygon[1]].pos[1]
        p_y3 = verts[polygon[2]].pos[1]

        p_z1 = verts[polygon[0]].pos[2]
        p_z2 = verts[polygon[1]].pos[2]
        p_z3 = verts[polygon[2]].pos[2]

        a_x = (p_x1 + p_x2 + p_x3) / 3
        a_y = (p_y1 + p_y2 + p_y3) / 3
        a_z = (p_z1 + p_z2 + p_z3) / 3

        p_x = math.floor(a_x / size_x)
        p_y = math.floor(a_y / size_y)
        p_z = math.floor(a_z / size_z)

        if p_x >= 0 and p_y >= 0 and p_z >= 0:
            cells[p_x][p_y][p_z] = 1

    return cells, (cell_size_x, cell_size_y, cell_size_z)


def generate_cells(objects: list, size_x, size_y, size_z, zone):
    logging.info(f'Converting all objects to one mesh...')

    vert_count = 0
    face_count = 0
    vertices_all = []
    triangles_all = []
    materials_all = {}
    # calls = [[ ['#' for col in range(a)] for col in range(b)] for row in range(c)]

    # adding all the vertices and faces into big global arrays
    # setting the vertex and face indexes by an offset
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
        # do materials
        if tris:
            for child in tris.children:
                if isinstance(child, FacesMaterial):
                    name = child.material_name
                    temp = child.applied_faces.copy()
                    for i in range(len(temp)):  # Update face references
                        temp[i] = temp[i] + face_count
                        materials_all[temp[i]] = name

        vert_count = vert_count + new_vert_count
        face_count = face_count + new_face_count

    if len(triangles_all) == 0:
        raise NoFacesError
    if len(vertices_all) == 0:
        raise NoVerticesError

    logging.info(f'Vertex: {len(vertices_all)}')
    logging.info(f'Polygons: {len(triangles_all)}')

    cells, _ = generate_cell_inter(vertices_all, triangles_all, size_x, size_y, size_z)

    box = _calculate_bounding_box(vertices_all)
    mesh_size_x = box[3] * 2
    mesh_size_y = box[4] * 2
    mesh_size_z = box[5] * 2

    cell_size_x = math.ceil(mesh_size_x / size_x)
    cell_size_y = math.ceil(mesh_size_y / size_y)
    cell_size_z = math.ceil(mesh_size_z / size_z)

    pprint.pprint(cells)

    lst = ET.Element('list')

    for x in range(cell_size_x):
        for y in range(cell_size_y):
            for z in range(cell_size_z):
                if cells[x][y][z]:
                    cell = ET.Element('element')
                    node = ET.Element('node')
                    node.set('class', '24006000')
                    chunk = ET.Element('chunk')
                    _set_multiple(chunk, {'class': '24006000', 'id': '000'})
                    _set_value(chunk, 'flags', '', {'bytes': '4'})
                    _set_value(chunk, 'bool', '1')
                    _set_value(chunk, 'uint32', '0')
                    _set_value(chunk, 'uint32', str(x))
                    _set_value(chunk, 'uint32', str(y))
                    _set_value(chunk, 'uint32', str(z))
                    _set_value(chunk, 'uint32', '4')
                    _set_value(chunk, 'node', '')
                    _set_value(chunk, 'node', '')
                    _set_value(chunk, 'node', '')
                    _set_value(chunk, 'node', '')
                    node.append(chunk)

                    chunk = ET.Element('chunk')
                    _set_multiple(chunk, {'class': '24006000', 'id': '001'})
                    _set_value(chunk, 'lookbackstr', zone, {'type': '40'})
                    _set_value(chunk, 'uint32', '1668506948')
                    _set_value(chunk, 'uint32', '1935764547')
                    node.append(chunk)

                    cell.append(node)
                    lst.append(cell)
    tree = ET.ElementTree(lst)
    return tree
