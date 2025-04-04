from __future__ import annotations
from dataclasses import dataclass, field
import struct

@dataclass
class Identifier:
    length: int = 0
    name: str = ""
        
    @classmethod
    def from_file(cls, file) -> Identifier:
        self = cls()
        self.length = int(struct.unpack("<H", file.read(2))[0])
        if self.length < 1:
            self.name = None
            return self
        self.name = struct.unpack("<{}s".format(self.length), file.read(self.length))[0].decode()
        return self

@dataclass
class Material:
    name: str = ""
    ambient: tuple[float, float, float] = (0.2, 0.2, 0.2)
    diffuse: tuple[float, float, float] = (1.0, 1.0, 2.0)
    specular: tuple[float, float, float] = (0.45, 0.45, 0.45)
    specular_power: float = 1.0
    lighting_model: bytes = 0

    @classmethod
    def from_file(cls, file) -> Material:
        self = cls()
        self.name = Identifier.from_file(file).name
        self.ambient = struct.unpack("<3f", file.read(12))
        self.diffuse = struct.unpack("<3f", file.read(12))
        self.specular = struct.unpack("<3f", file.read(12))
        self.specular_power = struct.unpack("<f", file.read(4))[0]
        self.lighting_model = struct.unpack("<b", file.read(1))[0]
        return self

@dataclass
class Face:
    indices: list[int] = field(default_factory=list)
    tc_indices: list[int] = field(default_factory=list)

    @classmethod
    def from_file(cls, file) -> Face:
        self = cls()
        self.indices = []
        self.tc_indices = []
        for i in range(3):
            self.indices.append(struct.unpack("<H", file.read(2))[0])
            self.tc_indices.append(struct.unpack("<H", file.read(2))[0])
        return self

@dataclass
class Vertex_group:
    num_faces: int = 0
    material: str = ""
    faces: list[Face] = field(default_factory=list)

    @classmethod
    def from_file(cls, file) -> Vertex_group:
        self = cls()
        self.num_faces = struct.unpack("<H", file.read(2))[0]
        self.material = Identifier.from_file(file).name
        self.faces = []
        for i in range(self.num_faces):
            self.faces.append(Face.from_file(file))
        return self

@dataclass
class Mesh:
    material: str = ""
    texture: str = ""
    num_vertices: int = 0
    num_tcs: int = 0
    num_groups: int = 0
    verts: list[tuple[float, float, float]] = field(default_factory=list)
    tcs: list[tuple[float, float]] = field(default_factory=list)
    groups: list[Vertex_group] = field(default_factory=list)
    cull_type: bytes = 0

    @classmethod
    def from_file(cls, file, sod_version) -> Mesh:
        self = cls()
        if (sod_version > 1.6):
            self.material = Identifier.from_file(file).name
        else:
            self.material = "Default"
        self.texture = Identifier.from_file(file).name
        self.num_vertices = struct.unpack("<H", file.read(2))[0]
        self.num_tcs = struct.unpack("<H", file.read(2))[0]
        self.num_groups = struct.unpack("<H", file.read(2))[0]
        
        self.verts = [struct.unpack("<3f", file.read(12)) for v in range(self.num_vertices)]
        self.tcs = [struct.unpack("<2f", file.read(8)) for t in range(self.num_tcs)]
        self.groups = [Vertex_group.from_file(file) for g in range(self.num_groups)]
        self.cull_type = struct.unpack("<b", file.read(1))[0]
        file.read(2) # unused space for padding I guess
        return self

