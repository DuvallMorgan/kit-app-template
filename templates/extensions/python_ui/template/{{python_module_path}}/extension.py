# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ext
import omni.kit.commands
import omni.ui as ui
import omni.usd
from pxr import Gf, Sdf, UsdGeom


# Functions and vars are available to other extensions as usual in python:
# `{{python_module}}.some_public_function(x)`
def some_public_function(x: int):
    """This is a public function that can be called from other extensions."""
    print(f"[{{ extension_name }}] some_public_function was called with {x}")
    return x ** x


# Any class derived from `omni.ext.IExt` in the top level module (defined in
# `python.modules` of `extension.toml`) will be instantiated when the extension
# gets enabled, and `on_startup(ext_id)` will be called. Later when the
# extension gets disabled on_shutdown() is called.
class MyExtension(omni.ext.IExt):
    """A small USD scene builder for the Python UI extension template."""
    # ext_id is the current extension id. It can be used with the extension
    # manager to query additional information, like where this extension is
    # located on the filesystem.
    def on_startup(self, _ext_id):
        """This is called every time the extension is activated."""
        print("[{{ extension_name }}] Extension startup")

        self._window = None
        self._prim_count = 0
        self._grid_count = 0
        self._fab_count = 0
        self._selected_path = None
        self._window = ui.Window("{{ extension_display_name }}", width=360, height=460)
        with self._window.frame:
            with ui.VStack():
                ui.Label("Create a USD primitive", height=24)
                self._status = ui.Label("No primitive selected")
                self._type = ui.ComboBox(0, "Cube", "Sphere", "Cylinder", "Cone")
                ui.Button("Create primitive", clicked_fn=self._create_prim)
                ui.Label("Transform", height=24)
                with ui.HStack():
                    ui.Label("Position", width=70)
                    self._position = [ui.FloatField(tooltip=axis) for axis in "XYZ"]
                with ui.HStack():
                    ui.Label("Scale", width=70)
                    self._scale = [ui.FloatField(1.0, tooltip=axis) for axis in "XYZ"]
                for field in self._position + self._scale:
                    field.model.add_value_changed_fn(self._update_transform)
                ui.Separator(height=8)
                ui.Label("100% clean-energy grid", height=24)
                with ui.HStack():
                    ui.Label("Grid size", width=70)
                    self._grid_size = ui.IntField(3, min=1, max=20)
                with ui.HStack():
                    ui.Label("Spacing", width=70)
                    self._grid_spacing = ui.FloatField(20.0, min=1.0)
                self._solar = ui.CheckBox(True)
                ui.Label("Solar generation", height=20)
                self._wind = ui.CheckBox(True)
                ui.Label("Wind generation", height=20)
                self._storage = ui.CheckBox(True)
                ui.Label("Battery storage", height=20)
                ui.Button("Build clean-energy grid", clicked_fn=self._build_grid)
                ui.Separator(height=8)
                ui.Label("3D nanoprint fab", height=24)
                with ui.HStack():
                    ui.Label("Printer bays", width=90)
                    self._printer_count = ui.IntField(8, min=1, max=64)
                ui.Button("Build nanoprint fab", clicked_fn=self._build_fab)
                ui.Separator(height=8)
                ui.Label("World city generator", height=24)
                with ui.HStack():
                    ui.Label("City blocks", width=90)
                    self._city_size = ui.IntField(4, min=1, max=20)
                with ui.HStack():
                    ui.Label("Block spacing", width=90)
                    self._city_spacing = ui.FloatField(35.0, min=5.0)
                ui.Button("Build 3D city", clicked_fn=self._build_city)

    def _create_prim(self):
        """Create a primitive on the current USD stage and select it."""
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._status.text = "Open or create a USD stage first"
            return
        try:
            self._ensure_world(stage)
            prim_type = ("Cube", "Sphere", "Cylinder", "Cone")[
                self._type.model.get_item_value_model().as_int
            ]
            path = self._unique_path(stage, "/World", prim_type)
            self._create_prim_checked(stage, path, prim_type)
        except RuntimeError as error:
            self._status.text = str(error)
            return

        self._selected_path = path
        omni.usd.get_context().get_selection().set_selected_prim_paths([path], True)
        self._status.text = f"Selected: {path}"
        self._set_vector_fields(Gf.Vec3f(0, 0, 0), Gf.Vec3f(1, 1, 1))

    def _ensure_world(self, stage):
        world = stage.GetPrimAtPath("/World")
        if not world.IsValid():
            self._create_prim_checked(stage, "/World", "Xform")

    def _unique_path(self, stage, parent_path, type_name):
        index = 1
        while True:
            path = f"{parent_path}/{type_name}{index}"
            if not stage.GetPrimAtPath(path).IsValid():
                return path
            index += 1

    def _create_prim_checked(self, stage, path, prim_type):
        result = omni.kit.commands.execute(
            "CreatePrim",
            prim_path=path,
            prim_type=prim_type,
            select_new_prim=False,
        )
        prim = stage.GetPrimAtPath(path)
        if result is False or not prim.IsValid():
            raise RuntimeError(f"Could not create USD prim: {path}")
        return prim

    def _build_grid(self):
        """Create a parameterized renewable generation and storage grid."""
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._status.text = "Open or create a USD stage first"
            return

        try:
            self._ensure_world(stage)
            size = max(1, min(20, self._grid_size.model.as_int))
            spacing = max(1.0, self._grid_spacing.model.as_float)
            root_path = self._unique_path(stage, "/World", "CleanEnergyGrid")
            self._create_prim_checked(stage, root_path, "Xform")

            node_paths = {}
            for row in range(size):
                for column in range(size):
                    path = f"{root_path}/Substation_{row}_{column}"
                    position = Gf.Vec3d(column * spacing, 0, row * spacing)
                    self._create_grid_node(stage, path, position, "Substation")
                    node_paths[(row, column)] = (path, position)

            for row in range(size):
                for column in range(size):
                    if column + 1 < size:
                        self._create_connection(
                            stage,
                            f"{root_path}/Line_H_{row}_{column}",
                            node_paths[(row, column)][1],
                            node_paths[(row, column + 1)][1],
                        )
                    if row + 1 < size:
                        self._create_connection(
                            stage,
                            f"{root_path}/Line_V_{row}_{column}",
                            node_paths[(row, column)][1],
                            node_paths[(row + 1, column)][1],
                        )

            center = (size - 1) * spacing / 2.0
            if self._solar.model.as_bool:
                self._create_grid_node(
                    stage, f"{root_path}/SolarPlant", Gf.Vec3d(-spacing, 0, center), "SolarPlant"
                )
            if self._wind.model.as_bool:
                self._create_grid_node(
                    stage,
                    f"{root_path}/WindFarm",
                    Gf.Vec3d(center, 0, (size - 1) * spacing + spacing),
                    "WindFarm",
                )
            if self._storage.model.as_bool:
                self._create_grid_node(
                    stage,
                    f"{root_path}/BatteryStorage",
                    Gf.Vec3d(size * spacing, 0, center),
                    "BatteryStorage",
                )
        except RuntimeError as error:
            self._status.text = str(error)
            return

        omni.usd.get_context().get_selection().set_selected_prim_paths(
            [root_path], True
        )
        self._status.text = f"Built {size}x{size} clean-energy grid"

    def _build_fab(self):
        """Create a conceptual 3D nanoprint fab station in USD."""
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._status.text = "Open or create a USD stage first"
            return

        try:
            self._ensure_world(stage)
            printer_count = max(1, min(64, self._printer_count.model.as_int))
            root_path = self._unique_path(stage, "/World", "NanoPrintFab")
            self._create_prim_checked(stage, root_path, "Xform")
            self._create_fab_node(
                stage, f"{root_path}/Cleanroom", Gf.Vec3d(0, 0, 0), "Cleanroom"
            )
            self._create_fab_node(
                stage,
                f"{root_path}/MaterialStation",
                Gf.Vec3d(-12, 0, 0),
                "MaterialStation",
            )
            self._create_fab_node(
                stage, f"{root_path}/Inspection", Gf.Vec3d(12, 0, 0), "Inspection"
            )
            for index in range(printer_count):
                row, column = divmod(index, 8)
                self._create_fab_node(
                    stage,
                    f"{root_path}/NanoPrinter_{index + 1:02d}",
                    Gf.Vec3d((column - 3.5) * 3.0, 0, (row + 1) * 3.0),
                    "NanoPrinter",
                )
        except RuntimeError as error:
            self._status.text = str(error)
            return

        omni.usd.get_context().get_selection().set_selected_prim_paths(
            [root_path], True
        )
        self._status.text = f"Built 3D nanoprint fab with {printer_count} printer bays"

    def _build_city(self):
        """Create a procedural city block layout for world-scale planning."""
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._status.text = "Open or create a USD stage first"
            return

        try:
            self._ensure_world(stage)
            size = max(1, min(20, self._city_size.model.as_int))
            spacing = max(5.0, self._city_spacing.model.as_float)
            root_path = self._unique_path(stage, "/World", "WorldCity")
            self._create_prim_checked(stage, root_path, "Xform")
            for row in range(size):
                for column in range(size):
                    x = column * spacing
                    z = row * spacing
                    block_path = f"{root_path}/Block_{row}_{column}"
                    self._create_prim_checked(stage, block_path, "Xform")
                    self._create_city_building(
                        stage,
                        f"{block_path}/Housing",
                        Gf.Vec3d(x - 8, 6, z + 8),
                        Gf.Vec3f(8, 12, 8),
                        "Housing",
                    )
                    self._create_city_building(
                        stage,
                        f"{block_path}/Hotel",
                        Gf.Vec3d(x + 8, 10, z + 8),
                        Gf.Vec3f(8, 20, 8),
                        "Hotel",
                    )
                    self._create_city_building(
                        stage,
                        f"{block_path}/DataCenter",
                        Gf.Vec3d(x, 5, z - 8),
                        Gf.Vec3f(14, 10, 8),
                        "DataCenter",
                    )
                    self._create_connection(
                        stage,
                        f"{root_path}/Road_Row_{row}_{column}",
                        Gf.Vec3d(x - spacing / 2, 0, z - spacing / 2),
                        Gf.Vec3d(x + spacing / 2, 0, z - spacing / 2),
                    )
                    self._create_connection(
                        stage,
                        f"{root_path}/Road_Column_{row}_{column}",
                        Gf.Vec3d(x - spacing / 2, 0, z - spacing / 2),
                        Gf.Vec3d(x - spacing / 2, 0, z + spacing / 2),
                    )

            center = (size - 1) * spacing / 2.0
            self._create_city_building(
                stage,
                f"{root_path}/UtilityHub",
                Gf.Vec3d(center, 4, -spacing),
                Gf.Vec3f(12, 8, 12),
                "UtilityHub",
            )
        except RuntimeError as error:
            self._status.text = str(error)
            return

        omni.usd.get_context().get_selection().set_selected_prim_paths(
            [root_path], True
        )
        self._status.text = f"Built {size}x{size} world city"

    def _create_city_building(self, stage, path, position, scale, building_type):
        prim = self._create_prim_checked(stage, path, "Cube")
        prim.CreateAttribute("city:buildingType", Sdf.ValueTypeNames.Token).Set(
            building_type
        )
        prim.CreateAttribute("city:cleanEnergyRequired", Sdf.ValueTypeNames.Bool).Set(
            True
        )
        xformable = UsdGeom.Xformable(prim)
        xformable.AddTranslateOp().Set(position)
        xformable.AddScaleOp().Set(scale)

    def _create_fab_node(self, stage, path, position, node_type):
        prim = self._create_prim_checked(stage, path, "Xform")
        prim.CreateAttribute("fab:process", Sdf.ValueTypeNames.Token).Set("3DNanoPrint")
        prim.CreateAttribute("fab:stationType", Sdf.ValueTypeNames.Token).Set(node_type)
        prim.CreateAttribute("fab:cleanEnergyRequired", Sdf.ValueTypeNames.Bool).Set(True)
        prim.CreateAttribute("fab:status", Sdf.ValueTypeNames.Token).Set("Planned")
        UsdGeom.Xformable(prim).AddTranslateOp().Set(position)

    def _create_grid_node(self, stage, path, position, node_type):
        prim = self._create_prim_checked(stage, path, "Xform")
        prim.CreateAttribute("cleanEnergy:nodeType", Sdf.ValueTypeNames.Token).Set(node_type)
        prim.CreateAttribute("cleanEnergy:renewable", Sdf.ValueTypeNames.Bool).Set(
            node_type in {"SolarPlant", "WindFarm"}
        )
        xformable = UsdGeom.Xformable(prim)
        xformable.AddTranslateOp().Set(position)

    def _create_connection(self, stage, path, start, end):
        curves = UsdGeom.BasisCurves.Define(stage, path)
        curves.CreateCurveVertexCountsAttr([2])
        curves.CreatePointsAttr([start, end])
        curves.CreateTypeAttr(UsdGeom.Tokens.linear)
        curves.CreateWidthsAttr([0.15])

    def _set_vector_fields(self, position, scale):
        for field, value in zip(self._position, position):
            field.model.set_value(float(value))
        for field, value in zip(self._scale, scale):
            field.model.set_value(float(value))

    def _update_transform(self, _model):
        if not self._selected_path:
            return
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(self._selected_path) if stage else None
        if not prim or not prim.IsValid():
            return
        position = Gf.Vec3d(
            *(field.model.as_float for field in self._position)
        )
        scale = Gf.Vec3d(*(field.model.as_float for field in self._scale))
        xformable = UsdGeom.Xformable(prim)
        ops = xformable.GetOrderedXformOps()
        translate_op = next(
            (op for op in ops if op.GetOpType() == UsdGeom.XformOp.TypeTranslate), None
        )
        scale_op = next(
            (op for op in ops if op.GetOpType() == UsdGeom.XformOp.TypeScale), None
        )
        if translate_op is None:
            translate_op = xformable.AddTranslateOp()
        if scale_op is None:
            scale_op = xformable.AddScaleOp()
        translate_op.Set(position)
        scale_op.Set(scale)

    def on_shutdown(self):
        """This is called every time the extension is deactivated. It is used
        to clean up the extension state."""
        if self._window:
            self._window.destroy()
            self._window = None
        print("[{{ extension_name }}] Extension shutdown")
