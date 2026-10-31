# SPDX-FileCopyrightText: 2025-2026 The French Monkey
# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "Curve",
    "author": "The French Monkey",
    "version": (1, 2, 5),
    "blender": (4, 2, 0),
    "location": "Sidebar > Curve Generator (Shader, Geometry, Compositor, Texture Node Editors)",
    "description": "Generate float curves",
    "category": "Node",
    "license": "GPL-3.0-or-later",
}

import bpy
import random
import math
import re
import os
import json
import shutil

try:
    from . import relay_updater
except ImportError:  # the Addon Collection has its own updates
    relay_updater = None

PRESET_NAME = "curve_generator_presets.json"
OLD_PRESET_FILE = os.path.join(os.path.expanduser("~"), PRESET_NAME)  # where presets lived before 1.2.5

# ------------------------------
# Preset Curves
# ------------------------------

EASING_PRESETS = {
    "linear": [0.0, 1.0],
    "ease": [0.25, 0.1, 0.25, 1.0],
    "ease-in": [0.42, 0.0, 1.0, 1.0],
    "ease-out": [0.0, 0.0, 0.58, 1.0],
    "ease-in-out": [0.42, 0.0, 0.58, 1.0],

    # Sine
    "ease-in-sine": [0.12, 0.0, 0.39, 0.0],
    "ease-out-sine": [0.61, 1.0, 0.88, 1.0],
    "ease-in-out-sine": [0.37, 0.0, 0.63, 1.0],

    # Quad
    "ease-in-quad": [0.11, 0.0, 0.5, 0.0],
    "ease-out-quad": [0.5, 1.0, 0.89, 1.0],
    "ease-in-out-quad": [0.45, 0.0, 0.55, 1.0],

    # Cubic
    "ease-in-cubic": [0.32, 0.0, 0.67, 0.0],
    "ease-out-cubic": [0.33, 1.0, 0.68, 1.0],
    "ease-in-out-cubic": [0.65, 0.0, 0.35, 1.0],

    # Quart
    "ease-in-quart": [0.5, 0.0, 0.75, 0.0],
    "ease-out-quart": [0.25, 1.0, 0.5, 1.0],
    "ease-in-out-quart": [0.76, 0.0, 0.24, 1.0],

    # Quint
    "ease-in-quint": [0.64, 0.0, 0.78, 0.0],
    "ease-out-quint": [0.22, 1.0, 0.36, 1.0],
    "ease-in-out-quint": [0.83, 0.0, 0.17, 1.0],

    # Expo
    "ease-in-expo": [0.7, 0.0, 0.84, 0.0],
    "ease-out-expo": [0.16, 1.0, 0.3, 1.0],
    "ease-in-out-expo": [0.87, 0.0, 0.13, 1.0],

    # Circ
    "ease-in-circ": [0.55, 0.0, 1.0, 0.45],
    "ease-out-circ": [0.0, 0.55, 0.45, 1.0],
    "ease-in-out-circ": [0.85, 0.0, 0.15, 1.0],

    # Back
    "ease-in-back": [0.36, 0.0, 0.66, -0.56],
    "ease-out-back": [0.34, 1.56, 0.64, 1.0],
    "ease-in-out-back": [0.68, -0.6, 0.32, 1.6],

    # Elastic
    "ease-out-elastic": [
        0, -0.0003, -0.0012, -0.0014, -0.0005, 0.001, 0.0022, 0.0021, 0.0003,
        -0.0023, -0.0039, -0.003, 0.0005, 0.0048, 0.0067, 0.0039, -0.0028,
        -0.0094, -0.0108, -0.0042, 0.0078, 0.0176, 0.0167, 0.0025, -0.0182,
        -0.0312, -0.024, 0.0043, 0.0383, 0.0532, 0.0313, -0.0222, -0.0753,
        -0.0865, -0.0336, 0.0625, 0.1404, 0.1334, 0.0198, -0.1456, -0.25,
        -0.1922, 0.0345, 0.3066, 0.4258, 0.25, -0.1775, -0.6027, -0.6923,
        -0.269, 0.5, 1.269, 1.6923, 1.6027, 1.1775, 0.75, 0.5742, 0.6934,
        0.9655, 1.1922, 1.25, 1.1456, 0.9802, 0.8666, 0.8596, 0.9375,
        1.0336, 1.0865, 1.0753, 1.0222, 0.9688, 0.9468, 0.9617, 0.9957,
        1.024, 1.0313, 1.0182, 0.9975, 0.9833, 0.9824, 0.9922, 1.0042,
        1.0108, 1.0094, 1.0028, 0.9961, 0.9933, 0.9952, 0.9995, 1.003,
        1.0039, 1.0023, 0.9997, 0.9979, 0.9978, 0.999, 1.0005, 1.0014,
        1.0012, 1.0003, 1],

    # Bounce
    "ease-out-bounce": [
        0.0, 0.3, 0.55, 0.7, 0.85, 0.95, 1.0, 0.97, 1.0, 0.99, 1.0, 1.0]
}

