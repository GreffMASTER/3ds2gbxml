import logging
import struct
from io import BytesIO

import numpy as np

from CPlugErrors import NoTrimeshError

class IncorrectFormatError(BaseException):
    pass


class DataError(BaseException):
    position: int
    args: tuple

    def __init__(self, position: int, args: tuple):
        self.position: int = position
        self.args = args


def _read_asciiz_string(file: BytesIO) -> str:
    out: str = ''
    while True:
        char = str(file.read(1), 'ascii')
        if char == '':
            raise DataError(file.tell(), ('asciiz string reached eof',))
        if ord(char) == 0:  # null character found, break
            break
        out += char
    return out


class Chunk:
    my_chunk_id: int
    my_chunk_size: int
    children: list = []
    file: BytesIO

    def __init__(self, data: bytes):
        logging.info(f'Reading "{self.__class__.__name__}"')
        self.file = BytesIO(data)
        self.children: list = []
        try:
            self.my_chunk_id = struct.unpack('<H', self.file.read(2))[0]
            self.my_chunk_size = struct.unpack('<I', self.file.read(4))[0]
            logging.info(f'Chunk size: {self.my_chunk_size}')
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)

    def _load_children(self, times: int = 99999999):
        logging.info('--++--')
        logging.info(f'Reading children for "{self.__class__.__name__}"')
        for i in range(times):
            # Check if there are any other child chunks in the buffer
            try:
                chunk_id = struct.unpack('<H', self.file.read(2))[0]
            except struct.error:
                logging.info(f'No more chunks for "{self.__class__.__name__}"')
                logging.info('--==--')
                break
            # Read child chunks
            try:
                chunk_size = struct.unpack('<I', self.file.read(4))[0]
                if chunk_size > self.my_chunk_size:
                    raise DataError(self.file.tell(), ('child chunk is bigger than parents, impossible!',))
            except struct.error as e:
                raise DataError(self.file.tell(), e.args)
            logging.info(f'Next chunk: "{hex(chunk_id)}" of size {chunk_size}')
            logging.info('------------------')
            # go back to start of the chunk

            self.file.seek(-6, 1)
            logging.info(f'Position: {hex(self.file.tell())}')
            chunk_data = self.file.read(chunk_size)

            try:
                match chunk_id:
                    case 0x0002:
                        self.children.append(M3DVersion(chunk_data))
                    case 0x0011:
                        self.children.append(Color24(chunk_data))
                    case 0x3d3d:
                        self.children.append(EditorChunk(chunk_data))
                    case 0x3d3e:
                        self.children.append(EditorConfiguration(chunk_data))
                    case 0x0100:
                        self.children.append(MasterScale(chunk_data))
                    case 0x4000:
                        self.children.append(ObjectBlock(chunk_data))
                    case 0x4100:
                        self.children.append(TriangularMesh(chunk_data))
                    case 0x4110:
                        self.children.append(VerticesList(chunk_data))
                    case 0x4112:
                        self.children.append(VertexNormals(chunk_data))
                    case 0x4115:
                        self.children.append(VertexColors(chunk_data))
                    case 0x4120:
                        self.children.append(FacesDescription(chunk_data))
                    case 0x4130:
                        self.children.append(FacesMaterial(chunk_data))
                    case 0x4140:
                        self.children.append(MappingCoordinates(chunk_data))
                    case 0x4145:
                        self.children.append(MappingCoordinatesList(chunk_data))
                    case 0x4150:
                        self.children.append(SmoothGroup(chunk_data))
                    case 0x4160:
                        self.children.append(AxisMatrix(chunk_data))
                    case 0xa000:
                        self.children.append(MaterialName(chunk_data))
                    case 0xa010:
                        self.children.append(AmbientColor(chunk_data))
                    case 0xa020:
                        self.children.append(DiffuseColor(chunk_data))
                    case 0xa030:
                        self.children.append(SpecularColor(chunk_data))
                    case 0xafff:
                        self.children.append(MaterialBlock(chunk_data))
                    case 0xb000:
                        self.children.append(KeyFramerChunk(chunk_data))
                    case 0xb002:
                        self.children.append(KeyFramerObject(chunk_data))
                    case 0xb008:
                        self.children.append(Frames(chunk_data))
                    case 0xb009:
                        self.children.append(UnknownClass1(chunk_data))
                    case 0xb00a:
                        self.children.append(KeyFramerHDR(chunk_data))
                    case 0xb010:
                        self.children.append(KeyFramerObjectName(chunk_data))
                    case 0xb013:
                        self.children.append(KeyFramerObjectPivotPosition(chunk_data))
                    case 0xb020:
                        self.children.append(KeyFramerObjectPositionTrack(chunk_data))
                    case 0xb021:
                        self.children.append(KeyFramerObjectRotationTrack(chunk_data))
                    case 0xb022:
                        self.children.append(KeyFramerObjectScaleTrack(chunk_data))
                    case 0xb030:
                        self.children.append(KeyFramerObjectHierarchyPosition(chunk_data))
                    case _:
                        logging.warning(f'Unknown or unimplemented chunk "{hex(chunk_id)}", skipping...')
            except DataError:
                raise


