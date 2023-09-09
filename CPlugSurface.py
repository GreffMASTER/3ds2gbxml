import logging
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
    'Snow': 21
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


def create_xml(model_object: ObjectBlock) -> ET.ElementTree:
    name_data = model_object.name.split('$')
    logging.info(f'Converting "{name_data[0]}" to Surface...')
    vertices = None
    triangles = None
    material = None

    trimesh: TriangularMesh = model_object.children[0]
    if not trimesh or not isinstance(trimesh, TriangularMesh):
        raise NoTrimeshError

    for child in trimesh.children:
        if isinstance(child, VerticesList):
            vertices = child
        if isinstance(child, FacesDescription):
            triangles = child
    for child in triangles.children:
        if isinstance(child, FacesMaterial):
            material = child

    if not triangles:
        raise NoFacesError
    if not vertices:
        raise NoVerticesError

    if material:
        logging.info(f'Material: "{material.material_name}"')
    logging.info(f'Vertex: {len(vertices.vertices)}')
    logging.info(f'Polygons: {len(triangles.polygons)}')

    gbx = ET.Element('gbx')

    if len(name_data) < 2:
        _set_multiple(gbx, GBX_XML_HEADER)
    else:
        _set_multiple(gbx, GBX_XML_HEADER_GEOM)

    body = ET.Element('body')

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugSurface', 'id': '000'})
    chunk.append(ET.Element('node'))
    body.append(chunk)

    chunk = ET.Element('chunk')
    _set_multiple(chunk, {'class': 'CPlugSurface', 'id': '001'})
    _set_value(chunk, 'uint32', '1')
    body.append(chunk)

    if len(name_data) < 2:

        chunk = ET.Element('chunk')
        _set_multiple(chunk, {'class': '0900D000', 'id': '002'})
        _set_value(chunk, 'uint32', '2')  # version

        lst = ET.Element('list')

        for vertex in vertices.vertices:
            le = ET.Element('element')
            _set_value(le, 'vec3', f'{vertex.pos[0]} {vertex.pos[1]} {vertex.pos[2]}')
            lst.append(le)

        chunk.append(lst)

        lst = ET.Element('list')

        i = 0
        for polygon in triangles.polygons:
            le = ET.Element('element')
            v_a = numpy.array(vertices.vertices[polygon[0]].pos)
            v_b = numpy.array(vertices.vertices[polygon[1]].pos)
            v_c = numpy.array(vertices.vertices[polygon[2]].pos)
            direct = numpy.cross(v_b - v_a, v_c - v_a)
            direct = direct / numpy.linalg.norm(direct)
            print(direct)
            _set_value(le, 'vec4', f'{direct[0]} {direct[1]} {direct[2]} {-vertices.vertices[polygon[0]].pos[1]}')
            _set_value(le, 'uint32', str(polygon[0]))
            _set_value(le, 'uint32', str(polygon[1]))
            _set_value(le, 'uint32', str(polygon[2]))
            # SurfaceType
            value = ET.Element('uint16')
            if material:
                surf_type = SURF_DICT.get(material.material_name)
                if surf_type:
                    if i in material.applied_faces:
                        value.text = str(surf_type)
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

        lst = ET.Element('list')
        # TODO implement MeshOctreeCells
        """ 
        i = 0
        for vertex in vertices.vertices:
    
            le = ET.Element('element')
    
            value = ET.Element('uint32')
            value.text = '1'
            le.append(value)
    
            value = ET.Element('vec3')
            value.text = f'{vertex[0]} {vertex[1]} {vertex[2]}'
            le.append(value)
    
            value = ET.Element('vec3')
            value.text = f'{vertex[0]/16} {vertex[1]/16} {vertex[2]/16}'
            le.append(value)
    
            value = ET.Element('uint32')
            value.text = str(i)
            le.append(value)
    
            lst.append(le)
            i += 1
        """

        chunk.append(lst)

        body.append(chunk)
    else:
        match name_data[1]:
            case 'Sphere':
                chunk = ET.Element('chunk')
                _set_multiple(chunk, {'class': '0900F000', 'id': '002'})
                _set_value(chunk, 'uint32', '0')
                width = 0.5
                logging.info(f'Sphere width: {width}')
                _set_value(chunk, 'float', str(width))
                if material:
                    surf_type = SURF_DICT.get(material.material_name)
                    if surf_type:
                        _set_value(chunk, 'uint16', str(surf_type))
                    else:
                        _set_value(chunk, 'uint16', '0')
                else:
                    _set_value(chunk, 'uint16', '0')
                body.append(chunk)

    # Pack it up to ElementTree
    gbx.append(body)
    tree = ET.ElementTree(gbx)

    return tree
