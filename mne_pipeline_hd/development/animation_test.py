# -*- coding: utf-8 -*-
import sys
from qtpy.QtWidgets import (
    QApplication,
    QGraphicsPathItem,
    QGraphicsView,
    QGraphicsScene,
)
from qtpy.QtGui import QPen, QColor, QPainterPath
from qtpy.QtCore import Qt, QVariantAnimation


class Edge(QGraphicsPathItem):
    def __init__(self):
        super().__init__()
        self.setPen(QPen(Qt.white, 5, Qt.SolidLine))

        self.animation = QVariantAnimation()
        self.animation.setLoopCount(-1)
        self.animation.valueChanged.connect(self.handle_valueChanged)
        self.animation.setStartValue(QColor("blue"))
        self.animation.setKeyValueAt(0.25, QColor("green"))
        self.animation.setKeyValueAt(0.5, QColor("yellow"))
        self.animation.setKeyValueAt(0.75, QColor("red"))
        self.animation.setEndValue(QColor("blue"))
        self.animation.setDuration(2000)

    def start_animation(self):
        self.animation.start()

    def handle_valueChanged(self, value):
        pen = self.pen()
        pen.setColor(value)
        self.setPen(pen)


app = QApplication(sys.argv)
viewer = QGraphicsView()
scene = QGraphicsScene()
viewer.setScene(scene)
edge = Edge()
scene.addItem(edge)
path = QPainterPath()
path.moveTo(0, 0)
path.lineTo(100, 100)
edge.setPath(path)
edge.start_animation()
viewer.show()

sys.exit(app.exec())
