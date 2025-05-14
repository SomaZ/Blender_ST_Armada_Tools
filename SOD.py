# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2025 SomaZ
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ##### END MIT LICENSE BLOCK #####

from __future__ import annotations
from dataclasses import dataclass, field
import struct

SUPPORTED_VERSIONS = (1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.91, 1.92, 1.93)

@dataclass
class Identifier:
    name: str = ""
        
    @classmethod
    def from_file(cls, file) -> Identifier:
        self = cls()
        length = int(struct.unpack("<H", file.read(2))[0])
        if length < 1:
            self.name = None
            return self
        self.name = struct.unpack("<{}s".format(length), file.read(length))[0].decode()
        return self
    
    def to_bytearray(self) -> bytearray:
        array = bytearray()
        if (not self.name or len(self.name) == 0):
            array += struct.pack("<H", 0)
            return array
        array += struct.pack("<H", len(self.name))
        array += self.name.encode(encoding="ascii", errors="replace")
        return array

@dataclass
class Material:
    name: str = ""
    ambient: tuple[float, float, float] = (0.2, 0.2, 0.2)
    diffuse: tuple[float, float, float] = (1.0, 1.0, 2.0)
    specular: tuple[float, float, float] = (0.45, 0.45, 0.45)
    specular_power: float = 1.0
    lighting_model: bytes = 0
    unknown: bytes = 0

    @classmethod
    def from_file(cls, file, sod_version) -> Material:
        self = cls()
        self.name = Identifier.from_file(file).name
        self.ambient = struct.unpack("<3f", file.read(12))
        self.diffuse = struct.unpack("<3f", file.read(12))
        self.specular = struct.unpack("<3f", file.read(12))
        self.specular_power = struct.unpack("<f", file.read(4))[0]
        self.lighting_model = struct.unpack("<b", file.read(1))[0]
        if sod_version >= 1.9:
            self.unknown = struct.unpack("<b", file.read(1))[0]

        return self
    
    def to_bytearray(self, sod_version) -> bytearray:
        array = bytearray()
        array += Identifier(self.name).to_bytearray()
        array += struct.pack("<3f", *self.ambient)
        array += struct.pack("<3f", *self.diffuse)
        array += struct.pack("<3f", *self.specular)
        array += struct.pack("<f", self.specular_power)
        array += struct.pack("<b", self.lighting_model)
        if sod_version >= 1.9:
            array += struct.pack("<b", self.unknown)
        return array

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
    
    def to_bytearray(self) -> bytearray:
        array = bytearray()
        for index, tc_index in zip(self.indices, self.tc_indices):
            array += struct.pack("<H", index)
            array += struct.pack("<H", tc_index)
        return array

@dataclass
class Vertex_group:
    material: str = ""
    faces: list[Face] = field(default_factory=list)

    @classmethod
    def from_file(cls, file) -> Vertex_group:
        self = cls()
        num_faces = struct.unpack("<H", file.read(2))[0]
        self.material = Identifier.from_file(file).name
        self.faces = []
        for i in range(num_faces):
            self.faces.append(Face.from_file(file))
        return self
    
    def to_bytearray(self) -> bytearray:
        array = bytearray()
        array += struct.pack("<H", len(self.faces))
        array += Identifier(self.material).to_bytearray()
        for face in self.faces:
            array += face.to_bytearray()
        return array

