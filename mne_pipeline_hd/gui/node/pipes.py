# -*- coding: utf-8 -*-
import math

from mne_pipeline_hd.gui.gui_utils import format_color
from mne_pipeline_hd.gui.node.node_defaults import defaults
from qtpy.QtCore import QPointF, Qt, QLineF, QRectF
from qtpy.QtGui import QPolygonF, QColor, QPainterPath, QBrush, QTransform, QPen
from qtpy.QtWidgets import (
    QGraphicsPathItem,
    QGraphicsItem,
    QGraphicsPolygonItem,
    QGraphicsTextItem,
)


class Pipe(QGraphicsPathItem):
    def __init__(self, input_port=None, output_port=None):
        """Initialize the pipe item.
        Notes
        -----
        The method "draw_path" has to be called at least once
        after the pipe is added to the scene.
        """
        super().__init__()

        # init QGraphicsPathItem
        self.setZValue(-1)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        # Hidden attributes
        self._input_port = input_port
        self._output_port = output_port
        self._color = defaults["pipes"]["color"]
        self._style = defaults["pipes"]["style"]
        self._active = False
        self._highlight = False

        size = 6.0
        self._poly = QPolygonF()
        self._poly.append(QPointF(-size, size))
        self._poly.append(QPointF(0.0, -size * 1.5))
        self._poly.append(QPointF(size, size))

        self._dir_pointer = QGraphicsPolygonItem(self)
        self._dir_pointer.setPolygon(self._poly)
        self._dir_pointer.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)

        self.set_pipe_styling(color=self.color, width=2, style=self.style)

    # --------------------------------------------------------------------------------------
    # Properties
    # --------------------------------------------------------------------------------------
    @property
    def input_port(self):
        return self._input_port

    @input_port.setter
    def input_port(self, port):
        self._input_port = port if hasattr(port, "connect_to") else None

    @property
    def output_port(self):
        return self._output_port

    @output_port.setter
    def output_port(self, port):
        self._output_port = port if hasattr(port, "connect_to") else None

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = format_color(color)

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, style):
        self._style = style

    # ----------------------------------------------------------------------------------
    # Qt methods
    # ----------------------------------------------------------------------------------
    def hoverEnterEvent(self, event):
        self.activate()

    def hoverLeaveEvent(self, event):
        self.reset()
        if self.input_port and self.output_port:
            if self.input_port.node.isSelected() or self.output_port.node.isSelected():
                self.highlight()
        if self.isSelected():
            self.highlight()

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemSelectedChange and self.scene():
            if value:
                self.highlight()
            else:
                self.reset()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget):
        """
        Draws the connection line between nodes.

        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        painter.save()

        pen = self.pen()
        if not self.isEnabled() and not self._active:
            pen.setColor(QColor(*defaults["pipes"]["disabled_color"]))
            pen.setStyle(Qt.PenStyle.DotLine)
            pen.setWidth(3)

        painter.setPen(pen)
        painter.setBrush(self.brush())
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)
        painter.drawPath(self.path())

        # QPaintDevice: Cannot destroy paint device that is being painted.
        painter.restore()

    @staticmethod
    def _calc_distance(p1, p2):
        x = math.pow((p2.x() - p1.x()), 2)
        y = math.pow((p2.y() - p1.y()), 2)
        return math.sqrt(x + y)

    def _draw_direction_pointer(self):
        """
        updates the pipe direction pointer arrow.
        """
        if not (self.input_port and self.output_port):
            self._dir_pointer.setVisible(False)
            return

        if not self.isEnabled() and not (self._active or self._highlight):
            color = QColor(*defaults["pipes"]["disabled_color"])
            pen = self._dir_pointer.pen()
            pen.setColor(color)
            self._dir_pointer.setPen(pen)
            self._dir_pointer.setBrush(color.darker(200))

        self._dir_pointer.setVisible(True)
        loc_pt = self.path().pointAtPercent(0.49)
        tgt_pt = self.path().pointAtPercent(0.51)
        radians = math.atan2(tgt_pt.y() - loc_pt.y(), tgt_pt.x() - loc_pt.x())
        degrees = math.degrees(radians) - 90
        self._dir_pointer.setRotation(degrees)
        self._dir_pointer.setPos(self.path().pointAtPercent(0.5))

        cen_x = self.path().pointAtPercent(0.5).x()
        cen_y = self.path().pointAtPercent(0.5).y()
        dist = math.hypot(tgt_pt.x() - cen_x, tgt_pt.y() - cen_y)

        self._dir_pointer.setVisible(True)
        if dist < 0.3:
            self._dir_pointer.setVisible(False)
            return
        if dist < 1.0:
            self._dir_pointer.setScale(dist)

    def draw_path(self, start_port, end_port=None, cursor_pos=None):
        """
        Draws the path between ports.

        Args:
            start_port (PortItem): port used to draw the starting point.
            end_port (PortItem): port used to draw the end point.
            cursor_pos (QtCore.QPointF): cursor position if specified this
                will be the draw end point.
        """
        if not start_port:
            return

        # get start / end positions.
        pos1 = start_port.scenePos()
        pos1.setX(pos1.x() + (start_port.boundingRect().width() / 2))
        pos1.setY(pos1.y() + (start_port.boundingRect().height() / 2))
        if cursor_pos:
            pos2 = cursor_pos
        elif end_port:
            pos2 = end_port.scenePos()
            pos2.setX(pos2.x() + (start_port.boundingRect().width() / 2))
            pos2.setY(pos2.y() + (start_port.boundingRect().height() / 2))
        else:
            return

        # visibility check for connected pipe.
        if self.input_port and self.output_port:
            is_visible = all(
                [
                    self._input_port.isVisible(),
                    self._output_port.isVisible(),
                    self._input_port.node.isVisible(),
                    self._output_port.node.isVisible(),
                ]
            )
            self.setVisible(is_visible)

            # don't draw pipe if a port or node is not visible.
            if not is_visible:
                return

        line = QLineF(pos1, pos2)
        path = QPainterPath()

        path.moveTo(line.x1(), line.y1())

        if self.scene():
            layout = self.scene().viewer().pipe_layout
        else:
            layout = "straight"

        if layout == "straight":
            path.lineTo(pos2)
        elif layout == "curved":
            ctr_offset_x1, ctr_offset_x2 = pos1.x(), pos2.x()
            tangent = abs(ctr_offset_x1 - ctr_offset_x2)

            max_width = start_port.node.boundingRect().width()
            tangent = min(tangent, max_width)
            if start_port.port_type == "in":
                ctr_offset_x1 -= tangent
                ctr_offset_x2 += tangent
            else:
                ctr_offset_x1 += tangent
                ctr_offset_x2 -= tangent

            ctr_point1 = QPointF(ctr_offset_x1, pos1.y())
            ctr_point2 = QPointF(ctr_offset_x2, pos2.y())
            path.cubicTo(ctr_point1, ctr_point2, pos2)
        elif layout == "angle":
            ctr_offset_x1, ctr_offset_x2 = pos1.x(), pos2.x()
            distance = abs(ctr_offset_x1 - ctr_offset_x2) / 2
            if start_port.port_type == "in":
                ctr_offset_x1 -= distance
                ctr_offset_x2 += distance
            else:
                ctr_offset_x1 += distance
                ctr_offset_x2 -= distance

            ctr_point1 = QPointF(ctr_offset_x1, pos1.y())
            ctr_point2 = QPointF(ctr_offset_x2, pos2.y())
            path.lineTo(ctr_point1)
            path.lineTo(ctr_point2)
            path.lineTo(pos2)
        self.setPath(path)

        self._draw_direction_pointer()

    def reset_path(self):
        """
        reset the pipe initial path position.
        """
        path = QPainterPath(QPointF(0.0, 0.0))
        self.setPath(path)
        self._draw_direction_pointer()

    def port_from_pos(self, pos, reverse=False):
        """
        Args:
            pos (QtCore.QPointF): current scene position.
            reverse (bool): false to return the nearest port.

        Returns:
            PortItem: port item.
        """
        inport_pos = self.input_port.scenePos()
        outport_pos = self.output_port.scenePos()
        input_dist = self._calc_distance(inport_pos, pos)
        output_dist = self._calc_distance(outport_pos, pos)
        if input_dist < output_dist:
            port = self.output_port if reverse else self.input_port
        else:
            port = self.input_port if reverse else self.output_port
        return port

    def set_pipe_styling(self, color, width=2, style=Qt.PenStyle.SolidLine):
        """
        Args:
            color (list or tuple): (r, g, b, a) values 0-255
            width (int): pipe width.
            style (int): pipe style.
        """
        pen = self.pen()
        pen.setWidth(width)
        pen.setColor(QColor(*color))
        pen.setStyle(style)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        pen = self._dir_pointer.pen()
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setWidth(width)
        pen.setColor(QColor(*color))
        self._dir_pointer.setPen(pen)
        self._dir_pointer.setBrush(QColor(*color).darker(200))

    def activate(self):
        self._active = True
        self.set_pipe_styling(
            color=defaults["pipes"]["active_color"],
            width=3,
            style=defaults["pipes"]["style"],
        )

    def active(self):
        return self._active

    def highlight(self):
        self._highlight = True
        self.set_pipe_styling(
            color=defaults["pipes"]["highlight_color"],
            width=2,
            style=defaults["pipes"]["style"],
        )

    def highlighted(self):
        return self._highlight

    def reset(self):
        """
        reset the pipe state and styling.
        """
        self._active = False
        self._highlight = False
        self.set_pipe_styling(color=self.color, width=2, style=self.style)
        self._draw_direction_pointer()

    def delete(self):
        # Remove pipe from connected_pipes in ports
        if self.input_port:
            self.input_port.connected_pipes.pop(self.output_port.id, None)
        if self.output_port:
            self.output_port.connected_pipes.pop(self.input_port.id, None)
        if self.scene():
            self.scene().removeItem(self)


class LivePipeItem(Pipe):
    """
    Live Pipe item used for drawing the live connection with the cursor.
    """

    def __init__(self):
        super(LivePipeItem, self).__init__()
        self.setZValue(4)

        self.color = defaults["pipes"]["active_color"]
        self.style = Qt.PenStyle.DashLine
        self.set_pipe_styling(color=self.color, width=3, style=self.style)

        self.shift_selected = False

        self._idx_pointer = LivePipePolygonItem(self)
        self._idx_pointer.setPolygon(self._poly)
        self._idx_pointer.setBrush(QColor(*self.color).darker(300))
        pen = self._idx_pointer.pen()
        pen.setWidth(self.pen().width())
        pen.setColor(self.pen().color())
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        self._idx_pointer.setPen(pen)

        color = self.pen().color()
        color.setAlpha(80)
        self._idx_text = QGraphicsTextItem(self)
        self._idx_text.setDefaultTextColor(color)
        font = self._idx_text.font()
        font.setPointSize(7)
        self._idx_text.setFont(font)

    def hoverEnterEvent(self, event):
        """
        re-implemented back to the base default behaviour or the pipe will
        lose it styling when another pipe is selected.
        """
        QGraphicsPathItem.hoverEnterEvent(self, event)

    def draw_path(self, start_port, end_port=None, cursor_pos=None, color=None):
        """
        re-implemented to also update the index pointer arrow position.

        Args:
            start_port (PortItem): port used to draw the starting point.
            end_port (PortItem): port used to draw the end point.
            cursor_pos (QtCore.QPointF): cursor position if specified this
                will be the draw end point.
            color (list[int]): override arrow index pointer color. (r, g, b)
        """
        super(LivePipeItem, self).draw_path(start_port, end_port, cursor_pos)
        self.draw_index_pointer(start_port, cursor_pos, color)

    def draw_index_pointer(self, start_port, cursor_pos, color=None):
        """
        Update the index pointer arrow position and direction when the
        live pipe path is redrawn.

        Args:
            start_port (PortItem): start port item.
            cursor_pos (QtCore.QPoint): cursor scene position.
            color (list[int]): override arrow index pointer color. (r, g, b).
        """
        text_rect = self._idx_text.boundingRect()

        transform = QTransform()
        transform.translate(cursor_pos.x(), cursor_pos.y())
        text_pos = (
            cursor_pos.x() - (text_rect.width() / 2),
            cursor_pos.y() - (text_rect.height() * 1.25),
        )
        if start_port.port_type == "in":
            transform.rotate(-90)
        else:
            transform.rotate(90)
        self._idx_text.setPos(*text_pos)
        self._idx_text.setPlainText("{}".format(start_port.name))

        self._idx_pointer.setPolygon(transform.map(self._poly))

        pen_color = QColor(*defaults["pipes"]["highlight_color"])
        if isinstance(color, (list, tuple)):
            pen_color = QColor(*color)

        pen = self._idx_pointer.pen()
        pen.setColor(pen_color)
        self._idx_pointer.setBrush(pen_color.darker(300))
        self._idx_pointer.setPen(pen)


class LivePipePolygonItem(QGraphicsPolygonItem):
    """
    Custom live pipe polygon shape.
    """

    def __init__(self, parent):
        super(LivePipePolygonItem, self).__init__(parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def paint(self, painter, option, widget):
        """
        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        painter.save()
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawPolygon(self.polygon())
        painter.restore()


