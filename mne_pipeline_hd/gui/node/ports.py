# -*- coding: utf-8 -*-
import logging
from collections import OrderedDict

from mne_pipeline_hd.gui.gui_utils import format_color
from mne_pipeline_hd.gui.node.node_defaults import defaults
from mne_pipeline_hd.gui.node.pipes import Pipe
from qtpy.QtCore import QRectF
from qtpy.QtGui import QColor, QPen
from qtpy.QtWidgets import QGraphicsItem, QGraphicsTextItem


class PortText(QGraphicsTextItem):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.font().setPointSize(8)
        self.setFont(self.font())
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)


class Port(QGraphicsItem):
    """A graphical representation of a port in a node-based interface.

    This class represents a port which can be an input or output port of a node.
    It supports hover events, multiple connections, and connection compatibility checks.
    It also handles the drawing of the port and its connections.

    Parameters
    ----------
    node : Node
        The node this port is part of.
    name : str
        The name of the port.
    port_type : str
        The type of the port, can be either 'in' or 'out'.
    multi_connection : bool
        Whether the port supports multiple connections or not, defaults to False.
    accepted_ports : list, None
        List of port names that this port can connect to.
        If None, it can connect to any port.
    """

    def __init__(
        self,
        node,
        name,
        port_type,
        multi_connection=False,
        accepted_ports=None,
    ):
        super().__init__(node)

        # init Qt graphics item
        self.setAcceptHoverEvents(True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(self.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.setZValue(2)

        # init text item
        self.text = PortText(name, self)

        # (hidden) attributes
        self.node = node
        self.id = id(self)
        self._name = name
        self._port_type = port_type
        self.multi_connection = multi_connection
        self.connected_ports = list()
        self.connected_pipes = OrderedDict()
        self.accepted_ports = accepted_ports

        self._width = defaults["ports"]["size"]
        self._height = defaults["ports"]["size"]
        self._color = defaults["ports"]["color"]
        self._border_color = defaults["ports"]["border_color"]
        self._active_color = defaults["ports"]["active_color"]
        self._active_border_color = defaults["ports"]["active_border_color"]
        self._hover_color = defaults["ports"]["hover_color"]
        self._hover_border_color = defaults["ports"]["hover_border_color"]
        self._text_color = defaults["nodes"]["text_color"]
        self._hovered = False

    # --------------------------------------------------------------------------------------
    # Properties
    # --------------------------------------------------------------------------------------
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self.text.setPlainText(value)

    @property
    def port_type(self):
        return self._port_type

    @port_type.setter
    def port_type(self, value):
        if value not in ["in", "out"]:
            raise ValueError(f"Invalid port type: {value}")
        self._port_type = value

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        width = max(width, defaults["ports"]["size"])
        self._width = width

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height):
        height = max(height, defaults["ports"]["size"])
        self._height = height

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = format_color(color)
        self.update()

    @property
    def border_color(self):
        return self._border_color

    @border_color.setter
    def border_color(self, color):
        self._border_color = format_color(color)
        self.update()

    @property
    def active_color(self):
        return self._active_color

    @active_color.setter
    def active_color(self, color):
        self._active_color = format_color(color)
        self.update()

    @property
    def active_border_color(self):
        return self._active_border_color

    @active_border_color.setter
    def active_border_color(self, color):
        self._active_border_color = format_color(color)
        self.update()

    @property
    def hover_color(self):
        return self._hover_color

    @hover_color.setter
    def hover_color(self, color):
        self._hover_color = format_color(color)
        self.update()

    @property
    def hover_border_color(self):
        return self._hover_border_color

    @hover_border_color.setter
    def hover_border_color(self, color):
        self._hover_border_color = format_color(color)
        self.update()

    @property
    def text_color(self):
        return self._text_color

    @text_color.setter
    def text_color(self, color):
        self._text_color = format_color(color)
        self.text.setDefaultTextColor(QColor(*self._text_color))

    @property
    def hovered(self):
        return self._hovered

    @hovered.setter
    def hovered(self, hovered):
        self._hovered = hovered
        self.update()

    # --------------------------------------------------------------------------------------
    # Qt methods
    # --------------------------------------------------------------------------------------
    def boundingRect(self):
        # NodeViewer.port_position_scene() depends
        # on the position of boundingRect to be (0, 0).
        return QRectF(
            0.0,
            0.0,
            self._width + defaults["ports"]["click_falloff"],
            self._height,
        )

    def setPos(self, x, y):
        super().setPos(x, y)
        falloff = defaults["ports"]["click_falloff"] - 2
        if self.port_type == "in":
            offset = self.boundingRect().width() - falloff
        else:
            offset = -self.text.boundingRect().width() + falloff
        self.text.setPos(offset, -1.5)

    def paint(self, painter, option, widget=None):
        """Draws the circular port.

        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        painter.save()

        rect_w = self._width / 1.8
        rect_h = self._height / 1.8
        rect_x = self.boundingRect().center().x() - (rect_w / 2)
        rect_y = self.boundingRect().center().y() - (rect_h / 2)
        port_rect = QRectF(rect_x, rect_y, rect_w, rect_h)

        if self._hovered:
            color = QColor(*self.hover_color)
            border_color = QColor(*self.hover_border_color)
        elif len(self.connected_pipes) > 0:
            color = QColor(*self.active_color)
            border_color = QColor(*self.active_border_color)
        else:
            color = QColor(*self.color)
            border_color = QColor(*self.border_color)

        pen = QPen(border_color, 1.8)
        painter.setPen(pen)
        painter.setBrush(color)
        painter.drawEllipse(port_rect)

        if self.connected_pipes and not self._hovered:
            painter.setBrush(border_color)
            w = port_rect.width() / 2.5
            h = port_rect.height() / 2.5
            rect = QRectF(
                port_rect.center().x() - w / 2, port_rect.center().y() - h / 2, w, h
            )
            border_color = QColor(*self.border_color)
            pen = QPen(border_color, 1.6)
            painter.setPen(pen)
            painter.setBrush(border_color)
            painter.drawEllipse(rect)
        elif self._hovered:
            if self.multi_connection:
                pen = QPen(border_color, 1.4)
                painter.setPen(pen)
                painter.setBrush(color)
                w = port_rect.width() / 1.8
                h = port_rect.height() / 1.8
            else:
                painter.setBrush(border_color)
                w = port_rect.width() / 3.5
                h = port_rect.height() / 3.5
            rect = QRectF(
                port_rect.center().x() - w / 2, port_rect.center().y() - h / 2, w, h
            )
            painter.drawEllipse(rect)
        painter.restore()

    def redraw_connected_pipes(self):
        if len(self.connected_pipes) == 0:
            return
        for node_id, pipe in self.connected_pipes.items():
            if self.port_type == "in":
                pipe.draw_path(self, pipe.output_port)
            elif self.port_type == "out":
                pipe.draw_path(pipe.input_port, self)

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemScenePositionHasChanged:
            self.redraw_connected_pipes()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self._hovered = True
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        super().hoverLeaveEvent(event)

    # --------------------------------------------------------------------------------------
    # Logic methods
    # --------------------------------------------------------------------------------------
    def to_dict(self):
        return {
            "name": self.name,
            "port_type": self.port_type,
            "multi_connection": self.multi_connection,
            "accepted_ports": self.accepted_ports,
        }

    def add_accepted_ports(self, ports):
        if isinstance(ports, list):
            self.accepted_ports.extend(ports)
        elif isinstance(ports, str):
            self._accepted_ports.append(ports)
        else:
            raise ValueError("Invalid port type")

    def connected(self, target_port):
        """Check if the specified port (port object, port name or port id) is connected
        to this port."""
        if isinstance(target_port, str):
            if target_port in [port.name for port in self.connected_ports]:
                return True
        elif isinstance(target_port, int):
            if target_port in [port.id for port in self.connected_ports]:
                return True
        elif isinstance(target_port, Port):
            if target_port in self.connected_ports:
                return True
        else:
            logging.warning(
                "Invalid port type for connection check "
                "(only port object, port name or port id accepted)."
            )
        return False

    def compatible(self, port, verbose=True):
        """Check if the specified port is compatible with this port."""
        # check if the ports are the same.
        if self is port:
            if verbose:
                logging.debug("Can't connect the same port.")
        # check if the ports are from the same node.
        elif self.node is port.node:
            if verbose:
                logging.debug("Can't connect ports from the same node.")
        # check if the ports are from the same type (can't connect input to input).
        elif self.port_type == port.port_type:
            if verbose:
                logging.debug("Can't connect the same port type.")
        # check if the ports are already connected.
        elif self.connected(port):
            if verbose:
                logging.debug("Ports are already connected.")
        # check if the ports are compatible.
        elif self.accepted_ports is not None and port.name not in self.accepted_ports:
            if verbose:
                logging.debug("Ports are not compatible.")
        else:
            if verbose:
                logging.debug("Ports are compatible.")
            return True
        return False

    def connect_to(self, target_port=None):
        """Create connection to the specified port and emits the
        :attr:`NodeGraph.port_connected` signal from the parent node graph.

        Args:
            target_port (Port): port object.
        """
        if target_port is None:
            for pipe in self.connected_pipes.values():
                pipe.delete()
            logging.debug("No target port specified.")
            return

        # validate accept connection.
        if not self.compatible(target_port):
            return

        # Remove existing connections from this port and the target port,
        # if not multi-connection.
        for port in [self, target_port]:
            if not port.multi_connection and len(port.connected_ports) > 0:
                for d_port in list(port.connected_ports):
                    port.disconnect_from(d_port)

        # Add to connected_ports
        for port, trg_port in [(self, target_port), (target_port, self)]:
            if trg_port not in port.connected_ports:
                port.connected_ports.append(trg_port)

        if self.port_type == "in":
            input_port = self
            output_port = target_port
        else:
            input_port = target_port
            output_port = self
        # Draw pipe
        if self.scene():
            pipe = Pipe(input_port, output_port)
            input_port.connected_pipes[output_port.id] = pipe
            output_port.connected_pipes[input_port.id] = pipe
            self.scene().addItem(pipe)
            pipe.draw_path(input_port, output_port)
            if self.node.isSelected() or target_port.node.isSelected():
                pipe.highlight()
            if not self.node.isVisible() or not target_port.node.isVisible():
                pipe.hide()
        else:
            logging.warning(
                f"Scene not found, could not draw pipe from "
                f"{self.name} to {target_port.name}."
            )

        # Emit Signal
        self.node.viewer.PortConnected.emit(input_port, output_port)

        self.update()
        target_port.update()
        logging.debug(
            f"Connected {self.node.name}/{self.name} to "
            f"{target_port.node.name}/{target_port.name}"
        )

    def disconnect_from(self, target_port=None):
        """Disconnect from the specified port and emits the
        :attr:`NodeGraph.port_disconnected` signal from the parent node graph.

        Args:
            target_port (NodeGrapchQt.Port): port object.
        """
        if not target_port:
            return

        # Remove ids from connected ports of this port and the target port.
        for port, trg_port in [(self, target_port), (target_port, self)]:
            port.connected_ports.remove(trg_port)

        # Remove the pipe connected to target_port
        rm_pipe = self.connected_pipes.pop(target_port.id, None)
        if rm_pipe is not None:
            rm_pipe.delete()

        # emit signal
        if self.port_type == "in":
            self.node.viewer.PortDisconnected.emit(self, target_port)
        else:
            self.node.viewer.PortDisconnected.emit(target_port, self)

        self.update()
        target_port.update()
        logging.debug(
            f"Disconnected {self.node.name}/{self.name} from "
            f"{target_port.node.name}/{target_port.name}"
        )

    def clear_connections(self):
        """Disconnect from all port connections and emit the
        :attr:`NodeGraph.port_disconnected` signals from the node graph."""
        # Copy to avoid iteration failure
        remove_ports = list(self.connected_ports)
        for port in remove_ports:
            self.disconnect_from(port)