VALID_NODE_TYPES = (0, 1, 3, 11, 12)
@dataclass
class Node:
    type: int = 0
    name: str = ""
    root: str = ""
    mat34: tuple[float] = (1,0,0,0,0,1,0,0,0,0,1,0)
    emitter: str = ""
    mesh: Mesh | None = None

    @classmethod
    def from_file(cls, file, sod_version) -> Node:
        self = cls()
        self.type = struct.unpack("<H", file.read(2))[0]
        self.name = Identifier.from_file(file).name
        self.root = Identifier.from_file(file).name
        self.mat34 = struct.unpack("<12f", file.read(12*4))
        if self.type == 12:
            self.emitter = Identifier.from_file(file).name
        elif self.type == 1:
            self.mesh = Mesh.from_file(file, sod_version)
        elif self.type not in VALID_NODE_TYPES:
            print("Error in file. Incorrect node type found")
        return self

@dataclass
class Animation_channel:
    name: str = ""
    num_keyframes: int = 0
    length: float = 0.0
    matrices: list[tuple[float]] = field(default_factory=list)

    @classmethod
    def from_file(cls, file) -> Animation_channel:
        self = cls()
        self.name = Identifier.from_file(file).name
        self.num_keyframes = struct.unpack("<H", file.read(2))[0]
        self.length = struct.unpack("<f", file.read(4))[0]
        file.read(2) # unused space for padding I guess
        self.matrices = []
        for j in range(self.num_keyframes):
            self.matrices.append(struct.unpack("<12f", file.read(12*4)))
        return self

@dataclass
class Animation_reference:
    type: bytes = 0
    node: str = ""
    anim: str = ""
    offset: float = 0.0

    @classmethod
    def from_file(cls, file, sod_version) -> Animation_reference:
        self = cls()
        self.type = struct.unpack("<b", file.read(1))[0]
        self.node = Identifier.from_file(file).name
        self.anim = Identifier.from_file(file).name
        if sod_version >= 1.8:
            self.offset = struct.unpack("<f", file.read(4))[0]
        else:
            self.offset = 0.0
        return self

@dataclass
class SOD:
    materials: dict[Material] = field(default_factory=dict)
    nodes: dict[Node] = field(default_factory=dict)
    channels: dict[Animation_channel] = field(default_factory=dict)
    references: dict[Animation_reference] = field(default_factory=dict)

    @classmethod
    def from_file_path(cls, file_path) -> SOD:
        self = cls()
        materials = {}
        nodes = {}
        channels = {}
        references = {}
        with open(file_path, "rb") as file:
            ident = file.read(10).decode()
            if ident != "Storm3D_SW":
                print("Not a valid sod file")
                return
            version = file.read(4)

            if version == struct.pack("<f", 1.6):
                whatever = struct.unpack("<H", file.read(2))[0]
                for i in range(whatever):
                    len = struct.unpack("<H", file.read(2))[0]
                    text = struct.unpack("<{}s".format(len), file.read(len))[0].decode()
                    len = struct.unpack("<H", file.read(2))[0]
                    text = struct.unpack("<{}s".format(len), file.read(len))[0].decode()
                    file.read(7)
            elif version != struct.pack("<f", 1.8) and version != struct.pack("<f", 1.7):
                print("Not a supported sod file")
                return
            
            version = round(struct.unpack("<f", version)[0],2)

            num_mats = struct.unpack("<H", file.read(2))[0]
            print("num_mats", num_mats)
            for i in range(num_mats):
                material = Material.from_file(file)
                materials[material.name] = material

            num_nodes = struct.unpack("<H", file.read(2))[0]
            print("num_nodes", num_nodes)
            for i in range(num_nodes):
                node = Node.from_file(file, version)
                nodes[node.name] = node

            num_animation_channels = struct.unpack("<H", file.read(2))[0]
            print("num_animation_channels", num_animation_channels)
            for i in range(num_animation_channels):
                channel = Animation_channel.from_file(file)
                channels[channel.name] = channel

            num_animation_references = struct.unpack("<H", file.read(2))[0]
            print("num_animation_references", num_animation_references)
            for i in range(num_animation_references):
                reference = Animation_reference.from_file(file, version)
                references[reference.node] = reference

        self.nodes = nodes
        self.materials = materials
        self.channels = channels
        self.references = references
        return self
