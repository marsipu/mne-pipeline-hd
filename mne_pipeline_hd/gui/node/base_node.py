# -*- coding: utf-8 -*-
import logging
from collections import OrderedDict

from mne_pipeline_hd.gui.gui_utils import format_color
from mne_pipeline_hd.gui.node.node_defaults import defaults
from mne_pipeline_hd.gui.node.ports import Port
from qtpy.QtCore import QRectF, Qt
from qtpy.QtGui import QColor, QPen, QPainterPath
from qtpy.QtWidgets import QGraphicsItem, QGraphicsTextItem, QGraphicsProxyWidget


class NodeTextItem(QGraphicsTextItem):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)


class BaseNode(QGraphicsItem):
    """Base class for all nodes in the NodeGraph.

    Parameters
    ----------
    ct : Controller
        A Controller-instance, where all session information is stored and managed.
    name : str
        Name of the node.
    ports : dict, list
        Dictionary with keys as (old) port id and values as dictionaries which contain kwargs for the :meth:`BaseNode.add_port()`.
    """

    def __init__(self, ct, name=None, ports=None):
        self.ct = ct
        # Initialize QGraphicsItem
        super().__init__()
        self.setFlags(
            self.GraphicsItemFlag.ItemIsSelectable | self.GraphicsItemFlag.ItemIsMovable
        )
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(1)

        # Initialize hidden attributes for properties (with node_defaults)
        self.id = id(self)
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

        # Initialize iports
        ports = ports or list()
        # If old id is added for reestablishing connections
        if isinstance(ports, dict):
            for port_id, port_kwargs in ports.values():
                self.add_port(old_id=port_id, **port_kwargs)
        else:
            for port_kwargs in ports:
                self.add_port(**port_kwargs)

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
        """Returns the input ports in a list (self._inputs is an OrderedDict and can be
        accessed internally when necessary)"""
        return list(self._inputs.values())

    @property
    def outputs(self):
        """Returns the output ports in a list (self._outputs is an OrderedDict and can
        be accessed internally when necessary)"""
        return list(self._outputs.values())

    @property
    def ports(self):
        """Returns all ports in a list."""
        return list(self._inputs.values()) + list(self._outputs.values())

    @property
    def widgets(self):
        return self._widgets

    @property
    def xy_pos(self):
        """Return the item scene postion. ("node.pos" conflicted with
        "QGraphicsItem.pos()" so it was refactored to "xy_pos".)

        Returns:
            list[float]: x, y scene position.
        """
        return [float(self.scenePos().x()), float(self.scenePos().y())]

    @xy_pos.setter
    def xy_pos(self, pos=None):
        """Set the item scene postion. ("node.pos" conflicted with "QGraphicsItem.pos()"
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
    def add_port(
        self,
        name,
        port_type,
        multi_connection=False,
        accepted_ports=None,
        old_id=None,
    ):
        """Adds a Port QGraphicsItem into the node.

        Parameters
        ----------
        name : str
            name for the port.
        port_type : str
            "in" or "out".
        multi_connection : bool
            allow multiple connections.
        accepted_ports : list, None
            list of accepted port names, if None all ports are accepted.
        old_id : int, None, optional
            old port id for reestablishing connections.

        Returns
        -------
        PortItem
            Port QGraphicsItem.
        """
        # Check port type
        if port_type not in ["in", "out"]:
            raise ValueError(f"Invalid port type: {port_type}")
        # port names must be unique for inputs/outputs
        existing = self.inputs if port_type == "in" else self.outputs
        if name in [p.name for p in existing]:
            logging.warning(f"Input port {name} already exists.")
            return
        # Create port
        port = Port(
            self, name, port_type, multi_connection, accepted_ports, old_id=old_id
        )
        # Add port to port-container
        ports = self._inputs if port_type == "in" else self._outputs
        ports[port.id] = port
        # Update scene
        if self.scene():
            self.draw_node()

        return port

    def add_input(
        self,
        name,
        multi_connection=False,
        accepted_ports=None,
    ):
        """Adds a Port QGraphicsItem into the node as input.

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
            Port QGraphicsItem.
        """
        port = self.add_port(name, "in", multi_connection, accepted_ports)

        return port

    def add_output(
        self,
        name,
        multi_connection=False,
        accepted_ports=None,
    ):
        """Adds a Port QGraphicsItem into the node as output.

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
            Port QGraphicsItem.
        """
        port = self.add_port(name, "out", multi_connection, accepted_ports)

        return port

    def port(self, port_type, port_idx=None, port_name=None, port_id=None, old_id=None):
        """Get port by the name or index.

        Parameters
        ----------
        port_type : str
            "in" or "out".
        port_idx : int
            Index of the port.
        port_name : str, optional
            Name of the port.
        port_id : int, optional
            Id of the port.
        old_id : int, optional
            Old id of the port for reestablishing connections.

        Returns
        -------
        Port
            The port that matches the provided index, name, or id. If multiple
            parameters are provided, the method will prioritize them in
            the following order: port_idx, port_name, port_id, old_id.
            If no parameters are provided or if no match is found.
            the method will return None.
        """
        if port_type not in ["in", "out"]:
            raise ValueError(f"Invalid port type: {port_type}")
        ports = self._inputs if port_type == "in" else self._outputs
        port_list = list(ports.values())

        if port_idx is not None:
            if not isinstance(port_idx, int):
                raise ValueError(f"Invalid port index: {port_idx}")
            if port_idx < len(port_list):
                return port_list[port_idx]
            else:
                logging.warning(f"{port_type} port {port_idx} not found.")
        elif port_name is not None:
            if not isinstance(port_name, str):
                raise ValueError(f"Invalid port name: {port_name}")
            port_names = [p for p in port_list if p.name == port_name]
            if len(port_names) > 1:
                logging.warning(
                    "More than one port with the same name. This should not be allowed."
                )
            elif len(port_names) == 0:
                logging.warning(f"{port_type} port {port_name} not found.")
            else:
                return port_names[0]
        elif port_id is not None:
            if not isinstance(port_id, int):
                raise ValueError(f"Invalid port id: {port_id}")
            if port_id in ports:
                return ports[port_id]
            else:
                logging.warning(f"{port_type} port {port_id} not found.")
        elif old_id is not None:
            if not isinstance(old_id, int):
                raise ValueError(f"Invalid old port id: {old_id}")
            old_id_ports = [p for p in port_list if p.old_id == old_id]
            if len(old_id_ports) > 1:
                logging.warning(
                    "More than one port with the same old id. This should not be allowed."
                )
            elif len(old_id_ports) == 0:
                logging.warning(f"{port_type} port with old id {old_id} not found.")
            else:
                return old_id_ports[0]
        else:
            logging.warning("No port identifier provided.")

    def input(self, **port_kwargs):
        """Get input port by the name, index, id or old id as in port()."""
        return self.port("in", **port_kwargs)

    def output(self, **port_kwargs):
        """Get output port by the name, index, id or old id as in port()."""
        return self.port("out", **port_kwargs)

    def connected_input_nodes(self):
        """Returns all nodes connected from the input ports.

        Returns:
            dict: {<input_port>: <node_list>}
        """
        nodes = OrderedDict()
        for p in self.inputs:
            nodes[p] = [cp.node for cp in p.connected_ports]
        return nodes

    def connected_output_nodes(self):
        """Returns all nodes connected from the output ports.

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
        """Remove node from the scene."""
        if self.scene() is not None:
            self.scene().removeItem(self)
        del self

    def to_dict(self):
        node_dict = {
            "name": self.name,
            "class": self.__class__.__name__,
            "pos": self.xy_pos,
            "ports": {p.id: p.to_dict() for p in self.ports},
        }

        return node_dict

    @classmethod
    def from_dict(cls, ct, node_dict):
        node_kwargs = {k: v for k, v in node_dict.items() if k not in ["class", "pos"]}
        node = cls(ct, **node_kwargs)
        node.xy_pos = node_dict["pos"]

        return node

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
        """Re-implemented to ignore event if LMB is over port collision area.

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
        """Re-implemented to ignore event if Alt modifier is pressed.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if event.modifiers() == Qt.KeyboardModifier.AltModifier:
            event.ignore()
            return
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        """Re-implemented to update pipes on selection changed.

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
        """Sets the initial base size for the node.

        Args:
            add_w (float): add additional width.
            add_h (float): add additional height.
        """
        self.width, self.height = self.calc_size(add_w, add_h)

    def _set_text_color(self, color):
        """Set text color.

        Args:
            color (tuple): color value in (r, g, b, a).
        """
        for port in self.inputs + self.outputs:
            port.text_color = color
        self._title_item.setDefaultTextColor(QColor(*color))

    def activate_pipes(self):
        """Active pipe color."""
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes.values():
                pipe.activate()

    def highlight_pipes(self):
        """Highlight pipe color."""
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes.values():
                pipe.highlight()

    def reset_pipes(self):
        """Reset all the pipe colors."""
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
        if self.scene():
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
        else:
            logging.warning("Node not in scene.")