# ------------------------------
# Utilities
# ------------------------------

def parse_css_easing(css_input):
    if isinstance(css_input, list):
        return css_input
    if not isinstance(css_input, str):
        return None
    css_string = css_input.strip().lower()
    if css_string.startswith("cubic-bezier("):
        match = re.match(
            r"cubic-bezier\(([-+]?\d*\.?\d+),\s*([-+]?\d*\.?\d+),\s*([-+]?\d*\.?\d+),\s*([-+]?\d*\.?\d+)\)",
            css_string
        )
        if match:
            return [float(match.group(i)) for i in range(1, 5)]
        return None
    if css_string.startswith("linear("):
        numbers = re.findall(r"[-+]?\d*\.?\d+", css_string)
        values = [float(n) for n in numbers]
        return values if len(values) >= 2 else None
    return EASING_PRESETS.get(css_string, None)

def make_positions(num, randomize=False):
    if num <= 1:
        return [0.0]
    if randomize:
        return sorted(random.random() for _ in range(num))
    return [i / (num - 1) for i in range(num)]

def random_curve(num_points, min_val, max_val):
    return [random.uniform(min_val, max_val) for _ in range(num_points)]

# ------------------------------
# Curve Generators
# ------------------------------

def generate_spring_curve(bounce, strength, invert_vert=False, invert_horiz=False):
    values = []
    num_points = bounce * 2 + 1
    for i in range(num_points):
        sign = -1 if i % 2 == 0 else 1
        y = sign * (strength ** i)
        if invert_vert:
            y *= -1
        values.append(y)
    x_positions = make_positions(len(values))
    if invert_horiz:
        x_positions = [1 - x for x in x_positions]
    return x_positions, values

def generate_elastic_curve(bounce, strength, invert_vert=False, invert_horiz=False):
    values = []
    x_positions = []
    amp = (strength * 2.0) ** 1.2
    num_points = bounce * 10 + 2
    for i in range(num_points):
        t = i / (num_points - 1)
        if t == 0:
            y = 0.0
        elif t == 1:
            y = 1.0
        else:
            p = 1.0 / bounce
            s = p / 4
            if t < 0.5:
                t2 = t * 2
                y = -0.5 * (2 ** (10 * (t2 - 1)) *
                            math.sin((t2 - 1 - s) * (2 * math.pi) / p)) * amp
            else:
                t2 = t * 2 - 1
                y = (2 ** (-10 * t2) *
                     math.sin((t2 - s) * (2 * math.pi) / p)) * amp * 0.5 + 1
        values.append(y)
        x_positions.append(t)
    mid_left = num_points // 2 - 1
    mid_right = num_points // 2
    values[mid_left] -= strength
    values[mid_right] += strength
    if invert_vert:
        values = [1 - v for v in values]
    if invert_horiz:
        x_positions = [1 - x for x in x_positions]
    return x_positions, values

def generate_bounce_curve(bounces=5, invert_vert=False):
    num_points = bounces * 10 + 10
    values = []
    for i in range(num_points):
        t = i / (num_points - 1)
        y = abs(math.sin(t * bounces * math.pi) * (1 - t) ** 2)
        values.append(y)
    if invert_vert:
        values = values[::-1]
    x_positions = make_positions(num_points)
    return x_positions, values

