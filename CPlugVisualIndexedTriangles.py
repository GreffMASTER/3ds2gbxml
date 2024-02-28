import logging
import os

import numpy as np
import xml.etree.ElementTree as ET
from modules.threedees import FacesDescription, MappingCoordinatesList, TriangularMesh, VerticesList, MappingCoordinates, ObjectBlock, Vertex, \
    VertexColors
from CPlugErrors import NoTrimeshError, NoVerticesError, NoFacesError


GBX_XML_HEADER = {
    'version': '6',
    'unknown': 'R',
    'class': 'CPlugVisualIndexedTriangles',
    'complvl': '1'
}


def compute_normals_gm(vertex: list[Vertex], faces: list[tuple]):
    normals = []

    for face in faces:
        A = np.array(vertex[face[0]].pos)
        B = np.array(vertex[face[1]].pos)
        C = np.array(vertex[face[2]].pos)
        AB = A - B
        AC = A - C

    return normals


def compute_normals(vertex: list[Vertex], facet: list[tuple]):
    normals = []
    vertexNormalLists = [[] for i in range(0, len(vertex))]
    for face in facet:
        a = vertex[face[0]].pos
        b = vertex[face[1]].pos
        c = vertex[face[2]].pos
        AB = np.array(a) - np.array(b)
        AC = np.array(a) - np.array(c)
        n = np.cross(AB, AC)
        n /= np.linalg.norm(n)
        for i in range(0, 3):
            vertexNormalLists[face[i]].append(n)
    for idx, normalList in enumerate(vertexNormalLists):
        normalSum = np.zeros(3)
        for normal in normalList:
          normalSum += normal
        normal = normalSum / float(len(normalList))
        normal /= np.linalg.norm(normal)
        normals.append(map(float, normal.tolist()))
    return normals


def _set_multiple(node: ET.Element, attrib: dict):
    for key, value in attrib.items():
        node.set(key, value)


