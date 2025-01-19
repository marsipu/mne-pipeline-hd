# -*- coding: utf-8 -*-
import logging
import math
from collections import OrderedDict

import qtpy

from mne_pipeline_hd.gui.node import nodes
from mne_pipeline_hd.gui.gui_utils import invert_rgb_color
from mne_pipeline_hd.gui.node.base_node import BaseNode
from mne_pipeline_hd.gui.node.node_defaults import defaults
from mne_pipeline_hd.gui.node.node_scene import NodeScene
from mne_pipeline_hd.gui.node.pipes import LivePipeItem, SlicerPipeItem, Pipe
from mne_pipeline_hd.gui.node.ports import Port
from qtpy.QtCore import QMimeData, QPointF, QPoint, QRectF, Qt, QRect, QSize, Signal
from qtpy.QtGui import QColor, QPainter, QPainterPath
from qtpy.QtWidgets import (
    QGraphicsView,
    QRubberBand,
    QGraphicsTextItem,
    QGraphicsPathItem,
)


class NodeViewer(QGraphicsView):
    """The NodeGraph displays the nodes and connections and manages them."""

    # ----------------------------------------------------------------------------------
    # Signals
    # ----------------------------------------------------------------------------------
    NodesCreated = Signal(list)
    NodesDeleted = Signal(list)
    NodeDoubleClicked = Signal(BaseNode)
    PortConnected = Signal(Port, Port)
    PortDisconnected = Signal(Port, Port)
    DataDropped = Signal(QMimeData, QPointF)

    MovedNodes = Signal(dict)
    ConnectionChanged = Signal(list, list)
    InsertNode = Signal(object, str, dict)
    NodeNameChanged = Signal(str, str)

    def __init__(self, ct, parent=None, debug_mode=False):
        super().__init__(parent)
        self.ct = ct
        self._debug_mode = debug_mode

        # attributes
        self._nodes = OrderedDict()
        self._pipe_layout = defaults["viewer"]["pipe_layout"]
        self._last_size = self.size()
        self._detached_port = None
        self._start_port = None
        self._origin_pos = None
        self._previous_pos = QPoint(int(self.width() / 2), int(self.height() / 2))
        self._prev_selection_nodes = []
        self._prev_selection_pipes = []
        self._node_positions = {}
        self.LMB_state = False
        self.RMB_state = False
        self.MMB_state = False
        self.COLLIDING_state = False

        # init QGraphicsView
        self.setScene(NodeScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
        self.setOptimizationFlag(
            QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing
        )
        self.setAcceptDrops(True)

        # set initial range
        self._scene_range = QRectF(0, 0, self.size().width(), self.size().height())
        self._update_scene()

        # initialize rubberband
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._rubber_band.isActive = False

        # initialize cursor text
        text_color = QColor(*invert_rgb_color(defaults["viewer"]["background_color"]))
        text_color.setAlpha(50)
        self._cursor_text = QGraphicsTextItem()
        self._cursor_text.setFlag(
            self._cursor_text.GraphicsItemFlag.ItemIsSelectable, False
        )
        self._cursor_text.setDefaultTextColor(text_color)
        self._cursor_text.setZValue(-2)
        font = self._cursor_text.font()
        font.setPointSize(7)
        self._cursor_text.setFont(font)
        self.scene().addItem(self._cursor_text)

        # initialize live pipe
        self._LIVE_PIPE = LivePipeItem()
        self._LIVE_PIPE.setVisible(False)
        self.scene().addItem(self._LIVE_PIPE)

        # initialize slicer pipe
        self._SLICER_PIPE = SlicerPipeItem()
        self._SLICER_PIPE.setVisible(False)
        self.scene().addItem(self._SLICER_PIPE)

        # initialize debug path
        self._debug_path = QGraphicsPathItem()
        self._debug_path.setZValue(1)
        pen = self._debug_path.pen()
        pen.setColor(QColor(255, 0, 0, 255))
        pen.setWidth(2)
        self._debug_path.setPen(pen)
        self._debug_path.setPath(QPainterPath())
        self.scene().addItem(self._debug_path)

    # ----------------------------------------------------------------------------------
    # Properties
    # ----------------------------------------------------------------------------------
    @property
    def nodes(self):
        """Return list of nodes in the node graph.

        Returns:
        --------
        nodes: OrderedDict
            The nodes are stored in an OrderedDict with the node id as the key.
        """
        return self._nodes

    @property
    def pipe_layout(self):
        """Return the pipe layout mode.

        Returns
        -------
        layout: str
            Pipe layout mode (either 'straight', 'curved', or 'angle').

        """
        return self._pipe_layout

    @pipe_layout.setter
    def pipe_layout(self, layout):
        """Set the pipe layout mode.

        Parameters
        ----------
        layout: str
            Pipe layout mode (either 'straight', 'curved', or 'angle').
        """
        if layout not in ["straight", "curved", "angle"]:
            logging.warning(
                f"{layout} is not a valid pipe layout, " f"defaulting to 'curved'."
            )
            layout = "curved"
        self._pipe_layout = layout

    # ----------------------------------------------------------------------------------
    # Logic methods
    # ----------------------------------------------------------------------------------
    def add_node(self, node):
        """
        Add a node to the node graph.

        See Also
        --------
        NodeGraph.registered_nodes : To list all node types

        Parameters
        ----------
        node : BaseNode
            The node to add to the node graph.

        """
        self.scene().addItem(node)
        self._nodes[node.id] = node

        # draw node (necessary to redraw after it is added to the scene)
        node.draw_node()

        return node

    def remove_node(self, node):
        """
        Remove a node from the node graph.

        Parameters
        ----------
        node : BaseNode
            Node instance to remove.
        """
        if node in self.scene().items():
            self.scene().removeItem(node)
        # Deliberately with room for KeyError to detect,
        # if nodes are not correctly added in the first place
        self.nodes.pop(node.id)

        node.delete()

    def create_node(self, node_info, **kwargs):
        """
        Create a node from the given class.

        Parameters
        ----------
        node_info: str or dict
            Can be a string to speficy the node class or a dictionary
            from node.to_dict().
        kwargs: dict
            Additional keyword arguments to pass into BaseNode.__init__()
            (replacing the values from the dictionary if provided).

        Returns
        -------
        node
            The created node.
        """
        if isinstance(node_info, dict):
            node_class = getattr(nodes, node_info["class"])
            for key in node_info:
                if key in kwargs:
                    node_info[key] = kwargs[key]
            node = node_class.from_dict(self.ct, node_info)
        elif isinstance(node_info, str):
            node_class = getattr(nodes, node_info)
            node = node_class(self.ct, **kwargs)
        else:
            raise ValueError("node_info must be a string or a dictionary.")
        self.add_node(node)

        return node

    def node(self, node_idx=None, node_name=None, node_id=None):
        """
        Get a node from the node graph based on either its index, name, or id.

        Parameters
        ----------
        node_idx : int, optional
            Index of the node in the node graph.
        node_name : str, optional
            Name of the node in the node graph.
        node_id : str, optional
            Unique identifier of the node in the node graph.

        Returns
        -------
        BaseNode
            The node that matches the provided index, name, or id. If multiple
            parameters are provided, the method will prioritize them in
            the following order: node_idx, node_name, node_id.
            If no parameters are provided or if no match is found,
            the method will return None.
        """
        if node_idx is not None:
            return list(self.nodes.values())[node_idx]
        elif node_name is not None:
            return [n for n in self.nodes.values() if n.name == node_name]
        elif node_id is not None:
            return self.nodes[node_id]

    def to_dict(self):
        viewer_dict = {node_id: node.to_dict() for node_id, node in self.nodes.items()}

        return viewer_dict

    def from_dict(self, viewer_dict):
        self.clear()
        # Create nodes
        for node_info in viewer_dict.values():
            self.create_node(node_info)
        # Continue: Initialize connections

    def clear(self):
        """
        Clear the node graph.
        """
        for node in list(self.nodes.values()):
            self.remove_node(node)

    # ----------------------------------------------------------------------------------
    # Qt methods
    # ----------------------------------------------------------------------------------
    def _set_viewer_zoom(self, value, sensitivity=None, pos=None):
        """
        Sets the zoom level.

        Args:
            value (float): zoom factor.
            sensitivity (float): zoom sensitivity.
            pos (QPoint): mapped position.
        """
        if pos:
            pos = self.mapToScene(pos)
        if sensitivity is None:
            scale = 1.001**value
            self.scale(scale, scale, pos)
            return

        if value == 0.0:
            return

        scale = (0.9 + sensitivity) if value < 0.0 else (1.1 - sensitivity)
        zoom = self.get_zoom()
        if defaults["viewer"]["zoom_min"] >= zoom:
            if scale == 0.9:
                return
        if defaults["viewer"]["zoom_max"] <= zoom:
            if scale == 1.1:
                return
        self.scale(scale, scale, pos)

    def _set_viewer_pan(self, pos_x, pos_y):
        """
        Set the viewer in panning mode.

        Args:
            pos_x (float): x pos.
            pos_y (float): y pos.
        """
        self._scene_range.adjust(pos_x, pos_y, pos_x, pos_y)
        self._update_scene()

    def scale(self, sx, sy, pos=None):
        scale = [sx, sx]
        center = pos or self._scene_range.center()
        w = self._scene_range.width() / scale[0]
        h = self._scene_range.height() / scale[1]
        self._scene_range = QRectF(
            center.x() - (center.x() - self._scene_range.left()) / scale[0],
            center.y() - (center.y() - self._scene_range.top()) / scale[1],
            w,
            h,
        )
        self._update_scene()

    def _update_scene(self):
        """
        Redraw the scene.
        """
        self.setSceneRect(self._scene_range)
        self.fitInView(self._scene_range, Qt.AspectRatioMode.KeepAspectRatio)

    def _combined_rect(self, nodes):
        """
        Returns a QRectF with the combined size of the provided node items.

        Args:
            nodes (list[AbstractNodeItem]): list of node qgraphics items.

        Returns:
            QRectF: combined rect
        """
        group = self.scene().createItemGroup(nodes)
        rect = group.boundingRect()
        self.scene().destroyItemGroup(group)
        return rect

    def _items_near(self, pos, width=20, height=20):
        """
        Filter node graph items from the specified position, width and
        height area.

        Args:
            pos (QPointF): scene pos.
            width (int): width area.
            height (int): height area.

        Returns:
            list: qgraphics items from the scene.
        """
        x, y = pos.x() - width, pos.y() - height
        rect = QRectF(x, y, width, height)
        items = []
        excl = [self._LIVE_PIPE, self._SLICER_PIPE]
        for item in self.scene().items(rect):
            if item in excl:
                continue
            items.append(item)
        return items

    # Reimplement events
    def resizeEvent(self, event):
        w, h = self.size().width(), self.size().height()
        if 0 in [w, h]:
            self.resize(self._last_size)
        delta = max(w / self._last_size.width(), h / self._last_size.height())
        self._set_viewer_zoom(delta)
        self._last_size = self.size()
        super().resizeEvent(event)

    def contextMenuEvent(self, event):
        # ToDo: reimplement context menu.
        pass

        return super().contextMenuEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.LMB_state = True
        elif event.button() == Qt.MouseButton.RightButton:
            self.RMB_state = True
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.MMB_state = True

        self._origin_pos = event.pos()
        self._previous_pos = event.pos()
        self._prev_selection_nodes, self._prev_selection_pipes = self.selected_items()

        # cursor pos.
        map_pos = self.mapToScene(event.pos())

        # debug path
        if self._debug_mode:
            if self.LMB_state:
                path = self._debug_path.path()
                path.moveTo(map_pos)
                self._debug_path.setPath(path)

        # pipe slicer enabled.
        if self.LMB_state and event.modifiers() == (
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier
        ):
            self._SLICER_PIPE.draw_path(map_pos, map_pos)
            self._SLICER_PIPE.setVisible(True)
            return

        # pan mode.
        if event.modifiers() == Qt.KeyboardModifier.AltModifier:
            return

        items = self._items_near(map_pos, 20, 20)
        nodes = [i for i in items if self.isnode(i)]

        if len(nodes) > 0:
            self.MMB_state = False

        # update the recorded node positions.
        selection = set([])
        selection.update(self.selected_nodes())
        self._node_positions.update({n: n.xy_pos for n in selection})

        # show selection marquee.
        if self.LMB_state and not items:
            rect = QRect(self._previous_pos, QSize())
            rect = rect.normalized()
            map_rect = self.mapToScene(rect).boundingRect()
            self.scene().update(map_rect)
            self._rubber_band.setGeometry(rect)
            self._rubber_band.isActive = True

        if not self._LIVE_PIPE.isVisible():
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.LMB_state = False
        elif event.button() == Qt.MouseButton.RightButton:
            self.RMB_state = False
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.MMB_state = False

        # hide pipe slicer.
        if self._SLICER_PIPE.isVisible():
            for i in self.scene().items(self._SLICER_PIPE.path()):
                if self.ispipe(i) and i != self._LIVE_PIPE:
                    i.input_port.disconnect_from(i.output_port)
            p = QPointF(0.0, 0.0)
            self._SLICER_PIPE.draw_path(p, p)
            self._SLICER_PIPE.setVisible(False)

        # hide selection marquee
        if self._rubber_band.isActive:
            self._rubber_band.isActive = False
            if self._rubber_band.isVisible():
                rect = self._rubber_band.rect()
                map_rect = self.mapToScene(rect).boundingRect()
                self._rubber_band.hide()
                self.scene().update(map_rect)
                return

        # find position changed nodes and emit signal.
        moved_nodes = {
            n: xy_pos
            for n, xy_pos in self._node_positions.items()
            if n.xy_pos != xy_pos
        }
        # only emit of node is not colliding with a pipe.
        if moved_nodes and not self.COLLIDING_state:
            self.MovedNodes.emit(moved_nodes)

        # reset recorded positions.
        self._node_positions = {}

        # emit signal if selected node collides with pipe.
        # Note: if collide state is true then only 1 node is selected.
        # ToDo: Implement colliding if necessary
        # nodes, pipes = self.selected_items()
        # if self.COLLIDING_state and nodes and pipes:
        #     self.InsertNode.emit(pipes[0], nodes[0].id, moved_nodes)

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        alt_modifier = event.modifiers() == Qt.KeyboardModifier.AltModifier
        if self._debug_mode:
            # Debug mouse
            if self.LMB_state:
                to_pos = self.mapToScene(event.pos())
                path = self._debug_path.path()
                path.lineTo(to_pos)
                self._debug_path.setPath(path)

        # Draw slicer
        if self.LMB_state and event.modifiers() == (
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier
        ):
            if self._SLICER_PIPE.isVisible():
                p1 = self._SLICER_PIPE.path().pointAtPercent(0)
                p2 = self.mapToScene(self._previous_pos)
                self._SLICER_PIPE.draw_path(p1, p2)
                self._SLICER_PIPE.show()
            self._previous_pos = event.pos()
            super().mouseMoveEvent(event)
            return

        # Pan view
        if self.MMB_state or (
            self.LMB_state and alt_modifier and not self._LIVE_PIPE.isVisible()
        ):
            previous_pos = self.mapToScene(self._previous_pos)
            current_pos = self.mapToScene(event.pos())
            delta = previous_pos - current_pos
            self._set_viewer_pan(delta.x(), delta.y())

        if self.LMB_state and self._rubber_band.isActive:
            rect = QRect(self._origin_pos, event.pos()).normalized()
            # if the rubber band is too small, do not show it.
            if max(rect.width(), rect.height()) > 5:
                if not self._rubber_band.isVisible():
                    self._rubber_band.show()
                map_rect = self.mapToScene(rect).boundingRect()
                path = QPainterPath()
                path.addRect(map_rect)
                self._rubber_band.setGeometry(rect)
                self.scene().setSelectionArea(
                    path, mode=Qt.ItemSelectionMode.IntersectsItemShape
                )
                self.scene().update(map_rect)

        elif self.LMB_state:
            self.COLLIDING_state = False
            nodes, pipes = self.selected_items()
            if len(nodes) == 1:
                node = nodes[0]
                [p.setSelected(False) for p in pipes]

                colliding_pipes = [
                    i for i in node.collidingItems() if self.ispipe(i) and i.isVisible()
                ]
                for pipe in colliding_pipes:
                    if not pipe.input_port:
                        continue
                    port_node_check = all(
                        [
                            pipe.input_port.node is not node,
                            pipe.output_port.node is not node,
                        ]
                    )
                    if port_node_check:
                        pipe.setSelected(True)
                        self.COLLIDING_state = True
                        break

        self._previous_pos = event.pos()
        super(NodeViewer, self).mouseMoveEvent(event)

    def wheelEvent(self, event):
        try:
            delta = event.delta()
        except AttributeError:
            # For PyQt5
            delta = event.angleDelta().y()
            if delta == 0:
                delta = event.angleDelta().x()
        self._set_viewer_zoom(delta, pos=event.pos())

    def dropEvent(self, event):
        pos = self.mapToScene(event.pos())
        event.setDropAction(Qt.DropAction.CopyAction)
        self.DataDropped.emit(event.mimeData(), QPointF(pos.x(), pos.y()))

    def dragEnterEvent(self, event):
        is_acceptable = any(
            [
                event.mimeData().hasFormat(i)
                for i in ["nodegraphqt/nodes", "text/plain", "text/uri-list"]
            ]
        )
        if is_acceptable:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        is_acceptable = any(
            [
                event.mimeData().hasFormat(i)
                for i in ["nodegraphqt/nodes", "text/plain", "text/uri-list"]
            ]
        )
        if is_acceptable:
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        event.ignore()

    def keyPressEvent(self, event):
        if self._LIVE_PIPE.isVisible():
            super(NodeViewer, self).keyPressEvent(event)
            return

        # show cursor text
        overlay_text = None
        self._cursor_text.setVisible(False)

        if (
            event.modifiers()
            == Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier
        ):
            overlay_text = "\n    ALT + SHIFT:\n    Pipe Slicer Enabled"
        if overlay_text:
            self._cursor_text.setPlainText(overlay_text)
            self._cursor_text.setPos(self.mapToScene(self._previous_pos))
            self._cursor_text.setVisible(True)

        super(NodeViewer, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        # hide and reset cursor text.
        self._cursor_text.setPlainText("")
        self._cursor_text.setVisible(False)

        super(NodeViewer, self).keyReleaseEvent(event)

    # ----------------------------------------------------------------------------------
    # Scene Events
    # ----------------------------------------------------------------------------------

    def sceneMouseMoveEvent(self, event):
        """
        triggered mouse move event for the scene.
         - redraw the live connection pipe.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent):
                The event handler from the QtWidgets.QGraphicsScene
        """
        if not self._LIVE_PIPE.isVisible():
            return
        if not self._start_port:
            return

        pos = event.scenePos()
        pointer_color = None
        for item in self.scene().items(pos):
            if not self.isport(item):
                continue

            x = item.boundingRect().width() / 2
            y = item.boundingRect().height() / 2
            pos = item.scenePos()
            pos.setX(pos.x() + x)
            pos.setY(pos.y() + y)
            if item == self._start_port:
                break
            pointer_color = defaults["pipes"]["highlight_color"]
            # ToDo: Accept implementation
            accept = True
            if not accept:
                pointer_color = [150, 60, 255]
                break

            if item.node == self._start_port.node:
                pointer_color = defaults["pipes"]["disabled_color"]
            elif item.port_type == self._start_port.port_type:
                pointer_color = defaults["pipes"]["disabled_color"]
            break

        self._LIVE_PIPE.draw_path(self._start_port, cursor_pos=pos, color=pointer_color)

    def sceneMousePressEvent(self, event):
        """
        triggered mouse press event for the scene (takes priority over viewer event).
         - detect selected pipe and start connection.

        Args:
            event (QtWidgets.QGraphicsScenePressEvent):
                The event handler from the QtWidgets.QGraphicsScene
        """
        # pipe slicer enabled.
        if event.modifiers() == (
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier
        ):
            return

        # viewer pan mode.
        if event.modifiers() == Qt.KeyboardModifier.AltModifier:
            return

        if self._LIVE_PIPE.isVisible():
            self.apply_live_connection(event)
            return

        pos = event.scenePos()
        items = self._items_near(pos, 5, 5)

        # filter from the selection stack in the following order
        # "node, port, pipe" this is to avoid selecting items under items.
        node, port, pipe = None, None, None
        for item in items:
            if self.isnode(item):
                node = item
            elif self.isport(item):
                port = item
            elif self.ispipe(item):
                pipe = item
            if any([node, port, pipe]):
                break

        if port:
            if not port.multi_connection and len(port.connected_ports) > 0:
                # ToDo: Might cause problems with multi-connections
                self._detached_port = port.connected_ports[0]
            self.start_live_connection(port)
            if not port.multi_connection:
                [p.delete() for p in port.connected_pipes.values()]
            return

        if node:
            node_items = [i for i in self._items_near(pos, 3, 3) if self.isnode(i)]

            # record the node positions at selection time.
            for n in node_items:
                self._node_positions[n] = n.xy_pos

        if pipe:
            if not self.LMB_state:
                return

            from_port = pipe.port_from_pos(pos, True)
            from_port.hovered = True

            attr = {
                "in": "input_port",
                "out": "output_port",
            }
            self._detached_port = getattr(pipe, attr[from_port.port_type])
            self.start_live_connection(from_port)
            self._LIVE_PIPE.draw_path(self._start_port, cursor_pos=pos)

            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                self._LIVE_PIPE.shift_selected = True
                return

            pipe.delete()

    def sceneMouseReleaseEvent(self, event):
        """
        triggered mouse release event for the scene.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent):
                The event handler from the QtWidgets.QGraphicsScene
        """
        if event.button() != Qt.MouseButton.MiddleButton:
            self.apply_live_connection(event)

    def apply_live_connection(self, event):
        """
        triggered mouse press/release event for the scene.
        - verifies the live connection pipe.
        - makes a connection pipe if valid.
        - emits the "connection changed" signal.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent):
                The event handler from the QtWidgets.QGraphicsScene
        """
        if not self._LIVE_PIPE.isVisible():
            return

        self._start_port.hovered = False

        # find the end port.
        end_port = None
        for item in self.scene().items(event.scenePos()):
            if self.isport(item):
                end_port = item
                break

        # if port disconnected from existing pipe.
        if end_port is None:
            if self._detached_port and not self._LIVE_PIPE.shift_selected:
                dist = math.hypot(
                    self._previous_pos.x() - self._origin_pos.x(),
                    self._previous_pos.y() - self._origin_pos.y(),
                )
                if dist <= 2.0:  # cursor pos threshold.
                    self._start_port.connect_to(self._detached_port)
                    self._detached_port = None
                else:
                    self._start_port.disconnect_from(self._detached_port)

            self._detached_port = None
            self.end_live_connection()
            return

        else:
            if self._start_port is end_port:
                return

        # constrain check
        compatible = self._start_port.compatible(end_port, verbose=False)

        # restore connection if ports are not compatible
        if not compatible:
            if self._detached_port:
                to_port = self._detached_port or end_port
                self._start_port.connect_to(to_port)
                self._detached_port = None
            self.end_live_connection()
            return

        # end connection if starting port is already connected.
        if self._start_port.multi_connection and self._start_port.connected(end_port):
            self._detached_port = None
            self.end_live_connection()
            logging.debug("Target Port is already connected.")
            return

        # disconnect target port from its connections if not multi connection.
        if not end_port.multi_connection and len(end_port.connected_ports) > 0:
            end_port.clear_connections()

        # Connect from detached port if available.
        if self._detached_port:
            self._start_port.disconnect_from(self._detached_port)

        # Make connection
        self._start_port.connect_to(end_port)

        self._detached_port = None
        self.end_live_connection()

    def start_live_connection(self, selected_port):
        """
        create new pipe for the connection.
        (show the live pipe visibility from the port following the cursor position)
        """
        if not selected_port:
            return
        self._start_port = selected_port
        if self._start_port.port_type == "in":
            self._LIVE_PIPE.input_port = self._start_port
        elif self._start_port == "out":
            self._LIVE_PIPE.output_port = self._start_port
        self._LIVE_PIPE.setVisible(True)
        self._LIVE_PIPE.draw_index_pointer(
            selected_port, self.mapToScene(self._origin_pos)
        )

    def end_live_connection(self):
        """
        delete live connection pipe and reset start port.
        (hides the pipe item used for drawing the live connection)
        """
        self._LIVE_PIPE.reset_path()
        self._LIVE_PIPE.setVisible(False)
        self._LIVE_PIPE.shift_selected = False
        self._start_port = None

    def isnode(self, item):
        """
        Check if the item is a node.

        Parameters
        ----------
        item: QGraphicsItem

        Returns
        -------
        result: bool
            True if the item is a node.
        """
        # For some reason, issubclass(item.__class__, BaseNode) does not work
        if item in self.nodes.values():
            return True
        return False

    def isport(self, item):
        """
        Check if the item is a port.

        Parameters
        ----------
        item: QGraphicsItem

        Returns
        -------
        result: bool
            True if the item is a port.
        """
        return isinstance(item, Port)

    def ispipe(self, item):
        """
        Check if the item is a pipe.

        Parameters
        ----------
        item: QGraphicsItem

        Returns
        -------
        result: bool
            True if the item is a pipe.
        """
        return isinstance(item, Pipe)

    def all_pipes(self):
        """
        Returns all pipe qgraphic items.

        Returns:
            list[PipeItem]: instances of pipe items.
        """
        return [i for i in self.scene().items() if self.ispipe(i)]

    def selected_nodes(self):
        """
        Returns selected node qgraphic items.

        Returns:
            list[AbstractNodeItem]: instances of node items.
        """
        return [i for i in self.scene().selectedItems() if self.isnode(i)]

    def selected_pipes(self):
        """
        Returns selected pipe qgraphic items.

        Returns:
            list[Pipe]: pipe items.
        """
        return [i for i in self.scene().selectedItems() if self.ispipe(i)]

    def selected_items(self):
        """
        Return selected graphic items in the scene.

        Returns:
            tuple(list[AbstractNodeItem], list[Pipe]):
                selected (node items, pipe items).
        """
        nodes = [i for i in self.scene().selectedItems() if self.isnode(i)]
        pipes = [i for i in self.scene().selectedItems() if self.ispipe(i)]

        return nodes, pipes

    def move_nodes(self, nodes, pos=None, offset=None):
        """
        Globally move specified nodes.

        Args:
            nodes (list[AbstractNodeItem]): node items.
            pos (tuple or list): custom x, y position.
            offset (tuple or list): x, y position offset.
        """
        group = self.scene().createItemGroup(nodes)
        group_rect = group.boundingRect()
        if pos:
            x, y = pos
        else:
            pos = self.mapToScene(self._previous_pos)
            x = pos.x() - group_rect.center().x()
            y = pos.y() - group_rect.center().y()
        if offset:
            x += offset[0]
            y += offset[1]
        group.setPos(x, y)
        self.scene().destroyItemGroup(group)

    def get_pipes_from_nodes(self, nodes=None):
        nodes = nodes or self.selected_nodes()
        if not nodes:
            return
        pipes = []
        for node in nodes:
            n_inputs = node.inputs if hasattr(node, "inputs") else []
            n_outputs = node.outputs if hasattr(node, "outputs") else []

            for port in n_inputs:
                for pipe in port.connected_pipes.values():
                    connected_node = pipe.output_port.node
                    if connected_node in nodes:
                        pipes.append(pipe)
            for port in n_outputs:
                for pipe in port.connected_pipes.values():
                    connected_node = pipe.input_port.node
                    if connected_node in nodes:
                        pipes.append(pipe)
        return pipes

    def center_selection(self, nodes=None):
        """
        Center on the given nodes or all nodes by default.

        Args:
            nodes (list[AbstractNodeItem]): a list of node items.
        """
        nodes = nodes or self.selected_nodes() or self.nodes.values()
        if not nodes:
            return

        rect = self._combined_rect(nodes)
        self._scene_range.translate(rect.center() - self._scene_range.center())
        self.setSceneRect(self._scene_range)

    def clear_selection(self):
        """
        Clear the selected items in the scene.
        """
        for node in self.nodes.values():
            node.setSelected(False)

    def reset_zoom(self, cent=None):
        """
        Reset the viewer zoom level.

        Args:
            cent (QtCore.QPoint): specified center.
        """
        self._scene_range = QRectF(0, 0, self.size().width(), self.size().height())
        if cent:
            self._scene_range.translate(cent - self._scene_range.center())
        self._update_scene()

    def get_zoom(self):
        """
        Returns the viewer zoom level.

        Returns:
            float: zoom level.
        """
        transform = self.transform()
        cur_scale = (transform.m11(), transform.m22())
        return float("{:0.2f}".format(cur_scale[0] - 1.0))

    def set_zoom(self, value=0.0):
        """
        Set the viewer zoom level.

        Args:
            value (float): zoom level
        """
        if value == 0.0:
            self.reset_zoom()
            return
        zoom = self.get_zoom()
        if zoom < 0.0:
            if not (
                defaults["viewer"]["zoom_min"] <= zoom <= defaults["viewer"]["zoom_max"]
            ):
                return
        else:
            if not (
                defaults["viewer"]["zoom_min"]
                <= value
                <= defaults["viewer"]["zoom_max"]
            ):
                return
        value = value - zoom
        self._set_viewer_zoom(value, 0.0)

    def zoom_to_nodes(self, nodes):
        self._scene_range = self._combined_rect(nodes)
        self._update_scene()

        if self.get_zoom() > 0.1:
            self.reset_zoom(self._scene_range.center())

    def fit_to_selection(self):
        """
        Sets the zoom level to fit selected nodes.
        If no nodes are selected then all nodes in the graph will be framed.
        """
        nodes = self.selected_nodes() or self.nodes.values()
        if not nodes:
            return
        self.zoom_to_nodes(nodes)

    def force_update(self):
        """
        Redraw the current node graph scene.
        """
        self._update_scene()

    def scene_rect(self):
        """
        Returns the scene rect size.

        Returns:
            list[float]: x, y, width, height
        """
        return [
            self._scene_range.x(),
            self._scene_range.y(),
            self._scene_range.width(),
            self._scene_range.height(),
        ]

    def set_scene_rect(self, rect):
        """
        Sets the scene rect and redraws the scene.

        Args:
            rect (list[float]): x, y, width, height
        """
        self._scene_range = QRectF(*rect)
        self._update_scene()

    def scene_center(self):
        """
        Get the center x,y pos from the scene.

        Returns:
            list[float]: x, y position.
        """
        cent = self._scene_range.center()
        return [cent.x(), cent.y()]

    def scene_cursor_pos(self):
        """
        Returns the cursor last position mapped to the scene.

        Returns:
            QtCore.QPoint: cursor position.
        """
        return self.mapToScene(self._previous_pos)

    def nodes_rect_center(self, nodes):
        """
        Get the center x,y pos from the specified nodes.

        Args:
            nodes (list[AbstractNodeItem]): list of node qgrphics items.

        Returns:
            list[float]: x, y position.
        """
        cent = self._combined_rect(nodes).center()
        return [cent.x(), cent.y()]

    def use_OpenGL(self):
        """
        Use QOpenGLWidget as the viewer.
        """
        if qtpy.PYQT5 or qtpy.PYSIDE2:
            from qtpy.QtWidgets import QOpenGLWidget
        else:
            from qtpy.QtOpenGLWidgets import QOpenGLWidget
        self.setViewport(QOpenGLWidget())

    def node_position_scene(self, **node_kwargs):
        node = self.node(**node_kwargs)
        scene_pos = node.scenePos() + node.boundingRect().center()

        return scene_pos

    def node_position_view(self, **node_kwargs):
        scene_pos = self.node_position_scene(**node_kwargs)
        view_pos = self.mapFromScene(scene_pos)

        return view_pos

    def port_position_scene(self, port_type, port, **node_kwargs):
        node = self.node(**node_kwargs)
        port = node.port(port_type, port)
        scene_pos = port.scenePos() + port.boundingRect().center()

        return scene_pos

    def port_position_view(self, port_type, port, **node_kwargs):
        scene_pos = self.port_position_scene(port_type, port, **node_kwargs)
        view_pos = self.mapFromScene(scene_pos)

        return view_pos

    # --------------------------------------------------------------------------------------
    # AutoLayout
    # --------------------------------------------------------------------------------------

    @staticmethod
    def _update_node_rank(node, nodes_rank, down_stream=True):
        """
        Recursive function for updating the node ranking.

        Args:
            node (NodeGraphQt.BaseNode): node to start from.
            nodes_rank (dict): node ranking object to be updated.
            down_stream (bool): true to rank down stram.
        """
        if down_stream:
            node_values = node.connected_output_nodes().values()
        else:
            node_values = node.connected_input_nodes().values()

        connected_nodes = set()
        for nds in node_values:
            connected_nodes.update(nds)

        rank = nodes_rank[node] + 1
        for n in connected_nodes:
            if n in nodes_rank:
                nodes_rank[n] = max(nodes_rank[n], rank)
            else:
                nodes_rank[n] = rank
            NodeViewer._update_node_rank(n, nodes_rank, down_stream)

    @staticmethod
    def _compute_node_rank(nodes, down_stream=True):
        """
        Compute the ranking of nodes.

        Args:
            nodes (list[NodeGraphQt.BaseNode]): nodes to start ranking from.
            down_stream (bool): true to compute down stream.

        Returns:
            dict: {NodeGraphQt.BaseNode: node_rank, ...}
        """
        nodes_rank = {}
        for node in nodes:
            nodes_rank[node] = 0
            NodeViewer._update_node_rank(node, nodes_rank, down_stream)
        return nodes_rank

    def auto_layout_nodes(self, nodes=None, down_stream=True, start_nodes=None):
        """
        Auto layout the nodes in the node graph.

        Note:
            If the node graph is acyclic then the ``start_nodes`` will need
            to be specified.

        Args:
            nodes (list[NodeGraphQt.BaseNode]): list of nodes to auto layout
                if nodes is None then all nodes is layed out.
            down_stream (bool): false to layout up stream.
            start_nodes (list[NodeGraphQt.BaseNode]):
                list of nodes to start the auto layout from (Optional).
        """
        nodes = nodes or self.nodes.values()

        start_nodes = start_nodes or []
        if down_stream:
            start_nodes += [
                n for n in nodes if not any(n.connected_input_nodes().values())
            ]
        else:
            start_nodes += [
                n for n in nodes if not any(n.connected_output_nodes().values())
            ]

        if not start_nodes:
            return

        nodes_center_0 = self.nodes_rect_center(nodes)

        nodes_rank = NodeViewer._compute_node_rank(start_nodes, down_stream)

        rank_map = {}
        for node, rank in nodes_rank.items():
            if rank in rank_map:
                rank_map[rank].append(node)
            else:
                rank_map[rank] = [node]

        current_x = 0
        node_height = 120
        for rank in sorted(range(len(rank_map)), reverse=not down_stream):
            ranked_nodes = rank_map[rank]
            max_width = max([node.width for node in ranked_nodes])
            current_x += max_width
            current_y = 0
            for idx, node in enumerate(ranked_nodes):
                dy = max(node_height, node.height)
                current_y += 0 if idx == 0 else dy
                node.setPos(current_x, current_y)
                current_y += dy * 0.5 + 10

            current_x += max_width * 0.5 + 100

        nodes_center_1 = self.nodes_rect_center(nodes)
        dx = nodes_center_0[0] - nodes_center_1[0]
        dy = nodes_center_0[1] - nodes_center_1[1]
        [n.setPos(n.x() + dx, n.y() + dy) for n in nodes]