def generate_stairs_curve(steps=10, invert_horiz=False):
    values = []
    x_positions = []
    for i in range(steps):
        step_height = i / steps
        start_x = i / steps
        end_x = (i + 1) / steps
        x_positions.append(start_x)
        values.append(step_height)
        x_positions.append(end_x - 1e-6)
        values.append(step_height)
    x_positions.append(1.0)
    values.append(1.0)
    if invert_horiz:
        x_positions = [1 - x for x in x_positions]
    return x_positions, values

def generate_peaks_curve(peaks_count=2, peak_max=1.0, peaks_randomizer=0.0):
    values = []
    for i in range(peaks_count):
        if peaks_randomizer <= 0.0:
            p = peak_max
        else:
            min_factor = max(0.0, 1.0 - peaks_randomizer)
            p = peak_max * (min_factor + (peaks_randomizer * random.random()))
        values.append(0.0)
        values.append(0.0)
        values.append(p)
        values.append(p)

    values.append(0.0)
    values.append(0.0)
    x_positions = make_positions(len(values))
    return x_positions, values

# ------------------------------
# Save/Load preset helpers
# ------------------------------

def clean_presets(data):
    """Only well formed presets, so a hand edited file cannot break saving."""
    if not isinstance(data, list):
        return []
    return [p for p in data if isinstance(p, dict) and "name" in p]

def get_preset_file():
    """Blender's own folder. An older preset file is copied across once and left in place."""
    try:
        folder = bpy.utils.extension_path_user(__package__, create=True)
    except Exception:  # inside the Addon Collection
        folder = bpy.utils.user_resource('CONFIG', path="curve_generator", create=True)
    path = os.path.join(folder, PRESET_NAME)
    if not os.path.exists(path) and os.path.exists(OLD_PRESET_FILE):
        try:
            shutil.copyfile(OLD_PRESET_FILE, path)
        except OSError:
            pass
    return path

def save_curve_to_file(preset_dict):
    preset_file = get_preset_file()
    presets = []
    if os.path.exists(preset_file):
        try:
            with open(preset_file, "r") as f:
                presets = clean_presets(json.load(f))
        except Exception:
            presets = []
    # remove any existing with same name
    presets = [p for p in presets if p.get('name') != preset_dict.get('name')]
    presets.append(preset_dict)
    try:
        with open(preset_file, "w") as f:
            json.dump(presets, f, indent=4)
    except Exception:
        pass

def get_available_presets():
    preset_file = get_preset_file()
    if not os.path.exists(preset_file):
        return []
    try:
        with open(preset_file, "r") as f:
            presets = clean_presets(json.load(f))
            return [p.get('name', "") for p in presets if 'name' in p]
    except Exception:
        return []

def load_curve_from_file(name):
    preset_file = get_preset_file()
    if not os.path.exists(preset_file):
        return None
    try:
        with open(preset_file, "r") as f:
            presets = clean_presets(json.load(f))
    except Exception:
        return None
    for p in presets:
        if p.get('name') == name:
            return p
    return None

# ------------------------------
# Core generation function
# ------------------------------