@dataclass
class Mesh:
    material: str = ""
    texture: str = ""
    verts: list[tuple[float, float, float]] = field(default_factory=list)
    tcs: list[tuple[float, float]] = field(default_factory=list)
    groups: list[Vertex_group] = field(default_factory=list)
    cull_type: bytes = 0

    # Armada 2 specific fields
    illumination: bool = False
    bumpmap: str = ""
    use_heightmap: bool = True
    assimilation_texture: str = ""

    @classmethod
    def from_file(cls, file, sod_version) -> Mesh:
        self = cls()

        if (sod_version >= 1.7):
            self.material = Identifier.from_file(file).name
        else:
            self.material = "default"

        num_textures = 1
        if (sod_version >= 1.93):
            mesh_flags = struct.unpack("<I", file.read(4))[0] # 0, 4 or 6
            if mesh_flags & 4:
                self.illumination = True
            num_textures = struct.unpack("<I", file.read(4))[0]

        self.texture = Identifier.from_file(file).name
        self.bumpmap = None

        if (sod_version == 1.91):
            unknown_texinfo = file.read(2)
        elif (sod_version == 1.92):
            self.assimilation_texture = Identifier.from_file(file).name
            unknown_texinfo = struct.unpack("<H", file.read(2))[0] # always 0
        elif (sod_version >= 1.93):
            unknown_info = struct.unpack("<I", file.read(4))[0] # always 0

            if num_textures == 2:
                self.bumpmap = Identifier.from_file(file).name
                bump_type = struct.unpack("<I", file.read(4))[0] # always 512 in vanilla files
                if not (bump_type & 512):
                    self.use_heightmap = False

            self.assimilation_texture = Identifier.from_file(file).name
            unknown_texinfo = struct.unpack("<H", file.read(2))[0] #always 0

        num_vertices = struct.unpack("<H", file.read(2))[0]
        num_tcs = struct.unpack("<H", file.read(2))[0]
        num_groups = struct.unpack("<H", file.read(2))[0]
        
        self.verts = [struct.unpack("<3f", file.read(12)) for v in range(num_vertices)]
        self.tcs = [struct.unpack("<2f", file.read(8)) for t in range(num_tcs)]
        self.groups = [Vertex_group.from_file(file) for g in range(num_groups)]
        self.cull_type = struct.unpack("<b", file.read(1))[0]

        unknown = struct.unpack("<H", file.read(2))[0]
        for i in range(unknown):
            file.read(2)
        return self
    
    def to_bytearray(self, sod_version = 1.8) -> bytearray:
        array = bytearray()
        if sod_version >= 1.7:
            if sod_version <= 1.8 and self.material == "opaque":
                array += Identifier("default").to_bytearray()
            else:
                array += Identifier(self.material).to_bytearray()

        if (sod_version >= 1.93):
            num_textures = 1
            mesh_flag = 0
            if self.bumpmap:
                num_textures = 2
                mesh_flag += 2 # use bumpmapping
            if self.illumination:
                mesh_flag += 4 # use texture alpha channel for self illumination

            array += struct.pack("<I", mesh_flag)
            array += struct.pack("<I", num_textures)

        array += Identifier(self.texture).to_bytearray()

        if (sod_version == 1.91):
            array += struct.pack("<H", 0)
        elif (sod_version == 1.92):
            array += Identifier(self.assimilation_texture).to_bytearray()
            array += struct.pack("<H", 0)
        elif (sod_version >= 1.93):
            array += struct.pack("<I", 0)
            if num_textures == 2:
                array += Identifier(self.bumpmap).to_bytearray()
                array += struct.pack("<I", 512 if self.use_heightmap else 0) # 512 is a flag to use a hightmap instead of a normalmap
            array += Identifier(self.assimilation_texture).to_bytearray()
            array += struct.pack("<H", 0)

        array += struct.pack("<H", len(self.verts))
        array += struct.pack("<H", len(self.tcs))
        array += struct.pack("<H", len(self.groups))
        for vert in self.verts:
            array += struct.pack("<3f", *vert)
        for tc in self.tcs:
            array += struct.pack("<2f", *tc)
        for group in self.groups:
            array += group.to_bytearray()
        array += struct.pack("<b", self.cull_type)
        array += struct.pack("<H", 0)
        return array

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
            print("Error in file. Incorrect node type found. Node:", self.name, "Type:", self.type)
        return self
    
    def to_bytearray(self, sod_version = 1.8) -> bytearray:
        array = bytearray()
        array += struct.pack("<H", self.type)
        array += Identifier(self.name).to_bytearray()
        array += Identifier(self.root).to_bytearray()
        array += struct.pack("<12f", *self.mat34)
        if self.type == 12:
            array += Identifier(self.emitter).to_bytearray()
        elif self.type == 1:
            array += self.mesh.to_bytearray(sod_version)
        return array

@dataclass
class Animation_channel:
    name: str = ""
    length: float = 0.0
    matrices: list[tuple[float]] = field(default_factory=list)
    scales: list[float] = field(default_factory=list)
    animation_type: int = 0

    @classmethod
    def from_file(cls, file) -> Animation_channel:
        self = cls()
        self.name = Identifier.from_file(file).name
        num_keyframes = struct.unpack("<H", file.read(2))[0]
        self.length = struct.unpack("<f", file.read(4))[0]
        self.animation_type = struct.unpack("<H", file.read(2))[0]
        if self.animation_type == 5:
            self.scales = []
            for j in range(num_keyframes):
                self.scales.append(struct.unpack("<f", file.read(4))[0])
            return self
        
        self.matrices = []
        for j in range(num_keyframes):
            self.matrices.append(struct.unpack("<12f", file.read(12*4)))
        return self
    
    def to_bytearray(self) -> bytearray:
        array = bytearray()
        array += Identifier(self.name).to_bytearray()
        if len(self.scales):
            array += struct.pack("<H", len(self.scales))
        else:
            array += struct.pack("<H", len(self.matrices))
        array += struct.pack("<f", self.length)
        if len(self.scales):
            array += struct.pack("<H", 5)
            for scale in self.scales:
                array += struct.pack("<f", scale)
            return array
        
        array += struct.pack("<H", 0)
        for mat34 in self.matrices:
            array += struct.pack("<12f", *mat34)
        return array

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
    
    def to_bytearray(self, sod_version = 1.8) -> bytearray:
        array = bytearray()
        array += struct.pack("<b", self.type)
        array += Identifier(self.node).to_bytearray()
        array += Identifier(self.anim).to_bytearray()
        if sod_version >= 1.8:
            array += struct.pack("<f", self.offset)
        return array

