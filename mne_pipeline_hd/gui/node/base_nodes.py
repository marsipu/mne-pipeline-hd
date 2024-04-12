# -*- coding: utf-8 -*-
from collections import OrderedDict

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPen, QPainterPath
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem, QGraphicsProxyWidget

from gui.node.ports import Port
from mne_pipeline_hd.gui.node import node_defaults


# Create a dict with node_defaults from _width to _text_color


class NodeTextItem(QGraphicsTextItem):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)


class BaseNode(QGraphicsItem):
    def __init__(self, ct):
        self.ct = ct
        # Initialize QGraphicsItem
        super().__init__()
        self.setFlags(
            self.GraphicsItemFlag.ItemIsSelectable | self.GraphicsItemFlag.ItemIsMovable
        )
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(1)

        # Initialize hidden attributes for properties (with node_defaults)
        self._id = id(self)
        self._name = "Base Node"
        self._node_type = "base_node"

        self._width = node_defaults["nodes"]["width"]
        self._height = node_defaults["nodes"]["height"]
        self._color = node_defaults["nodes"]["color"]
        self._selected_color = node_defaults["nodes"]["selected_color"]
        self._border_color = node_defaults["nodes"]["border_color"]
        self._selected_border_color = node_defaults["nodes"]["selected_border_color"]
        self._text_color = node_defaults["nodes"]["text_color"]

        self._title_item = NodeTextItem(self._name, self)
        self._inputs = OrderedDict()
        self._outputs = OrderedDict()
        self._widgets = list()

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name
        self._title_item.setPlainText(name)

    @property
    def node_type(self):
        return self._node_type

    @node_type.setter
    def node_type(self, node_type):
        self._node_type = node_type

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        width = max(width, node_defaults["nodes"]["width"])
        self._width = width

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height):
        height = max(height, node_defaults["nodes"]["height"])
        self._height = height

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color
        self.update()

    @property
    def selected_color(self):
        return self._selected_color

    @selected_color.setter
    def selected_color(self, color):
        self._selected_color = color
        self.update()

    @property
    def border_color(self):
        return self._border_color

    @border_color.setter
    def border_color(self, color):
        self._border_color = color
        self.update()

    @property
    def selected_border_color(self):
        return self._selected_border_color

    @selected_border_color.setter
    def selected_border_color(self, color):
        self._selected_border_color = color
        self.update()

    @property
    def text_color(self):
        return self._text_color

    @text_color.setter
    def text_color(self, color):
        self._text_color = color
        self.update()

    @property
    def inputs(self):
        return self._inputs

    @property
    def outputs(self):
        return self._outputs

    @property
    def widgets(self):
        return self._widgets

    @property
    def xy_pos(self):
        """
        return the item scene postion.
        ("node.pos" conflicted with "QGraphicsItem.pos()"
        so it was refactored to "xy_pos".)

        Returns:
            list[float]: x, y scene position.
        """
        return [float(self.scenePos().x()), float(self.scenePos().y())]

    @xy_pos.setter
    def xy_pos(self, pos=None):
        """
        set the item scene postion.
        ("node.pos" conflicted with "QGraphicsItem.pos()"
        so it was refactored to "xy_pos".)

        Args:
            pos (list[float]): x, y scene position.
        """
        pos = pos or [0.0, 0.0]
        self.setPos(pos[0], pos[1])

    # --------------------------------------------------------------------------------------
    # Qt methods
    # --------------------------------------------------------------------------------------
    def boundingRect(self):
        return QRectF(self.x(), self.y(), self.width, self.height)

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # base background.
        margin = 1.0
        rect = self.boundingRect()
        rect = QRectF(
            rect.left() + margin,
            rect.top() + margin,
            rect.width() - (margin * 2),
            rect.height() - (margin * 2),
        )

        radius = 4.0
        painter.setBrush(QColor(*self.color))
        painter.drawRoundedRect(rect, radius, radius)

        # light overlay on background when selected.
        if self.isSelected():
            painter.setBrush(QColor(*self.selected_color))
            painter.drawRoundedRect(rect, radius, radius)

        # node name background.
        padding = 3.0, 2.0
        text_rect = self._text_item.boundingRect()
        text_rect = QRectF(
            text_rect.x() + padding[0],
            rect.y() + padding[1],
            rect.width() - padding[0] - margin,
            text_rect.height() - (padding[1] * 2),
        )
        if self.isSelected():
            painter.setBrush(QColor(*self.selected_color))
        else:
            painter.setBrush(QColor(0, 0, 0, 80))
        painter.drawRoundedRect(text_rect, 3.0, 3.0)

        # node border
        if self.isSelected():
            border_width = 1.2
            border_color = QColor(*self.selected_border_color)
        else:
            border_width = 0.8
            border_color = QColor(*self.border_color)

        border_rect = QRectF(rect.left(), rect.top(), rect.width(), rect.height())

        pen = QPen(border_color, border_width)
        pen.setCosmetic(True)
        path = QPainterPath()
        path.addRoundedRect(border_rect, radius, radius)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
        painter.drawPath(path)

        painter.restore()

    def mousePressEvent(self, event):
        """
        Re-implemented to ignore event if LMB is over port collision area.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            for p in self._input_items.keys():
                if p.hovered:
                    event.ignore()
                    return
            for p in self._output_items.keys():
                if p.hovered:
                    event.ignore()
                    return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Re-implemented to ignore event if Alt modifier is pressed.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if event.modifiers() == Qt.KeyboardModifier.AltModifier:
            event.ignore()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        # ToDo: implement (e.g. open function code etc.)
        pass

    def itemChange(self, change, value):
        """
        Re-implemented to update pipes on selection changed.

        Args:
            change:
            value:
        """
        if change == self.GraphicsItemChange.ItemSelectedChange and self.scene():
            self.reset_pipes()
            if value:
                self.highlight_pipes()
            self.setZValue(1)
            if not self.selected:
                self.setZValue(1 + 1)
        elif change == self.GraphicsItemChange.ItemPositionChange:
            self.xy_pos = value

        return super().itemChange(change, value)

    def _set_base_size(self, add_w=0.0, add_h=0.0):
        """
        Sets the initial base size for the node.

        Args:
            add_w (float): add additional width.
            add_h (float): add additional height.
        """
        self.width, self.height = self.calc_size(add_w, add_h)

    def _set_text_color(self, color):
        """
        set text color.

        Args:
            color (tuple): color value in (r, g, b, a).
        """
        text_color = QColor(*color)
        for port, text in self._input_items.items():
            text.setDefaultTextColor(text_color)
        for port, text in self._output_items.items():
            text.setDefaultTextColor(text_color)
        self._text_item.setDefaultTextColor(text_color)

    def activate_pipes(self):
        """
        active pipe color.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.activate()

    def highlight_pipes(self):
        """
        Highlight pipe color.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.highlight()

    def reset_pipes(self):
        """
        Reset all the pipe colors.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.reset()

    def calc_size(self):
        # width, height from node name text.
        text_w = self._title_item.boundingRect().width()
        text_h = self._title_item.boundingRect().height()

        # width, height from node ports.
        port_width = 0.0
        p_input_text_width = 0.0
        p_output_text_width = 0.0
        p_input_height = 0.0
        p_output_height = 0.0
        for port, text in self._input_items.items():
            if not port.isVisible():
                continue
            if not port_width:
                port_width = port.boundingRect().width()
            t_width = text.boundingRect().width()
            if text.isVisible() and t_width > p_input_text_width:
                p_input_text_width = text.boundingRect().width()
            p_input_height += port.boundingRect().height()
        for port, text in self._output_items.items():
            if not port.isVisible():
                continue
            if not port_width:
                port_width = port.boundingRect().width()
            t_width = text.boundingRect().width()
            if text.isVisible() and t_width > p_output_text_width:
                p_output_text_width = text.boundingRect().width()
            p_output_height += port.boundingRect().height()

        port_text_width = p_input_text_width + p_output_text_width

        # width, height from node embedded widgets.
        widget_width = 0.0
        widget_height = 0.0
        for proxy_widget in self.widgets:
            if not proxy_widget.isVisible():
                continue
            w_width = proxy_widget.boundingRect().width()
            w_height = proxy_widget.boundingRect().height()
            if w_width > widget_width:
                widget_width = w_width
            widget_height += w_height

        side_padding = 0.0
        if all([widget_width, p_input_text_width, p_output_text_width]):
            port_text_width = max([p_input_text_width, p_output_text_width])
            port_text_width *= 2
        elif widget_width:
            side_padding = 10

        width = port_width + max([text_w, port_text_width]) + side_padding
        height = max([text_h, p_input_height, p_output_height, widget_height])
        if widget_width:
            # add additional width for node widget.
            width += widget_width
        if widget_height:
            # add bottom margin for node widget.
            height += 4.0
        height *= 1.05

        return width, height

    def align_title(self):
        rect = self.boundingRect()
        text_rect = self._title_item.boundingRect()
        x = rect.center().x() - (text_rect.width() / 2)
        self._text_item.setPos(x, rect.y())

    def align_widgets(self):
        if not self.widgets:
            return
        rect = self.boundingRect()
        y = rect.y()
        inputs = [p for p in self.inputs if p.isVisible()]
        outputs = [p for p in self.outputs if p.isVisible()]
        for widget in self.widgets:
            if not widget.isVisible():
                continue
            widget_rect = widget.boundingRect()
            if not inputs:
                x = rect.left() + 10
                widget.widget().setTitleAlign("left")
            elif not outputs:
                x = rect.right() - widget_rect.width() - 10
                widget.widget().setTitleAlign("right")
            else:
                x = rect.center().x() - (widget_rect.width() / 2)
                widget.widget().setTitleAlign("center")
            widget.setPos(x, y)
            y += widget_rect.height()

    def align_ports(self):
        width = self._width
        txt_offset = node_defaults["ports"]["click_falloff"] - 2
        spacing = 1

        # adjust input position
        inputs = [p for p in self.inputs if p.isVisible()]
        if inputs:
            port_width = inputs[0].boundingRect().width()
            port_height = inputs[0].boundingRect().height()
            port_x = (port_width / 2) * -1
            port_y = 0
            for port in inputs:
                port.setPos(port_x, port_y)
                port_y += port_height + spacing
        # adjust input text position
        for port, text in self._input_items.items():
            if port.isVisible():
                txt_x = port.boundingRect().width() / 2 - txt_offset
                text.setPos(txt_x, port.y() - 1.5)

        # adjust output position
        outputs = [p for p in self.outputs if p.isVisible()]
        if outputs:
            port_width = outputs[0].boundingRect().width()
            port_height = outputs[0].boundingRect().height()
            port_x = width - (port_width / 2)
            port_y = 0
            for port in outputs:
                port.setPos(port_x, port_y)
                port_y += port_height + spacing
        # adjust output text position
        for port, text in self._output_items.items():
            if port.isVisible():
                txt_width = text.boundingRect().width() - txt_offset
                txt_x = port.x() - txt_width
                text.setPos(txt_x, port.y() - 1.5)

    def draw_node(self):
        height = self._title_item.boundingRect().height() + 4.0

        # update port text items in visibility.
        for port, text in self._input_items.items():
            if port.isVisible():
                text.setVisible(port.display_name)
        for port, text in self._output_items.items():
            if port.isVisible():
                text.setVisible(port.display_name)

        # setup initial base size.
        self._set_base_size(add_h=height)
        # set text color when node is initialized.
        self._set_text_color(self.text_color)

        # --- set the initial node layout ---
        # align title text
        self.align_title()
        # arrange input and output ports.
        self.align_ports()
        # arrange node widgets
        self.align_widgets()

        self.update()

    def _add_port(self, port):
        """
        Adds a port qgraphics item into the node.

        Args:
            port (PortItem): port item.

        Returns:
            PortItem: port qgraphics item.
        """
        text = QGraphicsTextItem(port.name, self)
        text.font().setPointSize(8)
        text.setFont(text.font())
        text.setVisible(port.display_name)
        text.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        if port.port_type == "in":
            self._input_items[port] = text
        elif port.port_type == "out":
            self._output_items[port] = text
        if self.scene():
            self.draw_node()
        return port

    def add_input(
        self,
        name="input",
        multi_port=False,
        display_name=True,
        locked=False,
    ):
        """
        Adds a port qgraphics item into the node with the "port_type" set as
        IN_PORT.

        Args:
            name (str): name for the port.
            multi_port (bool): allow multiple connections.
            display_name (bool): display the port name.
            locked (bool): locked state.
            painter_func (function): custom paint function.

        Returns:
            PortItem: input port qgraphics item.
        """
        port = Port(self)
        port.name = name
        port.port_type = "in"
        port.multi_connection = multi_port
        port.display_name = display_name
        port.locked = locked
        return self._add_port(port)

    def add_output(
        self,
        name="output",
        multi_port=False,
        display_name=True,
        locked=False,
    ):
        """
        Adds a port qgraphics item into the node with the "port_type" set as
        OUT_PORT.

        Args:
            name (str): name for the port.
            multi_port (bool): allow multiple connections.
            display_name (bool): display the port name.
            locked (bool): locked state.
            painter_func (function): custom paint function.

        Returns:
            PortItem: output port qgraphics item.
        """

        port = Port(self)
        port.name = name
        port.port_type = "out"
        port.multi_connection = multi_port
        port.display_name = display_name
        port.locked = locked
        return self._add_port(port)

    def _delete_port(self, port, text):
        """
        Removes port item and port text from node.

        Args:
            port (PortItem): port object.
            text (QtWidgets.QGraphicsTextItem): port text object.
        """
        port.setParentItem(None)
        text.setParentItem(None)
        self.scene().removeItem(port)
        self.scene().removeItem(text)
        del port
        del text

    def delete_input(self, port):
        """
        Remove input port from node.

        Args:
            port (PortItem): port object.
        """
        self._delete_port(port, self._input_items.pop(port))

    def delete_output(self, port):
        """
        Remove output port from node.

        Args:
            port (PortItem): port object.
        """
        self._delete_port(port, self._output_items.pop(port))

    def add_widget(self, widget):
        """Add widget to the node."""
        proxy_widget = QGraphicsProxyWidget(self)
        proxy_widget.setWidget(widget)
        self.widgets.apppend(proxy_widget)

    def delete(self):
        """
        Remove node from the scene.
        """
        for port, text in self._input_items.items():
            self.delete_input(port)
        for port, text in self._output_items.items():
            self.delete_output(port)
        self.scene().removeItem(self)
        del self