def generate_curve_from_settings(context):
    s = context.scene.curve_gen_settings
    preset = s.curve_source

    if preset == 'RANDOM':
        values = random_curve(s.num_points_random, s.min_val_random, s.max_val_random)
        x_positions = make_positions(s.num_points_random, s.random_position)
    elif preset == 'SPRING':
        x_positions, values = generate_spring_curve(s.bounce, s.strength, s.invert_vert, s.invert_horiz)
    elif preset == 'ELASTIC':
        x_positions, values = generate_elastic_curve(s.elastic_bounce, s.elastic_strength, False, s.elastic_invert_horiz)
    elif preset == 'BOUNCE':
        x_positions, values = generate_bounce_curve(s.bounce_amount, s.bounce_invert_vert)
    elif preset == 'STAIRS':
        x_positions, values = generate_stairs_curve(s.steps_count, s.stairs_invert_horiz)
    elif preset == 'CUSTOM':
        values = parse_css_easing(s.css_string)
        if not values or len(values) < 2:
            return {'CANCELLED'}
        x_positions = make_positions(len(values))
        if s.css_invert_horiz:
            x_positions = [1 - x for x in x_positions]
    elif preset == 'PRESET':
        values = parse_css_easing(EASING_PRESETS.get(s.preset_name))
        if not values or len(values) < 2:
            return {'CANCELLED'}
        x_positions = make_positions(len(values))
    elif preset == 'PEAKS':
        x_positions, values = generate_peaks_curve(s.peaks_count, s.peaks_max_value, s.peaks_randomizer)
    elif preset == 'SAVELOAD':
        return {'CANCELLED'}
    else:
        return {'CANCELLED'}
    if values:
        min_val, max_val = min(values), max(values)
    else:
        min_val, max_val = 0.0, 1.0

    tree = active_tree(context)
    if not tree:
        return {'CANCELLED'}
    selected_nodes = [n for n in tree.nodes if n.select and n.bl_idname == 'ShaderNodeFloatCurve']
    if not selected_nodes:
        return {'CANCELLED'}
    curve_node = selected_nodes[0]
    mapping = curve_node.mapping.curves[0]

    # adjust number of points
    while len(mapping.points) < len(values):
        # create a new point
        last = mapping.points[-1]
        mapping.points.new(last.location.x, last.location.y)
    while len(mapping.points) > len(values):
        mapping.points.remove(mapping.points[-1])

    # assign values and handles (use_vector_handles applies to all sources)
    for point, x, y in zip(mapping.points, x_positions, values):
        point.location.x = x
        point.location.y = y
        if s.use_vector_handles:
            # set to VECTOR where possible
            if hasattr(point, "handle_type"):
                try:
                    point.handle_type = 'VECTOR'
                except Exception:
                    pass
            else:
                if hasattr(point, "handle_left_type"):
                    try:
                        point.handle_left_type = 'VECTOR'
                    except Exception:
                        pass
                if hasattr(point, "handle_right_type"):
                    try:
                        point.handle_right_type = 'VECTOR'
                    except Exception:
                        pass
        else:
            # set to AUTO where possible
            if hasattr(point, "handle_type"):
                try:
                    point.handle_type = 'AUTO'
                except Exception:
                    pass
            else:
                if hasattr(point, "handle_left_type"):
                    try:
                        point.handle_left_type = 'AUTO'
                    except Exception:
                        pass
                if hasattr(point, "handle_right_type"):
                    try:
                        point.handle_right_type = 'AUTO'
                    except Exception:
                        pass

    curve_node.mapping.clip_min_y = min_val
    curve_node.mapping.clip_max_y = max_val
    curve_node.mapping.extend = 'HORIZONTAL'
    try:
        curve_node.mapping.update()
    except Exception:
        pass
    try:
        tree.update_tag()
    except Exception:
        pass
    return {'FINISHED'}

# ------------------------------
# Save/Load operators and menu
# ------------------------------

def active_tree(context):
    # edit_tree is the tree being edited, so a node inside a group is found too.
    space = context.space_data
    return getattr(space, "edit_tree", None) or getattr(space, "node_tree", None)

class CURVE_MT_presets_menu(bpy.types.Menu):
    bl_label = "Saved Curves"
    bl_idname = "CURVE_MT_presets_menu"
    def draw(self, context):
        layout = self.layout
        presets = get_available_presets()
        if not presets:
            layout.label(text="No curves saved")
        else:
            for p in presets:
                op = layout.operator("curve.select_preset", text=p)
                op.preset_name = p