@dataclass
class SOD:
    version: float = 0.0
    materials: dict[Material] = field(default_factory=dict)
    nodes: dict[Node] = field(default_factory=dict)
    channels: dict[list[Animation_channel]] = field(default_factory=dict)
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
            if ident != "Storm3D_SW" and ident != "StarTrekDB":
                raise Exception("Not a valid sod file. File ident was {}. Expected 'Storm3D_SW' or 'StarTrekDB'".format(ident))

            version = file.read(4)
            self.version = round(struct.unpack("<f", version)[0], 2)
            print("File:", file_path.replace("\\", "/").rsplit("/", 1)[1], self.version)

            if self.version in (1.4, 1.5, 1.6):
                whatever = struct.unpack("<H", file.read(2))[0]
                for i in range(whatever):
                    len = struct.unpack("<H", file.read(2))[0]
                    text = struct.unpack("<{}s".format(len), file.read(len))[0].decode()
                    len = struct.unpack("<H", file.read(2))[0]
                    text = struct.unpack("<{}s".format(len), file.read(len))[0].decode()
                    file.read(7)
                    
            elif self.version not in SUPPORTED_VERSIONS:
                raise Exception("Not a supported sod file. File version was {}".format(self.version))

            num_mats = struct.unpack("<H", file.read(2))[0]
            print("Materials:", num_mats)
            for i in range(num_mats):
                material = Material.from_file(file, self.version)
                materials[material.name] = material

            num_nodes = struct.unpack("<H", file.read(2))[0]
            print("Nodes:", num_nodes)
            for i in range(num_nodes):
                node = Node.from_file(file, self.version)
                nodes[node.name] = node

            num_animation_channels = struct.unpack("<H", file.read(2))[0]
            print("Mesh Animations", num_animation_channels)
            for i in range(num_animation_channels):
                channel = Animation_channel.from_file(file)
                if channel.name in channels:
                    channels[channel.name].append(channel)
                    continue
                channels[channel.name] = [channel]

            if self.version in (1.4, 1.5):
                self.nodes = nodes
                self.materials = materials
                self.channels = channels
                self.references = {}
                return self

            num_animation_references = struct.unpack("<H", file.read(2))[0]
            print("Texture Animations", num_animation_references)
            for i in range(num_animation_references):
                reference = Animation_reference.from_file(file, self.version)
                references[reference.node] = reference

        self.nodes = nodes
        self.materials = materials
        self.channels = channels
        self.references = references
        return self
    
    def to_file(self, file_path):

        if self.version not in SUPPORTED_VERSIONS:
            raise Exception(
                "No valid sod version for writing the file. Version was {}".format(self.version))
        
        array = bytearray()
        if self.version in (1.4, 1.5):
            array += "StarTrekDB".encode(encoding="ascii")
        else:
            array += "Storm3D_SW".encode(encoding="ascii")
        array += struct.pack("<f", self.version)
        if self.version == 1.6:
            array += struct.pack("<H", 0)
        array += struct.pack("<H", len(self.materials))
        for mat in self.materials.values():
            array += mat.to_bytearray(self.version)
        array += struct.pack("<H", len(self.nodes))
        for node in self.nodes.values():
            array += node.to_bytearray(self.version)

        channel_count = 0
        for channel_list in self.channels.values():
            channel_count += len(channel_list)
        array += struct.pack("<H", channel_count)
        for channel_list in self.channels.values():
            for channel in channel_list:
                array += channel.to_bytearray()

        if self.version not in (1.4, 1.5):
            array += struct.pack("<H", len(self.references))
            for ref in self.references.values():
                array += ref.to_bytearray(self.version)

        with open(file_path, "wb") as file:
            file.write(array)
        return
