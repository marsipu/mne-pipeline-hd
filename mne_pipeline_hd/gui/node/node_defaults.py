# -*- coding: utf-8 -*-
from qtpy.QtCore import Qt

defaults = {
    "nodes": {
        "width": 160,
        "height": 60,
        "color": (23, 32, 41, 255),
        "selected_color": (255, 255, 255, 30),
        "border_color": (74, 84, 85, 255),
        "selected_border_color": (254, 207, 42, 255),
        "text_color": (255, 255, 255, 180),
    },
    "ports": {
        "size": 22,
        "color": (49, 115, 100, 255),
        "border_color": (29, 202, 151, 255),
        "active_color": (14, 45, 59, 255),
        "active_border_color": (107, 166, 193, 255),
        "hover_color": (17, 43, 82, 255),
        "hover_border_color": (136, 255, 35, 255),
        "click_falloff": 15,
    },
    "pipes": {
        "width": 1.2,
        "color": (175, 95, 30, 255),
        "disabled_color": (200, 60, 60, 255),
        "active_color": (70, 255, 220, 255),
        "highlight_color": (232, 184, 13, 255),
        "style": Qt.PenStyle.SolidLine,
    },
}