class CURVE_OT_select_preset(bpy.types.Operator):
    bl_idname = "curve.select_preset"
    bl_label = "Select Saved Curve"
    preset_name: bpy.props.StringProperty()

    def execute(self, context):
        s = context.scene.curve_gen_settings
        s.SelectedCurve = self.preset_name

        # load saved curve data
        curve_data = load_curve_from_file(self.preset_name)
        if not curve_data:
            return {'CANCELLED'}

        # get first selected float curve node
        tree = active_tree(context)
        if not tree:
            return {'CANCELLED'}
        selected_nodes = [n for n in tree.nodes if n.select and n.bl_idname == 'ShaderNodeFloatCurve']
        if not selected_nodes:
            return {'CANCELLED'}
        curve_node = selected_nodes[0]
        mapping = curve_node.mapping.curves[0]

        points = curve_data.get('points', [])
        if not points:
            return {'CANCELLED'}

        x_positions = [p[0] for p in points]
        values = [p[1] for p in points]

        # adjust number of points
        while len(mapping.points) < len(values):
            last = mapping.points[-1]
            mapping.points.new(last.location.x, last.location.y)
        while len(mapping.points) > len(values):
            mapping.points.remove(mapping.points[-1])

        # assign points
        for point, x, y in zip(mapping.points, x_positions, values):
            point.location.x = x
            point.location.y = y
            # handles
            if s.use_vector_handles:
                if hasattr(point, "handle_type"):
                    try:
                        point.handle_type = 'VECTOR'
                    except Exception:
                        pass
                else:
                    if hasattr(point, "handle_left_type"):
                        try:
                            point.handle_left_type = 'VECTOR'
                        except Exception:
                            pass
                    if hasattr(point, "handle_right_type"):
                        try:
                            point.handle_right_type = 'VECTOR'
                        except Exception:
                            pass
            else:
                if hasattr(point, "handle_type"):
                    try:
                        point.handle_type = 'AUTO'
                    except Exception:
                        pass
                else:
                    if hasattr(point, "handle_left_type"):
                        try:
                            point.handle_left_type = 'AUTO'
                        except Exception:
                            pass
                    if hasattr(point, "handle_right_type"):
                        try:
                            point.handle_right_type = 'AUTO'
                        except Exception:
                            pass

        # update clip
        try:
            curve_node.mapping.clip_min_y = min(values) if values else 0.0
            curve_node.mapping.clip_max_y = max(values) if values else 1.0
        except Exception:
            pass

        # force update
        try:
            curve_node.mapping.update()
        except Exception:
            pass
        try:
            tree.update_tag()
        except Exception:
            pass

        # force redraw
        for area in context.screen.areas:
            if area.type == 'NODE_EDITOR':
                area.tag_redraw()

        return {'FINISHED'}

class CURVE_OT_save_preset(bpy.types.Operator):
    bl_idname = "curve.save_preset"
    bl_label = "Save Current Curve"
    preset_name: bpy.props.StringProperty(name="Preset Name")
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    def execute(self, context):
        # find selected float curve node
        tree = active_tree(context)
        if not tree:
            self.report({'WARNING'}, "No node tree found")
            return {'CANCELLED'}
        selected_nodes = [n for n in tree.nodes if n.select and n.bl_idname == 'ShaderNodeFloatCurve']
        if not selected_nodes:
            self.report({'WARNING'}, "Select a FloatCurve node to save")
            return {'CANCELLED'}
        curve_node = selected_nodes[0]
        mapping = curve_node.mapping.curves[0]
        points = []
        for p in mapping.points:
            points.append([float(p.location.x), float(p.location.y)])
        if not points:
            self.report({'WARNING'}, "No points to save")
            return {'CANCELLED'}
        save_curve_to_file({"name": self.preset_name, "points": points})
        self.report({'INFO'}, f"Curve '{self.preset_name}' saved.")
        return {'FINISHED'}

# ------------------------------
# Operator
# ------------------------------

class NODE_OT_GenerateCurve(bpy.types.Operator):
    bl_idname = "node.css_generate_curve"
    bl_label = "Generate Curve"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        tree = active_tree(context)
        if not tree:
            return False
        selected_nodes = [n for n in tree.nodes if n.select and n.bl_idname == 'ShaderNodeFloatCurve']
        return bool(selected_nodes)

    def execute(self, context):
        generate_curve_from_settings(context)
        return {'FINISHED'}

