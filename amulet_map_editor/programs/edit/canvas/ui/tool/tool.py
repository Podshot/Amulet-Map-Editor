import wx
from typing import TYPE_CHECKING, Type, Dict, Optional

from amulet_map_editor.programs.edit.canvas.ui import BaseUI
from amulet_map_editor.programs.edit.canvas.ui.tool.tools.base_tool_ui import BaseToolUI, BaseToolUIType
from amulet_map_editor.programs.edit.canvas.events import (
    ToolChangeEvent,
    EVT_TOOL_CHANGE
)

from .tools.select import SelectOptions
from .tools.operation import SelectOperationUI
from .tools.import_tool import SelectImportOperationUI
from .tools.export_tool import SelectExportOperationUI

if TYPE_CHECKING:
    from ...edit_canvas import EditCanvas


class Tool(wx.BoxSizer, BaseUI):
    def __init__(self, canvas: "EditCanvas"):
        wx.BoxSizer.__init__(self, wx.VERTICAL)
        BaseUI.__init__(self, canvas)

        self._tools: Dict[str, BaseToolUIType] = {}
        self._active_tool: Optional[BaseToolUIType] = None

        self._tool_option_sizer = wx.BoxSizer(wx.VERTICAL)
        self.Add(self._tool_option_sizer, 1, wx.EXPAND, 0)

        tool_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        tool_select_sizer.AddStretchSpacer(1)
        self._tool_select = ToolSelect(canvas)
        tool_select_sizer.Add(self._tool_select, 0, wx.EXPAND, 0)
        tool_select_sizer.AddStretchSpacer(1)
        self.Add(tool_select_sizer, 0, wx.EXPAND, 0)

        self.canvas.Bind(EVT_TOOL_CHANGE, lambda evt: self._enable_tool(evt.tool))

        self.register_tool("Select", SelectOptions)
        self._enable_tool("Select")
        self.register_tool("Operation", SelectOperationUI)
        self.register_tool("Import", SelectImportOperationUI)
        self.register_tool("Export", SelectExportOperationUI)

    def bind_events(self):
        for tool in self._tools.values():
            tool.bind_events()

    def register_tool(self, name: str, tool_cls: Type[BaseToolUIType]):
        assert issubclass(tool_cls, (wx.Window, wx.Sizer)) and issubclass(tool_cls, BaseToolUI)
        self._tool_select.register_tool(name)
        tool = tool_cls(self.canvas)
        if isinstance(tool, wx.Window):
            tool.Hide()
        elif isinstance(tool, wx.Sizer):
            tool.ShowItems(show=False)
        self._tools[name] = tool
        self._tool_option_sizer.Add(tool, 1, wx.EXPAND, 0)

    def _enable_tool(self, tool: str):
        if tool in self._tools:
            if self._active_tool is not None:
                self._active_tool.disable()
                if isinstance(self._active_tool, wx.Window):
                    self._active_tool.Hide()
                elif isinstance(self._active_tool, wx.Sizer):
                    self._active_tool.ShowItems(show=False)
            self._active_tool = self._tools[tool]
            if isinstance(self._active_tool, wx.Window):
                self._active_tool.Show()
            elif isinstance(self._active_tool, wx.Sizer):
                self._active_tool.ShowItems(show=True)
            self._active_tool.enable()
            self.canvas.Layout()


class ToolSelect(wx.Panel, BaseUI):
    def __init__(self, canvas: "EditCanvas"):
        wx.Panel.__init__(self, canvas)
        BaseUI.__init__(self, canvas)

        self._sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self._sizer)

    def register_tool(self, name: str):
        button = wx.Button(self, label=name)
        self._sizer.Add(button)
        self._sizer.Fit(self)
        self.Layout()
        button.Bind(wx.EVT_BUTTON, lambda evt: wx.PostEvent(self.canvas, ToolChangeEvent(tool=name)))