class M3DVersion(Chunk):
    version: int

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.version = struct.unpack('<I', self.file.read(4))[0]
            logging.info(f'Version: {self.version}')
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class MasterScale(Chunk):
    scale: float

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.scale = struct.unpack('<f', self.file.read(4))[0]
            logging.info(f'Scale: {self.scale}')
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class EditorConfiguration(Chunk):
    u1: int

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.u1 = struct.unpack('<I', self.file.read(4))[0]
            logging.info(f'U1: {self.u1}')
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class AmbientColor(Chunk):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children = []
            super()._load_children(1)
        except DataError:
            raise


class DiffuseColor(Chunk):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children = []
            super()._load_children(1)
        except DataError:
            raise


class SpecularColor(Chunk):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children = []
            super()._load_children(1)
        except DataError:
            raise


class Color24(Chunk):
    r: int
    g: int
    b: int

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            unpacked = struct.unpack('<BBB', self.file.read(3))
            self.r = unpacked[0]
            self.g = unpacked[1]
            self.b = unpacked[2]
            logging.info(f'Color: {self.r} {self.g} {self.b}')
        except struct as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class MaterialName(Chunk):
    name: str

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.name = _read_asciiz_string(self.file)
            logging.info(f'Material name: "{self.name}"')
        except DataError:
            raise


class MaterialBlock(Chunk):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            super()._load_children()
        except DataError:
            raise