def create_xml(model_object: ObjectBlock) -> ET.ElementTree:
    logging.info(f'Converting "{model_object.name}" to VisualMesh...')

    base_uv = None
    uv_list = None
    vertices = None
    triangles = None
    colors = None
    color_diff = 0

    trimesh: TriangularMesh = model_object.children[0]
    if not trimesh or not isinstance(trimesh, TriangularMesh):
        raise NoTrimeshError

    for child in trimesh.children:
        if isinstance(child, MappingCoordinates):
            base_uv = child
        if isinstance(child, VerticesList):
            vertices = child
        if isinstance(child, FacesDescription):
            triangles = child
        if isinstance(child, VertexColors):
            colors = child
        if isinstance(child, MappingCoordinatesList):
            uv_list = child

    if not triangles:
        raise NoFacesError
    if not vertices:
        raise NoVerticesError

    if base_uv:
        logging.info(f'Base UV: {len(base_uv.uv)}')
    if uv_list:
        logging.info(f'UV count: {len(uv_list.uv_list)}')
        for i in range(len(uv_list.uv_list)):
            logging.info(f'--- Count: {len(uv_list.uv_list[i])}')
    logging.info(f'Vertex: {len(vertices.vertices)}')
    logging.info(f'Polygons: {len(triangles.polygons)}')
    if colors:
        logging.info(f'Colors: {len(colors.vertex_colors)}')
        # some weird fix that doesnt work
        # i really need to make a new exporter instead
        #color_diff = int((len(vertices.vertices) - len(colors.vertex_colors)) / 2)
        #color_diff = len(vertices.vertices) - len(colors.vertex_colors)

    normals = compute_normals(vertices.vertices, triangles.polygons)

    gbx = ET.Element('gbx')
    _set_multiple(gbx, GBX_XML_HEADER)

    body = ET.Element('body')

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugVisual', 'id': '001'})
    chunk.append(ET.Element('node'))
    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugVisual', 'id': '004'})
    chunk.append(ET.Element('node'))
    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugVisual', 'id': '005'})
    value = ET.Element('uint32')
    value.text = '0'
    chunk.append(value)
    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugVisual', 'id': '006'})
    # HasVertexNormals
    value = ET.Element('uint32')
    value.text = '1'
    chunk.append(value)
    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugVisual', 'id': '007'})
    value = ET.Element('uint32')
    value.text = '0'
    chunk.append(value)
    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugVisual', 'id': '008'})
    # IsGeometryStatic
    value = ET.Element('bool')
    value.text = '1'
    chunk.append(value)
    # IsIndexationStatic
    value = ET.Element('bool')
    value.text = '1'
    chunk.append(value)
    # If has UV map
    if base_uv:
        if uv_list:
            value = ET.Element('int32')
            value.text = str(len(uv_list.uv_list))
            chunk.append(value)
        else:
            value = ET.Element('int32')
            value.text = '1'
            chunk.append(value)
    else:
        value = ET.Element('int32')
        value.text = '0'
        chunk.append(value)


    # SkinFlags(?)
    value = ET.Element('bool')
    value.text = '0'
    chunk.append(value)

    # Vertex count
    value = ET.Element('uint32')
    value.text = str(len(vertices.vertices))
    chunk.append(value)

    if uv_list:
        logging.info('Writing Additional UVs')
        for i, uv in enumerate(uv_list.uv_list):
            logging.info(f'{i}')
            value = ET.Element('bool')
            value.text = '0'
            chunk.append(value)

            for uv_coord in uv:
                value = ET.Element('vec2')
                value.text = f'{uv_coord[0]} {uv_coord[1]}'
                logging.info(value.text)
                chunk.append(value)
    elif base_uv:
        logging.info('Writing Base UV')
        value = ET.Element('bool')
        value.text = '0'
        chunk.append(value)

        for uv_coord in base_uv.uv:
            value = ET.Element('vec2')
            value.text = f'{uv_coord[0]} {uv_coord[1]}'
            logging.info(value.text)
            chunk.append(value)
        
        


    value = ET.Element('bool')
    value.text = '1'
    chunk.append(value)

    value = ET.Element('uint32')
    value.text = '0'
    chunk.append(value)

    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugVisual3D', 'id': '002'})
    chunk.append(ET.Element('node'))
    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugVisual3D', 'id': '003'})
    i = 0
    last_color = (1, 1, 1)
    for vertex in vertices.vertices:
        # Vertex position
        value = ET.Element('vec3')
        value.text = f'{vertex.pos[0]} {vertex.pos[1]} {vertex.pos[2]}'
        chunk.append(value)
        # Vertex normal
        value = ET.Element('vec3')

        normal = normals[i]
        txt = ''
        for v in normal:
            txt += f'{v} '
        value.text = txt[:-1]
        chunk.append(value)
        # Vertex color
        value = ET.Element('color')
        if colors:
            try:
                col = colors.vertex_colors[i-color_diff]
                float_col = 1 / 255
                value.text = f'{float_col * col[0]} {float_col * col[1]} {float_col * col[2]}'
                last_color = (float_col * col[0], float_col * col[1], float_col * col[2])
            except:
                value.text = f'{last_color[0]} {last_color[1]} {last_color[2]}'
        else:
            value.text = '1.0 1.0 1.0'
        chunk.append(value)
        # ???
        value = ET.Element('float')
        value.text = '1'
        chunk.append(value)
        i += 1

    value = ET.Element('uint32')
    value.text = '0'
    chunk.append(value)
    chunk.append(value)
    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugVisualIndexed', 'id': '000'})
    value = ET.Element('uint32')
    value.text = str(len(triangles.polygons)*3)
    chunk.append(value)

    for polygon in triangles.polygons:
        value = ET.Element('uint16')
        value.text = str(polygon[0])
        chunk.append(value)
        value = ET.Element('uint16')
        value.text = str(polygon[1])
        chunk.append(value)
        value = ET.Element('uint16')
        value.text = str(polygon[2])
        chunk.append(value)

    body.append(chunk)

    # Pack it up to ElementTree
    gbx.append(body)
    tree = ET.ElementTree(gbx)

    return tree
