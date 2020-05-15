from __future__ import annotations

import os
from typing import Tuple, Union, Any

import wx

import numpy as np

import amulet_nbt as nbt
from amulet import BlockManager, SelectionGroup
from amulet.api.data_types import AnyNDArray
from amulet.api.wrapper import Interface, FormatWraper
from amulet_map_editor import log
from amulet_map_editor.amulet_wx.block_select import VersionSelect

from amulet_map_editor.amulet_wx.simple import SimpleDialog

from amulet.api.structure import Structure
from amulet.operations.paste import paste
from amulet.api.world import World

class SchematicInterface(Interface):
    def decode(self, cx: int, cz: int, data: Any) -> Tuple["Chunk", AnyNDArray]:
        pass

    def encode(self, chunk: "Chunk", palette: AnyNDArray,
               max_world_version: Tuple[str, Union[int, Tuple[int, int, int]]]) -> Any:
        pass

    def get_translator(self, max_world_version: Tuple[str, Union[int, Tuple[int, int, int]]], data: Any = None) -> \
    Tuple["Translator", Union[int, Tuple[int, int, int]]]:
        pass

    @staticmethod
    def is_valid(key: Tuple) -> bool:
        return True

schematic_interface = SchematicInterface()

class SchematicFormatWrapper(FormatWraper):
    def __init__(self, path):
        super(SchematicFormatWrapper, self).__init__(path)
        assert os.path.isfile(path)
        self._open = False
        self._platform = 'java'
        self._version = (1, 12, 2)
        self._selection = SelectionGroup()

    def readable(self) -> bool:
        return True

    def writeable(self) -> bool:
        return False

    @staticmethod
    def is_valid(path: str) -> bool:
        return os.path.isfile(path) and path.endswith(".schematic")

    @property
    def platform(self) -> str:
        """Platform string ("bedrock" / "java" / ...)"""
        return self._platform

    @platform.setter
    def platform(self, platform: str):
        if self._open:
            log.error(
                "Construction platform cannot be changed after the object has been opened."
            )
            return
        self._platform = platform

    @property
    def version(self) -> Tuple[int, int, int]:
        return self._version

    @version.setter
    def version(self, version: Tuple[int, int, int]):
        if self._open:
            log.error(
                "Construction version cannot be changed after the object has been opened."
            )
            return
        self._version = version

    @property
    def selection(self) -> SelectionGroup:
        return self._selection

    @selection.setter
    def selection(self, selection: SelectionGroup):
        if self._open:
            log.error(
                "Construction selection cannot be changed after the object has been opened."
            )
            return
        self._selection = selection

    def _get_interface(self, max_world_version, raw_chunk_data=None) -> "SchematicInterface":
        return schematic_interface

    def _get_interface_and_translator(
        self, max_world_version, raw_chunk_data=None
    ) -> Tuple["Interface", "Translator", "VersionNumberAny"]:
        interface = self._get_interface(max_world_version, raw_chunk_data)
        translator, version_identifier = interface.get_translator(
            max_world_version, raw_chunk_data, self.translation_manager
        )
        return interface, translator, version_identifier

    def open(self):
        if self._open:
            return

        assert os.path.isfile(self.path), "File specified does not exist."


        self._open = True

    def has_lock(self) -> bool:
        return True
    


def show_ui(parent, world, options: dict) -> dict:
    dialog = SimpleDialog(parent, "Import Schematic")
    file_picker = wx.FilePickerCtrl(
        dialog,
        path=options.get("path", ""),
        wildcard="Schematic file (*.schematic)|*.schematic",
        style=wx.FLP_USE_TEXTCTRL | wx.FLP_OPEN,
    )

    version_selector = VersionSelect(dialog, world.translation_manager)

    dialog.sizer.Add(file_picker, 0, wx.ALL, 5)
    dialog.sizer.Add(version_selector, 0, wx.ALL, 5)
    dialog.Fit()

    if dialog.ShowModal() == wx.ID_OK:
        options = {
            "path": file_picker.GetPath(),
            "platform": version_selector.platform,
            "version": version_selector.version
        }
    return options


def import_schematic(world: World, dimension, options) -> Structure:
    path = options.get("path", None)
    if isinstance(path, str) and path.endswith(".schematic") and os.path.isfile(path):
        translator = world.translation_manager.get_version(
            world.world_wrapper.platform, (1, 12, 2)
        )

        root = nbt.load(path)
        length, width, height = (
            root["Length"].value,
            root["Width"].value,
            root["Height"].value,
        )

        materials = root.get("Materials", nbt.TAG_String("alpha")).value
        block_ids = root.get("Blocks", nbt.TAG_Byte_Array()).value
        block_data = root.get("Data", nbt.TAG_Byte_Array()).value

        block_ids = block_ids.astype("uint16").reshape(height, length, width)
        block_data = block_data.reshape(height, length, width)

        if "AddBlocks" in root:
            size = height * length * width
            add = np.zeros(size + (size & 1), dtype="uint16")
            add[::2] = np.resize(root["AddBlocks"].value, add[::2].shape)
            add[1::2] = add[::2] & 0xF
            add[::2] >>= 4
            add <<= 8
            block_ids |= add[:size].reshape(height, length, width)

        entities = root.get("Entities", nbt.TAG_List()).value
        tile_entities = root.get("TileEntities", nbt.TAG_List()).value

        blocks = np.zeros((height, length, width), dtype=int)
        unique_ids = np.unique(block_ids)

        palette = BlockManager()

        for unique_id in unique_ids:
            block_position_mask = block_ids == unique_id
            corresponding_data_values = block_data & block_position_mask
            unique_data_values = np.unique(corresponding_data_values)
            for dv in unique_data_values:
                dv_position_mask = np.ma.getmask(np.ma.masked_where(block_data == dv, block_position_mask))
                index = palette.get_add_block(translator.ints_to_block(unique_id, dv))
                blocks[~dv_position_mask] = index

    return None


export = {
    "v": 1,
    "name": "Import Schematic",
    "features": ["src_selection", "wxoptions", "dst_location_absolute"],
    "structure_callable_inputs": ["options"],
    "structure_callable": import_schematic,
    "inputs": ["structure", "options"],
    "operation": paste,
    "wxoptions": show_ui,
}