# ------------------------------
# UI
# ------------------------------

class NODE_PT_curve_generator(bpy.types.Panel):
    bl_label = "Curve"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Curve"

    def draw(self, context):
        if relay_updater:
            relay_updater.draw(self.layout)
        layout = self.layout
        s = context.scene.curve_gen_settings
        tree = active_tree(context)
        selected_nodes = [n for n in tree.nodes if n.select and n.bl_idname == 'ShaderNodeFloatCurve'] if tree else []

        layout.operator("node.css_generate_curve", icon='FCURVE')
        layout.prop(s, "curve_source", text="Curve Source")

        if s.curve_source != 'SAVELOAD':
            layout.prop(s, "auto_refresh", text="Auto Refresh")
            layout.prop(s, "use_vector_handles")

        if s.curve_source == 'CUSTOM':
            layout.prop(s, "css_string")
            layout.prop(s, "css_invert_horiz")
        elif s.curve_source == 'PRESET':
            layout.prop(s, "preset_name")
        elif s.curve_source == 'SPRING':
            layout.prop(s, "bounce", slider=True)
            layout.prop(s, "strength", slider=True)
            layout.prop(s, "invert_vert")
            layout.prop(s, "invert_horiz")
        elif s.curve_source == 'ELASTIC':
            layout.prop(s, "elastic_bounce", slider=True)
            layout.prop(s, "elastic_strength", slider=True)
            layout.prop(s, "elastic_invert_horiz")
        elif s.curve_source == 'BOUNCE':
            layout.prop(s, "bounce_amount", slider=True)
            layout.prop(s, "bounce_invert_vert")
        elif s.curve_source == 'STAIRS':
            layout.prop(s, "steps_count", slider=True)
            layout.prop(s, "stairs_invert_horiz")
        elif s.curve_source == 'PEAKS':
            layout.prop(s, "peaks_max_value", slider=True)
            layout.prop(s, "peaks_randomizer", slider=True)
            layout.prop(s, "peaks_count", slider=True)
        elif s.curve_source == 'RANDOM':
            layout.prop(s, "num_points_random", slider=True)
            layout.prop(s, "min_val_random", slider=True)
            layout.prop(s, "max_val_random", slider=True)
            layout.prop(s, "random_position")
        elif s.curve_source == 'SAVELOAD':
            row = layout.row(align=True)
            row.operator("curve.save_preset", icon='ADD')
            row.menu("CURVE_MT_presets_menu", text="Load", icon='IMPORT')

        if not selected_nodes:
            col = layout.column()
            col.enabled = False
            col.label(text="Select a FloatCurve node to enable Generate")

# ------------------------------
# Update handler for auto-refresh
# ------------------------------

def _settings_update(self, context):
    try:
        if getattr(self, "auto_refresh", False):
            generate_curve_from_settings(context)
    except Exception:
        pass

# ------------------------------
# Properties
# ------------------------------

