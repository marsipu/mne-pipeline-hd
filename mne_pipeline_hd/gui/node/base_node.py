# -*- coding: utf-8 -*-
import logging
from collections import OrderedDict

from mne_pipeline_hd.gui.gui_utils import format_color
from mne_pipeline_hd.gui.node.node_defaults import defaults
from mne_pipeline_hd.gui.node.ports import Port
from qtpy.QtCore import QRectF, Qt
from qtpy.QtGui import QColor, QPen, QPainterPath
from qtpy.QtWidgets import QGraphicsItem, QGraphicsTextItem, QGraphicsProxyWidget


# Create a dict with node_defaults from _width to _text_color


class NodeTextItem(QGraphicsTextItem):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)


class BaseNode(QGraphicsItem):
    """
    Base class for all nodes in the NodeGraph.
    Parameters
    ----------
    ct : Controller
        A Controller-instance, where all session information is stored and managed.
    name : str
        Name of the node.
    inputs : dict
        Dictionary with input ports, where the key is the port name and
        the value is a dict with kwargs for the :meth:`BaseNode.add_input()`.
    outputs : dict
        Dictionary with output ports, where the key is the port name and
        the value is a dict with kwargs for :meth:`BaseNode.add_output()`.
    """

    def __init__(self, ct, name=None, inputs=None, outputs=None):
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
        self._name = name

        self._width = defaults["nodes"]["width"]
        self._height = defaults["nodes"]["height"]
        self._color = defaults["nodes"]["color"]
        self._selected_color = defaults["nodes"]["selected_color"]
        self._border_color = defaults["nodes"]["border_color"]
        self._selected_border_color = defaults["nodes"]["selected_border_color"]
        self._text_color = defaults["nodes"]["text_color"]

        self._title_item = NodeTextItem(self._name, self)
        self._inputs = OrderedDict()
        self._outputs = OrderedDict()
        self._widgets = list()

        # Initialize inputs and outputs
        inputs = inputs or dict()
        for input_name, input_kwargs in inputs.items():
            self.add_input(input_name, **input_kwargs)
        outputs = outputs or dict()
        for output_name, output_kwargs in outputs.items():
            self.add_output(output_name, **output_kwargs)

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
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        width = max(width, defaults["nodes"]["width"])
        self._width = width

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height):
        height = max(height, defaults["nodes"]["height"])
        self._height = height

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = format_color(color)
        self.update()

    @property
    def selected_color(self):
        return self._selected_color

    @selected_color.setter
    def selected_color(self, color):
        self._selected_color = format_color(color)
        self.update()

    @property
    def border_color(self):
        return self._border_color

    @border_color.setter
    def border_color(self, color):
        self._border_color = format_color(color)
        self.update()

    @property
    def selected_border_color(self):
        return self._selected_border_color

    @selected_border_color.setter
    def selected_border_color(self, color):
        self._selected_border_color = format_color(color)
        self.update()

    @property
    def text_color(self):
        return self._text_color

    @text_color.setter
    def text_color(self, color):
        self._text_color = format_color(color)
        self.update()

    @property
    def inputs(self):
        """
        This returns the input ports in a list
        (self._inputs is an OrderedDict and can be accessed internally when necessary)
        """
        return list(self._inputs.values())

    @property
    def outputs(self):
        """
        This returns the output ports in a list
        (self._outputs is an OrderedDict and can be accessed internally when necessary)
        """
        return list(self._outputs.values())

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
        pos = pos or (0.0, 0.0)
        self.setPos(*pos)

    @property
    def viewer(self):
        if self.scene():
            return self.scene().viewer()

    # ----------------------------------------------------------------------------------
    # Logic methods
    # ----------------------------------------------------------------------------------

    def add_input(
        self,
        name,
        multi_connection=False,
        accepted_ports=None,
    ):
        """
        Adds a port qgraphics item into the node with the "port_type" set as
        Parameters
        ----------
        name : str
            name for the port.
        multi_connection : bool
            allow multiple connections.
        accepted_ports : list, None
            list of accepted port names, if None all ports are accepted.

        Returns
        -------
        PortItem
            port qgraphics item.
        """
        # port names must be unique
        if name in [p.name for p in self.inputs]:
            logging.warning(f"Input port {name} already exists.")
            return
        port = Port(self, name, "in", multi_connection, accepted_ports)
        self._inputs[port.id] = port
        if self.scene():
            self.draw_node()

        return port

    def add_output(
        self,
        name,
        multi_connection=False,
        accepted_ports=None,
    ):
        """
        Adds a port qgraphics item into the node with the "port_type" set as
        Parameters
        ----------
        name : str
            name for the port.
        multi_connection : bool
            allow multiple connections.
        accepted_ports : list, None
            list of accepted port names, if None all ports are accepted.

        Returns
        -------
        PortItem
            port qgraphics item.
        """
        # port names must be unique
        if name in [p.name for p in self.outputs]:
            logging.warning(f"Output port {name} already exists.")
            return
        port = Port(self, name, "out", multi_connection, accepted_ports)
        self._outputs[port.id] = port
        if self.scene():
            self.draw_node()

        return port

    def input(self, port):
        """
        Get input port by the name, index or id.

        Args:
            port (str or int): port name, index or id.

        Returns:
            NodeGraphQt.Port: node port.
        """
        if isinstance(port, int):
            # Get input port by id
            if port in self._inputs:
                return self._inputs[port]
            # Get input port by index (self.inputs returns a list)
            elif port < len(self.inputs):
                return self.inputs[port]
        elif isinstance(port, str):
            port_names = [p.name for p in self.inputs]
            if port in port_names:
                name_index = port_names.index(port)
                return self.inputs[name_index]

    def output(self, port):
        """
        Get output port by the name, index or id.

        Args:
            port (str or int): port name, index or id.

        Returns:
            NodeGraphQt.Port: node port.
        """
        if isinstance(port, int):
            # Get output port by id
            if port in self._outputs:
                return self._outputs[port]
            # Get output port by index (self.outputs returns a list)
            elif port < len(self.outputs):
                return self.outputs[port]
        elif isinstance(port, str):
            port_names = [p.name for p in self.outputs]
            if port in port_names:
                name_index = port_names.index(port)
                return self.outputs[name_index]

    def port(self, port_type, port):
        """
        Get port by the name or index.

        Args:
            port_type (str): "in" or "out".
            port (str or int): port name or index.

        Returns:
            NodeGraphQt.Port: node port.
        """
        if port_type == "in":
            return self.input(port)
        elif port_type == "out":
            return self.output(port)

    def set_input(self, index, port):
        """
        Creates a connection pipe to the targeted output :class:`Port`.

        Args:
            index (int): index of the port.
            port (NodeGraphQt.Port): port object.
        """
        src_port = self.input(index)
        if src_port is None:
            logging.warning(f"Input port {index} not found.")
        else:
            src_port.connect_to(port)

    def set_output(self, index, port):
        """
        Creates a connection pipe to the targeted input :class:`Port`.

        Args:
            index (int): index of the port.
            port (NodeGraphQt.Port): port object.
        """
        src_port = self.output(index)
        if src_port is None:
            logging.warning(f"Output port {index} not found.")
        else:
            src_port.connect_to(port)

    def connected_input_nodes(self):
        """
        Returns all nodes connected from the input ports.

        Returns:
            dict: {<input_port>: <node_list>}
        """
        nodes = OrderedDict()
        for p in self.inputs:
            nodes[p] = [cp.node for cp in p.connected_ports]
        return nodes

    def connected_output_nodes(self):
        """
        Returns all nodes connected from the output ports.

        Returns:
            dict: {<output_port>: <node_list>}
        """
        nodes = OrderedDict()
        for p in self.outputs:
            nodes[p] = [cp.node for cp in p.connected_ports]
        return nodes

    def add_widget(self, widget):
        """Add widget to the node."""
        proxy_widget = QGraphicsProxyWidget(self)
        proxy_widget.setWidget(widget)
        self.widgets.append(proxy_widget)

    def delete(self):
        """
        Remove node from the scene.
        """
        if self.scene() is not None:
            self.scene().removeItem(self)
        del self

    def to_dict(self):
        node_dict = {
            "name": self.name,
            "class": self.__class__.__name__,
            "pos": self.xy_pos,
            "inputs": {p.id: p.to_dict() for p in self.inputs},
            "outputs": {p.id: p.to_dict() for p in self.outputs},
        }

        return node_dict

    @classmethod
    def from_dict(cls, node_dict, ct):
        node = cls(ct, name=node_dict["name"])
        node.xy_pos = node_dict["pos"]
        port_dict = dict()
        for port_id, port_dict in node_dict["inputs"].items():
            port = node.add_input()
            port_dict[port_id] = port

    # ----------------------------------------------------------------------------------
    # Qt methods
    # ----------------------------------------------------------------------------------
    def boundingRect(self):
        # NodeViewer.node_position_scene() depends
        # on the position of boundingRect to be (0, 0).
        return QRectF(0, 0, self.width, self.height)

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
        text_rect = self._title_item.boundingRect()
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
            for p in self.inputs + self.outputs:
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
            if self.isSelected():
                self.setZValue(1)
            else:
                self.setZValue(2)

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
        for port in self.inputs + self.outputs:
            port.text_color = color
        self._title_item.setDefaultTextColor(QColor(*color))

    def activate_pipes(self):
        """
        active pipe color.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes.values():
                pipe.activate()

    def highlight_pipes(self):
        """
        Highlight pipe color.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes.values():
                pipe.highlight()

    def reset_pipes(self):
        """
        Reset all the pipe colors.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes.values():
                pipe.reset()

    @staticmethod
    def _get_ports_size(ports):
        width = 0.0
        height = 0.0
        for port in ports:
            if not port.isVisible():
                continue
            port_width = port.boundingRect().width() / 2
            text_width = port.text.boundingRect().width()
            width = max([width, port_width + text_width])
            height += port.boundingRect().height()
        return width, height

    def calc_size(self, add_w=0.0, add_h=0.0):
        # width, height from node name text.
        title_width = self._title_item.boundingRect().width()
        title_height = self._title_item.boundingRect().height()

        # width, height from node ports.
        input_width, input_height = self._get_ports_size(self.inputs)

        # width, height from outputs
        output_width, output_height = self._get_ports_size(self.outputs)

        # width, height from node embedded widgets.
        widget_width = 0.0
        widget_height = 0.0
        for proxy_widget in self.widgets:
            if not proxy_widget.isVisible():
                continue
            w_width = proxy_widget.boundingRect().width()
            w_height = proxy_widget.boundingRect().height()
            widget_width = max([widget_width, w_width])
            widget_height += w_height

        width = input_width + output_width
        height = max([title_height, input_height, output_height, widget_height])
        # add additional width for node widget.
        if widget_width:
            width += widget_width
        # add padding if no inputs or outputs.
        if not self.inputs or not self.outputs:
            width += 10
        # add bottom margin for node widget.
        if widget_height:
            height += 10

        width += add_w
        height += add_h

        width = max([width, title_width])

        return width, height

    def align_title(self):
        rect = self.boundingRect()
        text_rect = self._title_item.boundingRect()
        x = rect.center().x() - (text_rect.width() / 2)
        self._title_item.setPos(x, rect.y())

    def align_widgets(self, v_offset=0.0):
        if not self.widgets:
            return
        rect = self.boundingRect()
        y = rect.y() + v_offset
        inputs = [p for p in self.inputs if p.isVisible()]
        outputs = [p for p in self.outputs if p.isVisible()]
        for widget in self.widgets:
            if not widget.isVisible():
                continue
            widget_rect = widget.boundingRect()
            if not inputs:
                x = rect.left() + 10
            elif not outputs:
                x = rect.right() - widget_rect.width() - 10
            else:
                x = rect.center().x() - (widget_rect.width() / 2)
            widget.setPos(x, y)
            y += widget_rect.height()

    def align_ports(self, v_offset=0.0):
        width = self._width
        spacing = 1

        # adjust input position
        inputs = [p for p in self.inputs if p.isVisible()]
        if inputs:
            port_width = inputs[0].boundingRect().width()
            port_height = inputs[0].boundingRect().height()
            port_x = (port_width / 2) * -1
            port_y = v_offset
            for port in inputs:
                port.setPos(port_x, port_y)
                port_y += port_height + spacing

        # adjust output position
        outputs = [p for p in self.outputs if p.isVisible()]
        if outputs:
            port_width = outputs[0].boundingRect().width()
            port_height = outputs[0].boundingRect().height()
            port_x = width - (port_width / 2)
            port_y = v_offset
            for port in outputs:
                port.setPos(port_x, port_y)
                port_y += port_height + spacing

    def draw_node(self):
        height = self._title_item.boundingRect().height() + 4

        # setup initial base size.
        self._set_base_size(add_h=height)
        # set text color when node is initialized.
        self._set_text_color(self.text_color)

        # --- set the initial node layout ---
        # align title text
        self.align_title()
        # arrange input and output ports.
        self.align_ports(v_offset=height)
        # arrange node widgets
        self.align_widgets(v_offset=height)

        self.update()
