from .base_operation import BaseSelectOperationUI
from amulet_map_editor.programs.edit import plugins


class SelectOperationUI(BaseSelectOperationUI):
    @property
    def _operations(self) -> plugins.OperationStorageType:
        return plugins.operations