class CurveGenSettings(bpy.types.PropertyGroup):
    curve_source: bpy.props.EnumProperty(
        name="Curve Source",
        items=[
            ('SPRING', "Spring", ""),
            ('ELASTIC', "Elastic", ""),
            ('BOUNCE', "Bounce", ""),
            ('STAIRS', "Stairs", ""),
            ('PEAKS', "Peaks", ""),
            ('RANDOM', "Random", ""),
            ('PRESET', "Preset", ""),
            ('CUSTOM', "Custom", ""),
            ('SAVELOAD', "Save/Load", ""),
        ],
        default='SPRING',
        update=_settings_update,
    )

    auto_refresh: bpy.props.BoolProperty(
        name="Auto Refresh",
        description="When enabled, the curve updates automatically when properties change",
        default=False,
        update=_settings_update,
    )

    use_vector_handles: bpy.props.BoolProperty(
        name="Use Vector Handles",
        default=False,
        description="Set point handles to VECTOR instead of AUTO",
        update=_settings_update,
    )

    # Preset / Custom
    preset_name: bpy.props.EnumProperty(
        name="Preset",
        items=[(k, k.replace("-", " ").title(), "") for k in EASING_PRESETS.keys()],
        default='linear',
        update=_settings_update,
    )
    css_string: bpy.props.StringProperty(
        name="Custom CSS",
        default="linear(0, 1)",
        update=_settings_update,
    )
    css_invert_horiz: bpy.props.BoolProperty(
        name="Invert Horizontally",
        default=False,
        update=_settings_update,
    )

    # Random
    num_points_random: bpy.props.IntProperty(
        name="Points",
        default=6,
        min=2,
        max=128,
        update=_settings_update,
    )
    min_val_random: bpy.props.FloatProperty(
        name="Min Value",
        default=-1.0,
        min=-1.0,
        max=0.0,
        update=_settings_update,
    )
    max_val_random: bpy.props.FloatProperty(
        name="Max Value",
        default=1.0,
        min=0.0,
        max=1.0,
        update=_settings_update,
    )
    random_position: bpy.props.BoolProperty(
        name="Random Position",
        default=False,
        update=_settings_update,
    )

    # Spring
    bounce: bpy.props.IntProperty(
        name="Bounce",
        default=5,
        min=1,
        max=30,
        update=_settings_update,
    )
    strength: bpy.props.FloatProperty(
        name="Strength",
        default=0.5,
        min=0.0,
        max=1.0,
        update=_settings_update,
    )
    invert_vert: bpy.props.BoolProperty(
        name="Invert Vertically",
        default=False,
        update=_settings_update,
    )
    invert_horiz: bpy.props.BoolProperty(
        name="Invert Horizontally",
        default=False,
        update=_settings_update,
    )

    # Elastic
    elastic_bounce: bpy.props.IntProperty(
        name="Bounce",
        default=5,
        min=1,
        max=30,
        update=_settings_update,
    )
    elastic_strength: bpy.props.FloatProperty(
        name="Strength",
        default=0.5,
        min=0.0,
        max=1.0,
        update=_settings_update,
    )
    elastic_invert_horiz: bpy.props.BoolProperty(
        name="Invert Horizontally",
        default=False,
        update=_settings_update,
    )

    # Bounce
    bounce_amount: bpy.props.IntProperty(
        name="Bounces",
        default=5,
        min=1,
        max=20,
        update=_settings_update,
    )
    bounce_invert_vert: bpy.props.BoolProperty(
        name="Invert Vertically",
        default=False,
        update=_settings_update,
    )

    # Stairs
    steps_count: bpy.props.IntProperty(
        name="Steps Counter",
        default=10,
        min=2,
        max=50,
        update=_settings_update,
    )
    stairs_invert_horiz: bpy.props.BoolProperty(
        name="Invert Horizontally",
        default=False,
        update=_settings_update,
    )

    # Peaks
    peaks_count: bpy.props.IntProperty(
        name="Peaks Count",
        default=2,
        min=1,
        max=50,
        update=_settings_update,
    )
    peaks_max_value: bpy.props.FloatProperty(
        name="Peaks Max Value",
        default=1.0,
        min=0.0,
        max=1.0,
        update=_settings_update,
    )
    peaks_randomizer: bpy.props.FloatProperty(
        name="Peaks Randomizer",
        default=0.0,
        min=0.0,
        max=1.0,
        description="0 = all peaks at max value; 1 = peaks randomized down to near 0",
        update=_settings_update,
    )

    # Save/Load
    SelectedCurve: bpy.props.StringProperty(name="Selected Curve", default="")

# ------------------------------
# Registration
# ------------------------------

classes = (
    CurveGenSettings,
    NODE_OT_GenerateCurve,
    NODE_PT_curve_generator,
    CURVE_MT_presets_menu,
    CURVE_OT_select_preset,
    CURVE_OT_save_preset,
)

def register():
    if relay_updater:
        relay_updater.register("blender-curve")
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.curve_gen_settings = bpy.props.PointerProperty(type=CurveGenSettings)

def unregister():
    if relay_updater:
        relay_updater.unregister()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.curve_gen_settings

if __name__ == "__main__":
    register()