class SlicerPipeItem(QGraphicsPathItem):
    """
    Base item used for drawing the pipe connection slicer.
    """

    def __init__(self):
        super(SlicerPipeItem, self).__init__()
        self.setZValue(5)

    def paint(self, painter, option, widget):
        """
        Draws the slicer pipe.

        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        color = QColor(*defaults["slicer"]["color"])
        p1 = self.path().pointAtPercent(0)
        p2 = self.path().pointAtPercent(1)
        size = 6.0
        offset = size / 2
        arrow_size = 4.0

        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        text = "slice"
        text_x = painter.fontMetrics().width(text) / 2
        text_y = painter.fontMetrics().height() / 1.5
        text_pos = QPointF(p1.x() - text_x, p1.y() - text_y)
        text_color = QColor(color)
        text_color.setAlpha(80)
        painter.setPen(
            QPen(text_color, defaults["slicer"]["width"], Qt.PenStyle.SolidLine)
        )
        painter.drawText(text_pos, text)

        painter.setPen(
            QPen(color, defaults["slicer"]["width"], Qt.PenStyle.DashDotLine)
        )
        painter.drawPath(self.path())

        pen = QPen(color, defaults["slicer"]["width"], Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(color)

        rect = QRectF(p1.x() - offset, p1.y() - offset, size, size)
        painter.drawEllipse(rect)

        arrow = QPolygonF()
        arrow.append(QPointF(-arrow_size, arrow_size))
        arrow.append(QPointF(0.0, -arrow_size * 0.9))
        arrow.append(QPointF(arrow_size, arrow_size))

        transform = QTransform()
        transform.translate(p2.x(), p2.y())
        radians = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        degrees = math.degrees(radians) - 90
        transform.rotate(degrees)

        painter.drawPolygon(transform.map(arrow))
        painter.restore()

    def draw_path(self, p1, p2):
        path = QPainterPath()
        path.moveTo(p1)
        path.lineTo(p2)
        self.setPath(path)