class MappingCoordinates(Chunk):
    uv: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.uv: list = []
            count = struct.unpack('<H', self.file.read(2))[0]
            for i in range(count):
                uv_element = struct.unpack('<ff', self.file.read(8))
                self.uv.append(uv_element)
            logging.info(f'UV Size: {len(self.uv)}')
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class MappingCoordinatesList(Chunk):
    uv_list: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.uv_list: list = []

            count = struct.unpack('<H', self.file.read(2))[0]
            for i in range(count):
                uv_coords: list = []
                count2 = struct.unpack('<H', self.file.read(2))[0]
                for j in range(count2):
                    uv_element = struct.unpack('<ff', self.file.read(8))
                    uv_coords.append(uv_element)
                self.uv_list.append(uv_coords)
            logging.info(f'UV List Size: {len(self.uv_list)}')
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class AxisMatrix(Chunk):
    matrix: list = [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.matrix: list = [
                [0, 0, 0],
                [0, 0, 0],
                [0, 0, 0],
                [0, 0, 0]
            ]
            for i in range(4):
                for j in range(3):
                    self.matrix[i][j] = struct.unpack('<f', self.file.read(4))[0]
            logging.info(self.matrix)
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class SmoothGroup(Chunk):
    smooth_group_list: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.smooth_group_list: list = []
        except DataError:
            raise
        while True:
            try:
                self.smooth_group_list.append(struct.unpack('<I', self.file.read(4))[0])
            except struct.error:
                break


class FacesMaterial(Chunk):
    material_name: str
    applied_faces: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.applied_faces: list = []
            self.material_name = _read_asciiz_string(self.file)
            logging.info(f'Name: "{self.material_name}"')

            count = struct.unpack('<H', self.file.read(2))[0]
            for i in range(count):
                face_index = struct.unpack('<H', self.file.read(2))[0]
                self.applied_faces.append(face_index)
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class FacesDescription(Chunk):
    polygons: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.polygons: list = []
            count = struct.unpack('<H', self.file.read(2))[0]
            for i in range(count):
                # polygon[3] is used for editor info, such as selected faces
                polygon = struct.unpack('<HHHH', self.file.read(8))
                self.polygons.append(polygon)
            logging.info(f'Polygon count: {len(self.polygons)}')
            super()._load_children()
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class Vertex:
    pos: tuple = (0.0, 0.0, 0.0)
    normal: tuple = (0.0, 0.0, 0.0)

    def __init__(self, x: float = 0, y: float = 0, z: float = 0, *, position: tuple = None):
        if position:
            self.pos = position
            return
        self.pos = (x, y, z)
        self.normal = (0.0, 0.0, 0.0)


class VerticesList(Chunk):
    vertices: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.vertices: list = []
            vertex_count = struct.unpack('<H', self.file.read(2))[0]
            logging.info(f'Vertices count: {vertex_count}')
            for i in range(vertex_count):
                vertex = Vertex(position=struct.unpack('<fff', self.file.read(12)))
                self.vertices.append(vertex)
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class VertexNormals(Chunk):
    vertex_normals: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.vertex_normals: list = []
            vertex_count = struct.unpack('<H', self.file.read(2))[0]

            logging.info(f'Vertex normal count: {vertex_count}')
            for i in range(vertex_count):
                vertex_normal = struct.unpack('<fff', self.file.read(12))
                self.vertex_normals.append(vertex_normal)
            super()._load_children(vertex_count)
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class VertexColors(Chunk):
    vertex_colors: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.vertex_colors: list = []
            vertex_count = struct.unpack('<H', self.file.read(2))[0]

            logging.info(f'Vertex color count: {vertex_count}')
            for i in range(vertex_count):
                vertex_color = struct.unpack('<BBB', self.file.read(3))
                self.vertex_colors.append(vertex_color)
            super()._load_children(vertex_count)
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class TriangularMesh(Chunk):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            super()._load_children()
        except DataError:
            raise


class ObjectBlock(Chunk):
    name: str

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.name = _read_asciiz_string(self.file)
            logging.info(f'Name: "{self.name}"')
            super()._load_children()
        except DataError:
            raise


class EditorChunk(Chunk):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            super()._load_children()
        except DataError:
            raise


class KeyFramerHDR(Chunk):
    u1: int
    u2: str
    u3: int

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            self.u1 = struct.unpack('<H', self.file.read(2))[0]
            self.u2 = _read_asciiz_string(self.file)
            self.u1 = struct.unpack('<I', self.file.read(4))[0]
        except struct.error as e:
            raise DataError(self.file.tell(), e.args)
        except DataError:
            raise


class KeyFramerChunk(Chunk):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            super()._load_children()
        except DataError:
            raise


class MainChunk(Chunk):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            super()._load_children()
        except DataError:
            raise

    def GetAllObjects(self):
        objects = []

        for editor_chunk in self.children:
            if isinstance(editor_chunk, EditorChunk):
                for obj in editor_chunk.children:
                    if isinstance(obj, ObjectBlock):
                        if len(obj.children) > 0:
                            objects.append(obj)
        return objects

    def GetAllVertices(self, UseVertex: bool = False):
        objects = self.GetAllObjects()
        vertices_all = []

        for model_object in objects:
            trimesh: TriangularMesh = model_object.children[0]
            if not trimesh or not isinstance(trimesh, TriangularMesh):
                raise NoTrimeshError
            for child in trimesh.children:
                if isinstance(child, VerticesList):
                    for vert in child.vertices:
                        vert: Vertex
                        if UseVertex:
                            vertices_all.append(vert)
                        else:
                            vertices_all.append(vert.pos)

        return vertices_all

    def GetAllFaces(self):
        objects = self.GetAllObjects()

        vert_count = 0
        face_count = 0
        vertices_all = []
        triangles_all = []

        # adding all the vertices and faces into big global arrays
        # setting the vertex and face indexes by an offset
        for model_object in objects:
            new_vert_count = 0
            new_face_count = 0

            trimesh: TriangularMesh = model_object.children[0]
            if not trimesh or not isinstance(trimesh, TriangularMesh):
                raise NoTrimeshError

            for child in trimesh.children:
                if isinstance(child, VerticesList):
                    new_vert_count = len(child.vertices)
                    vertices_all = vertices_all + child.vertices

                if isinstance(child, FacesDescription):
                    temp = child.polygons.copy()
                    for i in range(len(temp)):  # Update vertex references
                        poly = temp[i]
                        new_poly = (poly[0] + vert_count, poly[1] + vert_count, poly[2] + vert_count)
                        temp[i] = new_poly
                    new_face_count = len(temp)
                    triangles_all = triangles_all + temp

            vert_count = vert_count + new_vert_count
            face_count = face_count + new_face_count

        return triangles_all

    def GetAllNormals(self):
        normal_all = []
        normals = compute_normals(self.GetAllVertices(True), self.GetAllFaces())
        for norm in normals:
            n = []
            for k in norm:
                n.append(k)
            normal_all.append(n)
        return normal_all

    def GetBoundingBox(self):
        verts = self.GetAllVertices(True)
        return _calculate_bounding_box(verts)


class Frames(Chunk):
    start_frame: int = 0
    end_frame: int = 0

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.start_frame = struct.unpack('<I', self.file.read(4))[0]
            self.end_frame = struct.unpack('<I', self.file.read(4))[0]
        except DataError:
            raise


class UnknownClass1(Chunk):
    u1: int = 0

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.u1 = struct.unpack('<I', self.file.read(4))[0]
        except DataError:
            raise


class KeyFramerObject(Chunk):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.children: list = []
            super()._load_children()
        except DataError:
            raise


class KeyFramerObjectName(Chunk):
    name: str = ''
    u1: int = 0
    u2: int = 0

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.name = _read_asciiz_string(self.file)
            self.u1 = struct.unpack('<I', self.file.read(4))[0]
            self.u2 = struct.unpack('<H', self.file.read(2))[0]
        except DataError:
            raise


class KeyFramerObjectPivotPosition(Chunk):
    x: float = 0
    y: float = 0
    z: float = 0

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.x = struct.unpack('<f', self.file.read(4))[0]
            self.y = struct.unpack('<f', self.file.read(4))[0]
            self.z = struct.unpack('<f', self.file.read(4))[0]
        except DataError:
            raise


class KeyFramerObjectPositionTrack(Chunk):
    frames: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.frames = []
            self.file.read(10)  # idk
            n_keys = self.u2 = struct.unpack('<H', self.file.read(2))[0]
            self.file.read(2)  # idk
            for i in range(n_keys):
                frame = {
                    'nframe': struct.unpack('<H', self.file.read(2))[0]
                }
                self.file.read(4)  # idk
                frame['x'] = struct.unpack('<f', self.file.read(4))[0]
                frame['y'] = struct.unpack('<f', self.file.read(4))[0]
                frame['z'] = struct.unpack('<f', self.file.read(4))[0]
        except DataError:
            raise


class KeyFramerObjectRotationTrack(Chunk):
    frames: list = []

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.frames = []
            self.file.read(10)  # idk
            n_keys = self.u2 = struct.unpack('<H', self.file.read(2))[0]
            self.file.read(2)  # idk
            for i in range(n_keys):
                frame = {
                    'nframe': struct.unpack('<H', self.file.read(2))[0]
                }
                self.file.read(4)  # idk
                frame['rad'] = struct.unpack('<f', self.file.read(4))[0]
                frame['axis_x'] = struct.unpack('<f', self.file.read(4))[0]
                frame['axis_y'] = struct.unpack('<f', self.file.read(4))[0]
                frame['axis_z'] = struct.unpack('<f', self.file.read(4))[0]
        except DataError:
            raise


class KeyFramerObjectScaleTrack(KeyFramerObjectPositionTrack):
    def __init__(self, data: bytes):
        try:
            super().__init__(data)

        except DataError:
            raise


class KeyFramerObjectHierarchyPosition(Chunk):
    u1: int = 0

    def __init__(self, data: bytes):
        try:
            super().__init__(data)
            self.u2 = struct.unpack('<H', self.file.read(2))[0]
        except DataError:
            raise


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


def read_3ds(path: str) -> MainChunk:
    try:
        file = open(path, 'rb')
    except OSError:
        raise
    logging.info(f'Parsing file "{path}"...')
    chunk_id = hex(struct.unpack('<H', file.read(2))[0])
    if chunk_id != '0x4d4d':
        raise IncorrectFormatError
    try:
        chunk_size = struct.unpack('<I', file.read(4))[0]
    except struct.error as e:
        raise DataError(file.tell(), e.args)
    # go back to start of the chunk
    file.seek(-6, 1)
    chunk_data = file.read(chunk_size)
    try:
        chunk = MainChunk(chunk_data)
    except DataError:
        raise

    file.close()
    logging.info('Parsing complete!')
    return chunk
