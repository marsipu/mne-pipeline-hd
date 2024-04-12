# -*- coding: utf-8 -*-
from mne_pipeline_hd.gui.node.node_defaults import defaults
from qtpy.QtCore import Qt, QLineF
from qtpy.QtGui import QColor, QPen, QPainter
from qtpy.QtWidgets import QGraphicsScene


class NodeScene(QGraphicsScene):
    def __init__(self, parent=None):
        super(NodeScene, self).__init__(parent)
        self._grid_mode = "lines"
        self._grid_size = defaults["viewer"]["grid_size"]
        self._grid_color = defaults["viewer"]["grid_color"]
        self._bg_color = defaults["viewer"]["background_color"]
        self.setBackgroundBrush(QColor(*self._bg_color))

    @property
    def grid_mode(self):
        return self._grid_mode

    @grid_mode.setter
    def grid_mode(self, mode=None):
        if mode is None:
            mode = defaults["viewer"]["grid_mode"]
        self._grid_mode = mode

    @property
    def grid_size(self):
        return self._grid_size

    @grid_size.setter
    def grid_size(self, size=None):
        if size is None:
            size = defaults["viewer"]["grid_size"]
        self._grid_size = size

    @property
    def grid_color(self):
        return self._grid_color

    @grid_color.setter
    def grid_color(self, color=None):
        if color is None:
            color = defaults["viewer"]["grid_color"]
        self._grid_color = color

    @property
    def bg_color(self):
        return self._bg_color

    @bg_color.setter
    def bg_color(self, color=None):
        if color is None:
            color = defaults["viewer"]["background_color"]
        self._bg_color = color
        self.setBackgroundBrush(QColor(*self._bg_color))

    def _draw_grid(self, painter, rect, pen, grid_size):
        """
        draws the grid lines in the scene.

        Args:
            painter (QPainter): painter object.
            rect (QRectF): rect object.
            pen (QPen): pen object.
            grid_size (int): grid size.
        """
        left = int(rect.left())
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())

        first_left = left - (left % grid_size)
        first_top = top - (top % grid_size)

        lines = []
        lines.extend(
            [QLineF(x, top, x, bottom) for x in range(first_left, right, grid_size)]
        )
        lines.extend(
            [QLineF(left, y, right, y) for y in range(first_top, bottom, grid_size)]
        )

        painter.setPen(pen)
        painter.drawLines(lines)

    def _draw_dots(self, painter, rect, pen, grid_size):
        """
        draws the grid dots in the scene.

        Args:
            painter (QPainter): painter object.
            rect (QRectF): rect object.
            pen (QPen): pen object.
            grid_size (int): grid size.
        """
        zoom = self.viewer().get_zoom()
        if zoom < 0:
            grid_size = int(abs(zoom) / 0.3 + 1) * grid_size

        left = int(rect.left())
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())

        first_left = left - (left % grid_size)
        first_top = top - (top % grid_size)

        pen.setWidth(grid_size / 10)
        painter.setPen(pen)

        [
            painter.drawPoint(int(x), int(y))
            for x in range(first_left, right, grid_size)
            for y in range(first_top, bottom, grid_size)
        ]

    def drawBackground(self, painter, rect):
        super(NodeScene, self).drawBackground(painter, rect)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setBrush(self.backgroundBrush())

        if self._grid_mode == "dots":
            pen = QPen(QColor(*self.grid_color), 0.65)
            self._draw_dots(painter, rect, pen, self._grid_size)

        elif self._grid_mode == "lines":
            zoom = self.viewer().get_zoom()
            if zoom > -0.5:
                pen = QPen(QColor(*self.grid_color), 0.65)
                self._draw_grid(painter, rect, pen, self.grid_size)

            color = QColor(*self._bg_color).darker(200)
            if zoom < -0.0:
                color = color.darker(100 - int(zoom * 110))
            pen = QPen(color, 0.65)
            self._draw_grid(painter, rect, pen, self.grid_size * 8)

        painter.restore()

    def mousePressEvent(self, event):
        selected_nodes = self.viewer().selected_nodes()
        if self.viewer():
            self.viewer().sceneMousePressEvent(event)
        super(NodeScene, self).mousePressEvent(event)
        keep_selection = any(
            [
                event.button() == Qt.MouseButton.MiddleButton,
                event.button() == Qt.MouseButton.RightButton,
                event.modifiers() == Qt.KeyboardModifier.AltModifier,
            ]
        )
        if keep_selection:
            for node in selected_nodes:
                node.setSelected(True)

    def mouseMoveEvent(self, event):
        if self.viewer():
            self.viewer().sceneMouseMoveEvent(event)
        super(NodeScene, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.viewer():
            self.viewer().sceneMouseReleaseEvent(event)
        super(NodeScene, self).mouseReleaseEvent(event)

    def viewer(self):
        return self.views()[0] if self.views() else None
