# -*- coding: utf-8 -*-
import logging
import math
from collections import OrderedDict

import qtpy
from mne_pipeline_hd.gui.gui_utils import invert_rgb_color
from mne_pipeline_hd.gui.node.base_node import BaseNode
from mne_pipeline_hd.gui.node.node_defaults import defaults
from mne_pipeline_hd.gui.node.node_scene import NodeScene
from mne_pipeline_hd.gui.node.pipes import LivePipeItem, SlicerPipeItem, Pipe
from mne_pipeline_hd.gui.node.ports import Port
from qtpy.QtCore import QMimeData, QPointF, QPoint, QRectF, Qt, QRect, QSize, Signal
from qtpy.QtGui import QColor, QPainter, QPainterPath
from qtpy.QtWidgets import QGraphicsView, QRubberBand, QGraphicsTextItem


class NodeViewer(QGraphicsView):
    """The NodeGraph displays the nodes and connections and manages them."""

    # ----------------------------------------------------------------------------------
    # Signals
    # ----------------------------------------------------------------------------------
    NodesCreated = Signal(list)
    NodesDeleted = Signal(list)
    NodeSelected = Signal(BaseNode)
    NodeSelectionChanged = Signal(list, list)
    NodeDoubleClicked = Signal(BaseNode)
    PortConnected = Signal(Port, Port)
    PortDisconnected = Signal(Port, Port)
    DataDropped = Signal(QMimeData, QPointF)

    MovedNodes = Signal(dict)
    ConnectionSliced = Signal(list)
    ConnectionChanged = Signal(list, list)
    InsertNode = Signal(object, str, dict)
    NodeNameChanged = Signal(str, str)

    def __init__(self, ct, parent=None):
        super().__init__(parent)
        self.ct = ct

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
        self.ALT_state = False
        self.CTRL_state = False
        self.SHIFT_state = False
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

        # connect signals
        self.ConnectionSliced.connect(self.on_connection_sliced)
        self.ConnectionChanged.connect(self.on_connection_changed)

    # ----------------------------------------------------------------------------------
    # Properties
    # ----------------------------------------------------------------------------------
    @property
    def nodes(self):
        """Return list of nodes in the node graph.

        Returns:
        --------
        nodes: list
            List of nodes in the node graph.

        Notes:
        ------
            The nodes are stored in an OrderedDict in self._nodes with the node id as the key.
        """
        return list(self._nodes.values())

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
        if not isinstance(node, BaseNode):
            logging.error(f"NodeViewer.remove_node: {node} is not a BaseNode instance.")

        if node in self.scene().items():
            self.scene().removeItem(node)
        if node.id in self.nodes:
            del self.nodes[node.id]

        node.delete()

    def create_node(self, node_class):
        """
        Create a node from the given class.

        Parameters
        ----------
        node_class
            The node class to create.

        Returns
        -------
        node
            The created node.
        """
        node = node_class(self.ct)
        self.add_node(node)

        return node

    def on_connection_changed(self, disconnected, connected):
        for start_port, end_port in disconnected:
            start_port.disconnect(end_port)
        for start_port, end_port in connected:
            start_port.connect(end_port)

    def on_connection_sliced(self, ports):
        for input_port, output_port in ports:
            input_port.disconnect(output_port)

    def to_dict(self):
        # ToDo: Implement this
        graph_dict = {"nodes": dict(), "connections": dict()}

        return graph_dict

    def from_dict(self, graph_dict):
        # ToDo: Implement this
        for node_id, node_data in graph_dict["nodes"].items():
            node = self.add_node(node_data["type"])
            node.from_dict(node_data)

        for conn_id, conn_data in graph_dict["connections"].items():
            start_port = self.nodes[conn_data["start_node"]].outputs[
                conn_data["start_port"]
            ]
            end_port = self.nodes[conn_data["end_node"]].inputs[conn_data["end_port"]]
            self.establish_connection(start_port, end_port)

    def get_pipe_layout(self):
        """
        Returns the pipe layout mode.

        Returns:
            int: pipe layout mode.
        """
        return self._pipe_layout

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

    def _items_near(self, pos, item_type=None, width=20, height=20):
        """
        Filter node graph items from the specified position, width and
        height area.

        Args:
            pos (QPoint): scene pos.
            item_type: filter item type. (optional)
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
            if not item_type or isinstance(item, item_type):
                items.append(item)
        return items

    def _on_pipes_sliced(self, path):
        """
        Triggered when the slicer pipe is active

        Args:
            path (QPainterPath): slicer path.
        """
        ports = []
        for i in self.scene().items(path):
            if isinstance(i, Pipe) and i != self._LIVE_PIPE:
                if any([i.input_port.locked, i.output_port.locked]):
                    continue
                ports.append([i.input_port, i.output_port])
        self.ConnectionSliced.emit(ports)

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
        (self._prev_selection_nodes, self._prev_selection_pipes) = self.selected_items()

        # cursor pos.
        map_pos = self.mapToScene(event.pos())

        # pipe slicer enabled.
        slicer_mode = all([self.ALT_state, self.SHIFT_state, self.LMB_state])
        if slicer_mode:
            self._SLICER_PIPE.draw_path(map_pos, map_pos)
            self._SLICER_PIPE.setVisible(True)
            return

        # pan mode.
        if self.ALT_state:
            return

        items = self._items_near(map_pos, None, 20, 20)
        pipes = []
        nodes = []
        for itm in items:
            if isinstance(itm, Pipe):
                pipes.append(itm)
            elif isinstance(itm, BaseNode):
                nodes.append(itm)

        if len(nodes) > 0:
            self.MMB_state = False

        # record the node selection as "self.selected_nodes()" is not updated
        # here on the mouse press event.
        selection = set([])

        if self.LMB_state:
            # toggle extend node selection.
            if self.SHIFT_state:
                for node in nodes:
                    node.selected = not node.selected
                    if node.selected:
                        selection.add(node)
            # unselected nodes with the "ctrl" key.
            elif self.CTRL_state:
                for node in nodes:
                    node.selected = False
            # if no modifier keys then add to selection set.
            else:
                for node in nodes:
                    if node.selected:
                        selection.add(node)

        selection.update(self.selected_nodes())

        # update the recorded node positions.
        self._node_positions.update({n: n.xy_pos for n in selection})

        # show selection marquee.
        if self.LMB_state and not items:
            rect = QRect(self._previous_pos, QSize())
            rect = rect.normalized()
            map_rect = self.mapToScene(rect).boundingRect()
            self.scene().update(map_rect)
            self._rubber_band.setGeometry(rect)
            self._rubber_band.isActive = True

        # stop here so we don't select a node.
        # (ctrl modifier can be used for something else in future.)
        if self.CTRL_state:
            return

        # allow new live pipe with the shift modifier on port that allow
        # for multi connection.
        if self.SHIFT_state:
            if pipes:
                pipes[0].reset()
                port = pipes[0].port_from_pos(map_pos, reverse=True)
                if not port.locked and port.multi_connection:
                    self._cursor_text.setPlainText("")
                    self._cursor_text.setVisible(False)
                    self.start_live_connection(port)

            # return here as the default behaviour unselects nodes with
            # the shift modifier.
            return

        if not self._LIVE_PIPE.isVisible():
            super(NodeViewer, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.LMB_state = False
        elif event.button() == Qt.MouseButton.RightButton:
            self.RMB_state = False
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.MMB_state = False

        # hide pipe slicer.
        if self._SLICER_PIPE.isVisible():
            self._on_pipes_sliced(self._SLICER_PIPE.path())
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

                rect = QRect(self._origin_pos, event.pos()).normalized()
                rect_items = self.scene().items(self.mapToScene(rect).boundingRect())
                node_ids = []
                for item in rect_items:
                    if isinstance(item, BaseNode):
                        node_ids.append(item.id)

                # emit the node selection signals.
                if node_ids:
                    prev_ids = [
                        n.id for n in self._prev_selection_nodes if not n.selected
                    ]
                    self.NodeSelected.emit(node_ids[0])
                    self.NodeSelectionChanged.emit(node_ids, prev_ids)

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
        nodes, pipes = self.selected_items()
        if self.COLLIDING_state and nodes and pipes:
            self.InsertNode.emit(pipes[0], nodes[0].id, moved_nodes)

        # emit node selection changed signal.
        prev_ids = [n.id for n in self._prev_selection_nodes if not n.selected]
        node_ids = [n.id for n in nodes if n not in self._prev_selection_nodes]
        self.NodeSelectionChanged.emit(node_ids, prev_ids)

        super(NodeViewer, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.ALT_state and self.SHIFT_state:
            if self.LMB_state and self._SLICER_PIPE.isVisible():
                p1 = self._SLICER_PIPE.path().pointAtPercent(0)
                p2 = self.mapToScene(self._previous_pos)
                self._SLICER_PIPE.draw_path(p1, p2)
                self._SLICER_PIPE.show()
            self._previous_pos = event.pos()
            super(NodeViewer, self).mouseMoveEvent(event)
            return

        if self.MMB_state and self.ALT_state:
            pos_x = event.x() - self._previous_pos.x()
            zoom = 0.1 if pos_x > 0 else -0.1
            self._set_viewer_zoom(zoom, 0.05, pos=event.pos())
        elif self.MMB_state or (self.LMB_state and self.ALT_state):
            previous_pos = self.mapToScene(self._previous_pos)
            current_pos = self.mapToScene(event.pos())
            delta = previous_pos - current_pos
            self._set_viewer_pan(delta.x(), delta.y())

        if not self.ALT_state:
            if self.SHIFT_state or self.CTRL_state:
                if not self._LIVE_PIPE.isVisible():
                    self._cursor_text.setPos(self.mapToScene(event.pos()))

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

                if self.SHIFT_state or self.CTRL_state:
                    nodes, pipes = self.selected_items()

                    for node in self._prev_selection_nodes:
                        node.selected = True

                    if self.CTRL_state:
                        for pipe in pipes:
                            pipe.setSelected(False)
                        for node in nodes:
                            node.selected = False

        elif self.LMB_state:
            self.COLLIDING_state = False
            nodes, pipes = self.selected_items()
            if len(nodes) == 1:
                node = nodes[0]
                [p.setSelected(False) for p in pipes]

                colliding_pipes = [
                    i
                    for i in node.collidingItems()
                    if isinstance(i, Pipe) and i.isVisible()
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
        """
        Key press event re-implemented to update the states for attributes:
        - ALT_state
        - CTRL_state
        - SHIFT_state

        Args:
            event (QKeyEvent): key event.
        """
        self.ALT_state = event.modifiers() == Qt.KeyboardModifier.AltModifier
        self.CTRL_state = event.modifiers() == Qt.KeyboardModifier.ControlModifier
        self.SHIFT_state = event.modifiers() == Qt.KeyboardModifier.ShiftModifier

        if event.modifiers() == (
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier
        ):
            self.ALT_state = True
            self.SHIFT_state = True

        if self._LIVE_PIPE.isVisible():
            super(NodeViewer, self).keyPressEvent(event)
            return

        # show cursor text
        overlay_text = None
        self._cursor_text.setVisible(False)
        if not self.ALT_state:
            if self.SHIFT_state:
                overlay_text = "\n    SHIFT:\n    Toggle/Extend Selection"
            elif self.CTRL_state:
                overlay_text = "\n    CTRL:\n    Deselect Nodes"
        elif self.ALT_state and self.SHIFT_state:
            overlay_text = "\n    ALT + SHIFT:\n    Pipe Slicer Enabled"
        if overlay_text:
            self._cursor_text.setPlainText(overlay_text)
            self._cursor_text.setPos(self.mapToScene(self._previous_pos))
            self._cursor_text.setVisible(True)

        super(NodeViewer, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """
        Key release event re-implemented to update the states for attributes:
        - ALT_state
        - CTRL_state
        - SHIFT_state

        Args:
            event (QKeyEvent): key event.
        """
        self.ALT_state = event.modifiers() == Qt.KeyboardModifier.AltModifier
        self.CTRL_state = event.modifiers() == Qt.KeyboardModifier.ControlModifier
        self.SHIFT_state = event.modifiers() == Qt.KeyboardModifier.ShiftModifier
        super(NodeViewer, self).keyReleaseEvent(event)

        # hide and reset cursor text.
        self._cursor_text.setPlainText("")
        self._cursor_text.setVisible(False)

    # --- scene events ---

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
            if not isinstance(item, Port):
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
         - remap Shift and Ctrl modifier.

        Args:
            event (QtWidgets.QGraphicsScenePressEvent):
                The event handler from the QtWidgets.QGraphicsScene
        """
        # pipe slicer enabled.
        if self.ALT_state and self.SHIFT_state:
            return

        # viewer pan mode.
        if self.ALT_state:
            return

        if self._LIVE_PIPE.isVisible():
            self.apply_live_connection(event)
            return

        pos = event.scenePos()
        items = self._items_near(pos, None, 5, 5)

        # filter from the selection stack in the following order
        # "node, port, pipe" this is to avoid selecting items under items.
        node, port, pipe = None, None, None
        for item in items:
            if isinstance(item, BaseNode):
                node = item
            elif isinstance(item, Port):
                port = item
            elif isinstance(item, Pipe):
                pipe = item
            if any([node, port, pipe]):
                break

        if port:
            if not port.multi_connection and port.connected_ports:
                self._detached_port = port.connected_ports[0]
            self.start_live_connection(port)
            if not port.multi_connection:
                [p.delete() for p in port.connected_pipes]
            return

        if node:
            node_items = self._items_near(pos, BaseNode, 3, 3)

            # record the node positions at selection time.
            for n in node_items:
                self._node_positions[n] = n.xy_pos

            # emit selected node id with LMB.
            if event.button() == Qt.MouseButton.LeftButton:
                self.NodeSelected.emit(node.id)
            return

        if pipe:
            if not self.LMB_state:
                return

            from_port = pipe.port_from_pos(pos, True)

            if from_port.locked:
                return

            from_port.hovered = True

            attr = {
                "in": "input_port",
                "out": "output_port",
            }
            self._detached_port = getattr(pipe, attr[from_port.port_type])
            self.start_live_connection(from_port)
            self._LIVE_PIPE.draw_path(self._start_port, cursor_pos=pos)

            if self.SHIFT_state:
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
            if isinstance(item, Port):
                end_port = item
                break

        connected = []
        disconnected = []

        # if port disconnected from existing pipe.
        if end_port is None:
            if self._detached_port and not self._LIVE_PIPE.shift_selected:
                dist = math.hypot(
                    self._previous_pos.x() - self._origin_pos.x(),
                    self._previous_pos.y() - self._origin_pos.y(),
                )
                if dist <= 2.0:  # cursor pos threshold.
                    self.establish_connection(self._start_port, self._detached_port)
                    self._detached_port = None
                else:
                    disconnected.append((self._start_port, self._detached_port))
                    self.ConnectionChanged.emit(disconnected, connected)

            self._detached_port = None
            self.end_live_connection()
            return

        else:
            if self._start_port is end_port:
                return

        # constrain check
        compatible = self._start_port.compatible(end_port)

        # restore connection check.
        restore_connection = any(
            [
                # if same port type.
                end_port.port_type == self._start_port.port_type,
                # if end port is the start port.
                end_port == self._start_port,
                # if detached port is the end port.
                self._detached_port == end_port,
                # if a port has a accept port type constrain.
                not compatible,
            ]
        )
        if restore_connection:
            if self._detached_port:
                to_port = self._detached_port or end_port
                self.establish_connection(self._start_port, to_port)
                self._detached_port = None
            self.end_live_connection()
            return

        # end connection if starting port is already connected.
        if (
            self._start_port.multi_connection
            and self._start_port in end_port.connected_ports
        ):
            self._detached_port = None
            self.end_live_connection()
            return

        # make connection.
        if not end_port.multi_connection and end_port.connected_ports:
            dettached_end = end_port.connected_ports[0]
            disconnected.append((end_port, dettached_end))

        if self._detached_port:
            disconnected.append((self._start_port, self._detached_port))

        connected.append((self._start_port, end_port))

        self.ConnectionChanged.emit(disconnected, connected)

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

    def establish_connection(self, start_port, end_port):
        """
        establish a new pipe connection.
        (adds a new pipe item to draw between 2 ports)
        """
        pipe = Pipe(start_port, end_port)
        self.scene().addItem(pipe)
        if start_port.node.selected or end_port.node.selected:
            pipe.highlight()
        if not start_port.node.isVisible() or not end_port.node.isVisible():
            pipe.hide()

    def all_pipes(self):
        """
        Returns all pipe qgraphic items.

        Returns:
            list[PipeItem]: instances of pipe items.
        """
        excl = [self._LIVE_PIPE, self._SLICER_PIPE]
        return [
            i for i in self.scene().items() if isinstance(i, Pipe) and i not in excl
        ]

    def all_nodes(self):
        """
        Returns all node qgraphic items.

        Returns:
            list[AbstractNodeItem]: instances of node items.
        """
        return [i for i in self.scene().items() if isinstance(i, BaseNode)]

    def selected_nodes(self):
        """
        Returns selected node qgraphic items.

        Returns:
            list[AbstractNodeItem]: instances of node items.
        """
        return [i for i in self.scene().selectedItems() if isinstance(i, BaseNode)]

    def selected_pipes(self):
        """
        Returns selected pipe qgraphic items.

        Returns:
            list[Pipe]: pipe items.
        """
        pipes = [i for i in self.scene().selectedItems() if isinstance(i, Pipe)]
        return pipes

    def selected_items(self):
        """
        Return selected graphic items in the scene.

        Returns:
            tuple(list[AbstractNodeItem], list[Pipe]):
                selected (node items, pipe items).
        """
        nodes = []
        pipes = []
        for item in self.scene().selectedItems():
            if isinstance(item, BaseNode):
                nodes.append(item)
            elif isinstance(item, Pipe):
                pipes.append(item)
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
                for pipe in port.connected_pipes:
                    connected_node = pipe.output_port.node
                    if connected_node in nodes:
                        pipes.append(pipe)
            for port in n_outputs:
                for pipe in port.connected_pipes:
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
        if not nodes:
            if self.selected_nodes():
                nodes = self.selected_nodes()
            elif self.all_nodes():
                nodes = self.all_nodes()
            if not nodes:
                return

        rect = self._combined_rect(nodes)
        self._scene_range.translate(rect.center() - self._scene_range.center())
        self.setSceneRect(self._scene_range)

    def clear_selection(self):
        """
        Clear the selected items in the scene.
        """
        for node in self.nodes:
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
        nodes = self.selected_nodes() or self.all_nodes()
        if not nodes:
            return
        self.zoom_to_nodes([n.view for n in nodes])

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

    def clear_key_state(self):
        """
        Resets the Ctrl, Shift, Alt modifiers key states.
        """
        self.CTRL_state = False
        self.SHIFT_state = False
        self.ALT_state = False

    def use_OpenGL(self):
        """
        Use QOpenGLWidget as the viewer.
        """
        if qtpy.PYQT5 or qtpy.PYSIDE2:
            from qtpy.QtWidgets import QOpenGLWidget
        else:
            from qtpy.QtOpenGLWidgets import QOpenGLWidget
        self.setViewport(QOpenGLWidget())

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
        for nodes in node_values:
            connected_nodes.update(nodes)

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
        nodes = nodes or self.all_nodes()

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

        node_views = [n.view for n in nodes]
        nodes_center_0 = self.nodes_rect_center(node_views)

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
            max_width = max([node.view.width for node in ranked_nodes])
            current_x += max_width
            current_y = 0
            for idx, node in enumerate(ranked_nodes):
                dy = max(node_height, node.view.height)
                current_y += 0 if idx == 0 else dy
                node.set_pos(current_x, current_y)
                current_y += dy * 0.5 + 10

            current_x += max_width * 0.5 + 100

        nodes_center_1 = self.nodes_rect_center(node_views)
        dx = nodes_center_0[0] - nodes_center_1[0]
        dy = nodes_center_0[1] - nodes_center_1[1]
        [n.set_pos(n.x_pos() + dx, n.y_pos() + dy) for n in nodes]
