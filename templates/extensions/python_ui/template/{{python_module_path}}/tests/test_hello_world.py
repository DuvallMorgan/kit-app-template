# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add
#   suport for async/await tests
#   For most things refer to unittest docs:
#   https://docs.python.org/3/library/unittest.html
import omni.kit.test
import omni.kit.app
import omni.usd
from pxr import UsdGeom

# Extension for writing UI tests (to simulate UI interaction)
import omni.kit.ui_test as ui_test

# Import extension python module we are testing with absolute import path,
# as if we are external user (other extension)
import {{ python_module }}


# Having a test class dervived from omni.kit.test.AsyncTestCase declared on the
# root of module will make it auto-discoverable by omni.kit.test
class Test(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        pass

    # After running each test
    async def tearDown(self):
        pass

    # Actual test, notice it is an "async" function, so "await" can be used if needed
    async def test_hello_public_function(self):
        result = {{ python_module }}.some_public_function(4)
        self.assertEqual(result, 256)

    async def test_window_button(self):
        create_button = ui_test.find(
            "{{ extension_display_name }}//Frame/**/Button[*].text=='Create primitive'"
        )
        self.assertIsNotNone(create_button)
        grid_button = ui_test.find(
            "{{ extension_display_name }}//Frame/**/Button[*].text=='Build clean-energy grid'"
        )
        self.assertIsNotNone(grid_button)
        fab_button = ui_test.find(
            "{{ extension_display_name }}//Frame/**/Button[*].text=='Build nanoprint fab'"
        )
        self.assertIsNotNone(fab_button)

    async def test_builders_create_valid_usd(self):
        context = omni.usd.get_context()
        result, error = await context.new_stage_async()
        self.assertTrue(result, error)
        await omni.kit.app.get_app().next_update_async()

        grid_button = ui_test.find(
            "{{ extension_display_name }}//Frame/**/Button[*].text=='Build clean-energy grid'"
        )
        await grid_button.click()
        await omni.kit.app.get_app().next_update_async()

        stage = context.get_stage()
        grid = stage.GetPrimAtPath("/World/CleanEnergyGrid1")
        self.assertTrue(grid.IsValid())
        solar = stage.GetPrimAtPath("/World/CleanEnergyGrid1/SolarPlant")
        self.assertTrue(solar.IsValid())
        self.assertEqual(
            solar.GetAttribute("cleanEnergy:nodeType").Get(), "SolarPlant"
        )
        line = stage.GetPrimAtPath("/World/CleanEnergyGrid1/Line_H_0_0")
        self.assertTrue(UsdGeom.BasisCurves(line).GetPrim().IsValid())

        fab_button = ui_test.find(
            "{{ extension_display_name }}//Frame/**/Button[*].text=='Build nanoprint fab'"
        )
        await fab_button.click()
        await omni.kit.app.get_app().next_update_async()

        fab = stage.GetPrimAtPath("/World/NanoPrintFab1")
        self.assertTrue(fab.IsValid())
        printer = stage.GetPrimAtPath("/World/NanoPrintFab1/NanoPrinter_01")
        self.assertTrue(printer.IsValid())
        self.assertEqual(
            printer.GetAttribute("fab:process").Get(), "3DNanoPrint"
        )
        self.assertTrue(
            printer.GetAttribute("fab:cleanEnergyRequired").Get()
        )
