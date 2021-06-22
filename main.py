#version 1:创建一个空窗体
#version 2:创建一个带有菜单栏的窗体
#version 3:创建一个带有工具栏的窗体
#version 4:设置central组件
#version 5:为File按键添加打开图像行为QAction
#version 6:为Open按钮添加图像打开对话框触发行为:QFileDialog
#version 7:打开图像,显示在QScroll面板上
#version 8:打开图像,显示在QScroll面板上以外,右侧打开显示图像相关信息
#version 9:图像相关信息table:(1)图像名;(2)图像宽高;(3)图像编码;(4)图像深度;(5)图像数值类型;(6)图像类型
#version 10:图像状态栏显示坐标功能
#version 11:mouse cursor cross line tracking
#version 12:mouse cursor 跟随坐标
#version 13:绘图格式自定义配置:组件设置
#version 14:Rect轮廓编辑模式:添加透明色
#version 15:抽取矩形编辑类:Rect轮廓
#version 16:定义鼠标事件:轮廓可移动 鼠标靠近透明色
#version 17:编辑顶点 三种模式划分
#version 18:弹出标签框(图像class分类信息;编辑完成按钮;格式文件选项;截取功能) 轮廓编号i;图像内坐标XY信息 
#version 19:关闭时有标注轮廓:提示保存,生成编辑文件(Pascal Voc);简化初始化参数
#version 20:弹出编辑格式文件保存提示框QMessage;轮廓撤销,轮廓删减;关闭不保存
#version 21:鼠标接近,操作提示语;
#version 22:图像语义分割框(Poly);Rect & Poly类整合;XML & JSON
#version 23:载入标注文件(XML,JSON)
#version 24:设置pypi包;设置package打包
#version 25:添加图像拖拽功能;图像缩放功能

import os
import sys
import math

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from lib.support_formats import PascalVocWriter, JsonWriter

DISTANCE_LIMIT = 4
CREATING, MOVING, ADJUSTING = list(range(3))
SUPPORT_FMTS = ["Pascal Voc", "Yolo", "Json"]

class PointCalculator(object):
    @staticmethod
    def pointInsideRect(labelPoint, rect):
        startPoint, endPoint = rect
        return (startPoint.x()-labelPoint.x()) * (endPoint.x()-labelPoint.x()) <= 0 and \
                 (startPoint.y()-labelPoint.y()) * (endPoint.y()-labelPoint.y()) <= 0

    @staticmethod
    def pointInsidePolygon(labelPoint, poly):
        qpoly = QPolygon(poly)
        return qpoly.containsPoint(labelPoint, Qt.OddEvenFill)

    @staticmethod
    def euclidDis(labelPoint, disPoint):
        return math.hypot(labelPoint.x() - disPoint.x(),
                        labelPoint.y() - disPoint.y())

    @staticmethod
    def rectDis(labelPoint, rect):
        return min([abs(labelPoint.x()-rect[0].x()),
                    abs(labelPoint.x()-rect[1].x()),
                    abs(labelPoint.y()-rect[0].y()),
                    abs(labelPoint.y()-rect[1].y())])

    @staticmethod
    def polyDis(labelPoint, poly):
        return min([PointCalculator.euclidDis(labelPoint, polyPoint) for polyPoint in poly])

    @staticmethod
    def nearestRectVertex(labelPoint, rects):
        rect_index = -1
        nearPoint = None
        distance = -1
        
        for i, rect in enumerate(rects):
            x1, x2, y1, y2 = rect[0].x(), rect[1].x(), rect[0].y(), rect[1].y()
            for vertexPoint in [QPoint(x1, y1), QPoint(x1, y2), QPoint(x2, y1), QPoint(x2, y2)]:
                current_distance = PointCalculator.euclidDis(labelPoint, vertexPoint)
                if distance == -1 or distance > current_distance:
                    distance = current_distance
                    nearPoint = vertexPoint
                    rect_index = i

        if distance <= DISTANCE_LIMIT:
            return nearPoint, rect_index
        return None, None

    @staticmethod
    def nearestVertex(labelPoint, shapes):
        shape_index = -1
        vertex_index = -1
        nearPoint = None
        distance = -1
        
        for i, shape in enumerate(shapes):
            for j, vertexPoint in enumerate(shape):
                current_distance = PointCalculator.euclidDis(labelPoint, vertexPoint)
                if distance == -1 or distance > current_distance:
                    distance = current_distance
                    nearPoint = vertexPoint
                    shape_index = i
                    vertex_index = j

        if distance <= DISTANCE_LIMIT:
            return nearPoint, shape_index, vertex_index
        return None, None, None

    @staticmethod
    def getReferPoint(labelPoint, rect):
        xs = [rect[0].x(), rect[1].x()]
        ys = [rect[0].y(), rect[1].y()]
        xs.remove(labelPoint.x())
        ys.remove(labelPoint.y())
        return QPoint(xs[0], ys[0])

    @staticmethod
    def nearestRect(labelPoint, rects):
        index = -1
        distance = -1
        for i, rect in enumerate(rects):
            if PointCalculator.pointInsideRect(labelPoint, rect):
                distanceRect = PointCalculator.rectDis(labelPoint, rect)
                if distance == -1 or distance > distanceRect:
                    distance = distanceRect
                    index = i
        return index

    @staticmethod
    def nearestPoly(labelPoint, polys):
        index = -1
        distance = -1
        for i, poly in enumerate(polys):
            if PointCalculator.pointInsidePolygon(labelPoint, poly):
                distancePoly = PointCalculator.polyDis(labelPoint, poly)
                if distance == -1 or distance > distancePoly:
                    distance = distancePoly
                    index = i
        return index

class ShapeLabel(object):

    def __init__(self):
        super().__init__()
        self.currentShape = []
        self.editing_mode = None
        self.adjustStatus = False
        self.nearPoint = None
        self.near_shape_index = -1
        self.near_vertex_index = -1
        self.move_index = -1
        self.movePoint = None
        self.benchShape = []
        self.shapes = []
        self.classes = []

    def isAddPoint(self):
        return True

    def isAddShape(self):
        return True

    def addPoint(self, labelPoint):
        if self.isAddPoint():
            self.currentShape.append(labelPoint)

    def addShape(self):
        if self.isAddShape():
            self.shapes.append(self.currentShape)
            self.currentShape = []

    def createWithdrawal(self):
        if self.editing_mode == CREATING:
            if len(self.currentShape) > 0:
                self.currentShape.pop()

    def moveBench(self, labelPoint):
        if not self.benchShape:
            self.move_index = PointCalculator.nearestPoly(labelPoint, self.shapes)
            if self.move_index >= 0:
                self.movePoint = labelPoint
                self.benchShape = self.shapes[self.move_index]
        else:
            self.movePoint = None
            self.benchShape = None

    def moveUpdate(self, labelPoint):
        if self.move_index >= 0 and self.movePoint and self.benchShape:
            self.shapes[self.move_index] = \
                [labelPoint - self.movePoint + benchPoint for benchPoint in self.benchShape]

    def moveDelete(self):
        if self.editing_mode == MOVING:
            if self.move_index >= 0:
                self.shapes.pop(self.move_index)
                self.move_index = -1
        elif self.editing_mode == ADJUSTING and self.adjustStatus and self.nearPoint:
            adjust_shape = self.shapes[self.near_shape_index]
            adjust_shape.pop(self.near_vertex_index)
            self.shapes[self.near_shape_index] = adjust_shape
            self.adjustStatus = False

    def changeAdjustStatus(self):
        if not self.adjustStatus and self.nearPoint:
            self.adjustStatus = True
        elif self.adjustStatus:
            self.adjustStatus = False

    def adjustShape(self, labelPoint):
        if not self.adjustStatus:
            self.nearPoint, self.near_shape_index, self.near_vertex_index = PointCalculator.nearestVertex(labelPoint, self.shapes)
        else:
            if self.shapes and self.nearPoint:
                self.shapes[self.near_shape_index][self.near_vertex_index] = labelPoint

    def drawCreateShape(self, painter, labelPoint):
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.red, Qt.BDiagPattern))
        painter.drawPolyline(QPolygon(self.currentShape))
        if len(self.currentShape) > 0:
            painter.drawLine(self.currentShape[-1].x(), self.currentShape[-1].y(),
                            labelPoint.x(), labelPoint.y())

        painter.setBrush(QBrush(Qt.green, Qt.SolidPattern))
        for vertexPoint in self.currentShape:
            painter.drawEllipse(QPoint(vertexPoint.x(), vertexPoint.y()), 3, 3)
    
    def drawAdjustShape(self, painter):
        shape = self.shapes[self.near_shape_index]
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(0, 255, 0, 30), Qt.SolidPattern))
        painter.drawPolygon(QPolygon(shape))
        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.red, Qt.SolidPattern))
        for vertexPoint in shape:
            painter.drawRect(vertexPoint.x()-5, vertexPoint.y()-5, 10, 10)

class RectLabel(ShapeLabel):

    def __init__(self):
        ShapeLabel.__init__(self)
        self.referPoint = None

    def isAddShape(self):
        if len(self.currentShape) == 2:
            return True
        return False

    def moveBench(self, labelPoint):
        if not self.benchShape:
            self.move_index = PointCalculator.nearestRect(labelPoint, self.shapes)
            if self.move_index >= 0:
                self.movePoint = labelPoint
                self.benchShape = self.shapes[self.move_index]
        else:
            self.movePoint = None
            self.benchShape = None

    def drawCreateShape(self, painter, labelPoint):
        startPoint = None
        endPoint = None
        
        if len(self.currentShape) == 2:
            startPoint, endPoint = self.currentShape
        elif len(self.currentShape) == 1:
            startPoint = self.currentShape[0]

        if startPoint:
            painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
            painter.setBrush(QBrush(Qt.red, Qt.BDiagPattern))
            painter.drawRect(startPoint.x(), startPoint.y(), 
                            labelPoint.x()-startPoint.x(),
                            labelPoint.y()-startPoint.y())
            painter.drawLine(startPoint.x(), startPoint.y(), 
                            labelPoint.x(), labelPoint.y())
            painter.setBrush(QBrush(Qt.green, Qt.SolidPattern))
            painter.drawEllipse(QPoint(startPoint.x(), startPoint.y()), 3, 3)
        if endPoint:
            painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
            painter.drawEllipse(QPoint(endPoint.x(), endPoint.y()), 3, 3)

    def adjustShape(self, labelPoint):
        if not self.adjustStatus:
            self.nearPoint, self.near_shape_index = PointCalculator.nearestRectVertex(labelPoint, self.shapes)
            if self.shapes and self.nearPoint:
                self.referPoint = PointCalculator.getReferPoint(self.nearPoint, self.shapes[self.near_shape_index])
        else:
            if self.shapes and self.nearPoint:
                self.shapes[self.near_shape_index] = [labelPoint, self.referPoint]

    def drawAdjustShape(self, painter):
        startPoint, endPoint = self.shapes[self.near_shape_index]
        x1 = startPoint.x()
        y1 = startPoint.y()
        x2 = endPoint.x()
        y2 = endPoint.y()
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(0, 255, 0, 30), Qt.SolidPattern))
        painter.drawRect(x1, y1, x2-x1, y2-y1)
        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.red, Qt.SolidPattern))
        painter.drawRect(x1-5, y1-5, 10, 10)
        painter.drawRect(x2-5, y1-5, 10, 10)
        painter.drawRect(x1-5, y2-5, 10, 10)
        painter.drawRect(x2-5, y2-5, 10, 10)
    
    def paintRect(self, painter, labelPoint):
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        for i, [startPoint, endPoint] in enumerate(self.shapes):
            if PointCalculator.pointInsideRect(labelPoint, [startPoint, endPoint]):
                painter.setBrush(QBrush(QColor(0, 255, 0, 30), Qt.SolidPattern))
            else:
                painter.setBrush(QBrush(QColor(0, 255, 0, 0), Qt.SolidPattern))
            if i == self.move_index and self.editing_mode == MOVING:
                painter.setBrush(QBrush(QColor(0, 0, 255, 30), Qt.SolidPattern))
            if i != self.near_shape_index:
                painter.drawRect(startPoint.x(), startPoint.y(), 
                                endPoint.x()-startPoint.x(),
                                endPoint.y()-startPoint.y())

        painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.blue, Qt.SolidPattern))
        for i, [startPoint, endPoint] in enumerate(self.shapes):
            if i != self.near_shape_index:
                painter.drawEllipse(QPoint(startPoint.x(), startPoint.y()), 3, 3)
                painter.drawEllipse(QPoint(startPoint.x(), endPoint.y()), 3, 3)
                painter.drawEllipse(QPoint(endPoint.x(), endPoint.y()), 3, 3)
                painter.drawEllipse(QPoint(endPoint.x(), startPoint.y()), 3, 3)
        
        if self.editing_mode == CREATING:
            self.drawCreateShape(painter, labelPoint)
        
        if self.editing_mode == ADJUSTING and self.nearPoint:
            self.drawAdjustShape(painter)

class PolyLabel(ShapeLabel):

    def __init__(self):
        ShapeLabel.__init__(self)
        self.currentClosed = False

    def isClosePoint(self, labelPoint):
        return len(self.currentShape) >= 2 and PointCalculator.euclidDis(labelPoint, self.currentShape[0]) <= DISTANCE_LIMIT

    def addPoint(self, labelPoint):
        if not self.isClosePoint(labelPoint):
            self.currentShape.append(labelPoint)
        else:
            self.currentClosed = True

    def addShape(self):
        if self.currentClosed:
            self.shapes.append(self.currentShape)
            self.currentShape = []
            self.currentClosed = False

    def drawCreateShape(self, painter, labelPoint):
        super().drawCreateShape(painter, labelPoint)
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.red, Qt.BDiagPattern))
        if len(self.currentShape) >= 1 and self.isClosePoint(labelPoint):
            painter.drawLine(self.currentShape[0].x(), self.currentShape[0].y(),
                                labelPoint.x(), labelPoint.y())
            painter.setBrush(QBrush(Qt.green, Qt.SolidPattern))
            painter.drawEllipse(self.currentShape[0], 8, 8)

    def paintPoly(self, painter, labelPoint):
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        for i, shape in enumerate(self.shapes):
            if PointCalculator.pointInsidePolygon(labelPoint, shape):
                painter.setBrush(QBrush(QColor(0, 255, 0, 30), Qt.SolidPattern))
            else:
                painter.setBrush(QBrush(QColor(0, 255, 0, 0), Qt.SolidPattern))
            if i == self.move_index and self.editing_mode == MOVING:
                painter.setBrush(QBrush(QColor(0, 0, 255, 30), Qt.SolidPattern))
            if i != self.near_shape_index:
                painter.drawPolygon(QPolygon(shape))

        painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.blue, Qt.SolidPattern))
        for i, shape in enumerate(self.shapes):
            if i != self.near_shape_index:
                for vertexPoint in shape:
                    painter.drawEllipse(QPoint(vertexPoint.x(), vertexPoint.y()), 3, 3)
        
        if self.editing_mode == CREATING:
            self.drawCreateShape(painter, labelPoint)
        
        if self.editing_mode == ADJUSTING and self.nearPoint:
            self.drawAdjustShape(painter)

class LabelDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        self.difficult = False
        self.name_list = []
        self.completer = QCompleter(self.name_list)
        self.writerType = None
        self.edit = QLineEdit()
        self.edit.setCompleter(self.completer)

        layout = QVBoxLayout()
        layout.addWidget(self.edit)
        self.diffCheckbox = QCheckBox('difficult', self)
        self.diffCheckbox.clicked.connect(self.changeDiffCheck)
        layout.addWidget(self.diffCheckbox)
        self.formatCombobox = QComboBox()
        for fmt in SUPPORT_FMTS:
            self.formatCombobox.addItem(fmt)
        self.formatCombobox.currentTextChanged.connect(self.changeWriter)
        self.writerType = SUPPORT_FMTS[0]
        layout.addWidget(self.formatCombobox)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def changeDiffCheck(self):
        if self.diffCheckbox.isChecked():
            self.difficult = True
        else:
            self.difficult = False

    def changeWriter(self, text):
        self.writerType = text

    def update(self, text):
        self.name_list.append(text)
        self.completer.model().setStringList(self.name_list)

    def popUp(self, text=''):
        self.edit.setText(text)
        self.edit.setSelection(0, len(text))
        self.edit.setFocus(Qt.PopupFocusReason)
        return self.edit.text() if self.exec_() else None

class ImageLabel(QLabel):

    def __init__(self):
        super().__init__()
        self.tracking = False
        self.shape_mode = None
        self.editLabel = None
        self.labelDialog = LabelDialog(self)

        self.scale = 1
        self.labelPoint = QPoint()
        self.imagePoint = QPoint()

        self.image = QImage()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        self.withdrawalShortcut = QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.withdrawalShape)
        self.deleteShortcut = QShortcut(QKeySequence(Qt.Key_Delete), self, activated=self.deleteShape)

    def withdrawalShape(self):
        if self.editLabel:
            self.editLabel.createWithdrawal()
    
    def deleteShape(self):
        if self.editLabel:
            self.editLabel.moveDelete()
    
    def checkImageRange(self, pos):
        return pos.x() >= 0 and pos.x() < self.image.width() * self.scale and pos.y() >= 0 and \
            pos.y() < self.image.height() * self.scale

    def offset_to_center(self):
        s = self.scale
        area = super().size()
        w, h = self.image.width() * s, self.image.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QPointF(x, y)

    def image_pos(self, point):
        return point / self.scale - self.offset_to_center()

    def canvas_pos(self, point):
        return (point + self.offset_to_center()) * self.scale

    def getImageRect(self):
        pos = self.canvas_pos(QPoint(0, 0))
        return pos.x(), pos.y(), self.image.width() * self.scale, self.image.height() * self.scale

    def drawTrackingLine(self, painter):
        _, _, w0, h0 = self.getImageRect()
        hl1 = self.canvas_pos(QPoint(0, self.imagePoint.y()))
        hl2 = self.canvas_pos(QPoint(w0, self.imagePoint.y()))
        vl1 = self.canvas_pos(QPoint(self.imagePoint.x(), 0))
        vl2 = self.canvas_pos(QPoint(self.imagePoint.x(), h0))
        painter.drawLine(hl1.x(), hl1.y(), hl2.x(), hl2.y())
        painter.drawLine(vl1.x(), vl1.y(), vl2.x(), vl2.y())

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.image.width() and self.checkImageRange(self.imagePoint):
            painter = QPainter(self)
            if self.tracking:
                painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
                self.drawTrackingLine(painter)
                painter.drawText(QRect(self.labelPoint.x(), self.labelPoint.y(), 80, -60), 
                                Qt.AlignCenter, "(%d, %d)" % (self.imagePoint.x(), self.imagePoint.y()))
            if self.shape_mode == "Rect":
                if not self.editLabel:
                    self.editLabel = RectLabel()
                    self.parent().window().createRadiobox.setEnabled(True)
                    self.parent().window().moveRadiobox.setEnabled(True)
                    self.parent().window().adjustRadiobox.setEnabled(True)
                    self.parent().window().createRadiobox.setChecked(True)
                    self.parent().window().polyRadio.setEnabled(False)
                self.labelDialog.formatCombobox.setCurrentIndex(0)
                self.editLabel.paintRect(painter, self.labelPoint)
            elif self.shape_mode == "Poly":
                if not self.editLabel:
                    self.editLabel = PolyLabel()
                    self.parent().window().createRadiobox.setEnabled(True)
                    self.parent().window().moveRadiobox.setEnabled(True)
                    self.parent().window().adjustRadiobox.setEnabled(True)
                    self.parent().window().createRadiobox.setChecked(True)
                    self.parent().window().rectRadio.setEnabled(False)
                self.labelDialog.formatCombobox.setCurrentIndex(2)
                self.editLabel.paintPoly(painter, self.labelPoint)

        self.update()

    def mousePressEvent(self, event):
        self.labelPoint = event.pos()
        self.imagePoint = self.image_pos(self.labelPoint)
        if self.shape_mode == "Rect" and self.editLabel:
            if self.editLabel.editing_mode == CREATING:
                self.editLabel.addPoint(self.labelPoint)
            elif self.editLabel.editing_mode == MOVING:
                self.editLabel.moveBench(self.labelPoint)
            elif self.editLabel.editing_mode == ADJUSTING:
                self.editLabel.changeAdjustStatus()
        elif self.shape_mode == "Poly" and self.editLabel:
            if self.editLabel.editing_mode == CREATING:
                self.editLabel.addPoint(self.labelPoint)
            elif self.editLabel.editing_mode == MOVING:
                self.editLabel.moveBench(self.labelPoint)
            elif self.editLabel.editing_mode == ADJUSTING:
                self.editLabel.changeAdjustStatus()

        super().mousePressEvent(event)
        self.update()

    def mouseMoveEvent(self, event):
        self.labelPoint = event.pos()
        self.imagePoint = self.image_pos(self.labelPoint)
        if self.image.width() and self.checkImageRange(self.imagePoint):
            self.parent().window().status.showMessage("X: %d Y: %d" % (self.imagePoint.x(), self.imagePoint.y()))
        else:
            self.parent().window().status.showMessage("")
        if self.shape_mode == "Rect" and self.editLabel:
            if self.editLabel.editing_mode == MOVING:
                self.editLabel.moveUpdate(self.labelPoint)
            elif self.editLabel.editing_mode == ADJUSTING:
                self.editLabel.adjustShape(self.labelPoint)
        if self.shape_mode == "Poly" and self.editLabel:
            if self.editLabel.editing_mode == MOVING:
                self.editLabel.moveUpdate(self.labelPoint)
            elif self.editLabel.editing_mode == ADJUSTING:
                self.editLabel.adjustShape(self.labelPoint)
                
        super().mouseMoveEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        self.labelPoint = event.pos()
        self.imagePoint = self.image_pos(self.labelPoint)
        if self.shape_mode == "Rect" and self.editLabel:
            if self.editLabel.editing_mode == CREATING:
                if len(self.editLabel.currentShape) == 2:
                    text = self.labelDialog.popUp()
                    self.editLabel.addShape()
                    if not text or len(text) == 0:
                        self.editLabel.shapes.pop()
                    else:
                        self.editLabel.classes.append(text)
                        self.labelDialog.update(text)
        elif self.shape_mode == "Poly" and self.editLabel:
            if self.editLabel.editing_mode == CREATING:
                if self.editLabel.isClosePoint(self.labelPoint):
                    text = self.labelDialog.popUp()
                    self.editLabel.addShape()
                    if not text or len(text) == 0:
                        self.editLabel.shapes.pop()
                    else:
                        self.editLabel.classes.append(text)
                        self.labelDialog.update(text)

        super().mouseReleaseEvent(event)
        self.update()

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.fileName = None
        self.setMouseTracking(False)
        self.setMenuBar()
        self.setToolBar()
        self.setScrollArea()
        self.setPropertyDock()
        self.setTrackingDock()
        self.setStatusBar()
        self.resize(800, 600)

    def setMenuBar(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        openAction = QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.openImageDialog)
        saveAction = QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.saveLabelDialog)
        fileMenu.addAction(openAction)
        fileMenu.addAction(saveAction)

    def setToolBar(self):
        self.toolbar = self.addToolBar('')
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

    def setScrollArea(self):
        scroll = QScrollArea()
        self.imageLabel = ImageLabel()
        scroll.setWidget(self.imageLabel)
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)
        scroll.setVisible(True)

    def setPropertyDock(self):
        self.propertyDock = QDockWidget("Image Properties", self)
        self.tableView = QTableView()
        self.model = QStandardItemModel(4, 2)
        self.model.setHorizontalHeaderLabels(['Property', 'Value'])
        self.tableView.setModel(self.model)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableView.setAlternatingRowColors(True)
        self.nameCombox = QComboBox()
        self.nameCombox.addItem("File Name(including path)")
        self.nameCombox.addItem("File Name(pure name)")
        self.nameCombox.addItem("Directory Name")
        self.nameText = QLabel()
        item21 = QStandardItem("Image Width")
        item31 = QStandardItem("Image Height")
        item41 = QStandardItem("Image Depth")
        self.tableView.setIndexWidget(self.model.index(0, 0), self.nameCombox)
        self.tableView.setIndexWidget(self.model.index(0, 1), self.nameText)
        self.model.setItem(1, 0, item21)
        self.model.setItem(2, 0, item31)
        self.model.setItem(3, 0, item41)
        self.propertyDock.setWidget(self.tableView)
        self.addDockWidget(Qt.RightDockWidgetArea, self.propertyDock)

    def setTrackingDock(self):
        self.trackingDock = QDockWidget("Image Tracking", self)
        self.trackingWidget = QWidget()
        whole_layout = QVBoxLayout()

        trackCheckbox = QCheckBox('Tracking', self)
        trackCheckbox.clicked.connect(self.changeTrackingMode)
        whole_layout.addWidget(trackCheckbox)

        operationGroup = QGroupBox('Operate Mode:', self)
        operation_layout = QVBoxLayout()

        self.createRadiobox = QRadioButton('Creating', self)
        self.createRadiobox.toggled.connect(self.changeEditMode)
        self.createRadiobox.setEnabled(False)
        operation_layout.addWidget(self.createRadiobox)

        self.moveRadiobox = QRadioButton('Moving', self)
        self.moveRadiobox.toggled.connect(self.changeEditMode)
        self.moveRadiobox.setEnabled(False)
        operation_layout.addWidget(self.moveRadiobox)

        self.adjustRadiobox = QRadioButton('Adjusting', self)
        self.adjustRadiobox.toggled.connect(self.changeEditMode)
        self.adjustRadiobox.setEnabled(False)
        operation_layout.addWidget(self.adjustRadiobox)

        operationGroup.setLayout(operation_layout)
        whole_layout.addWidget(operationGroup)
        
        shapeGroup = QGroupBox('Shape Mode:', self)
        shape_layout = QVBoxLayout()
        self.rectRadio = QRadioButton('Rect', self)
        self.rectRadio.clicked.connect(lambda checked, text=self.rectRadio.text():self.changeShapeMode(checked, text))
        shape_layout.addWidget(self.rectRadio)
        
        self.polyRadio = QRadioButton('Poly', self)
        self.polyRadio.clicked.connect(lambda checked, text=self.polyRadio.text():self.changeShapeMode(checked, text))
        shape_layout.addWidget(self.polyRadio)
        
        shapeGroup.setLayout(shape_layout)
        whole_layout.addWidget(shapeGroup)
        self.trackingWidget.setLayout(whole_layout)

        self.trackingDock.setWidget(self.trackingWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.trackingDock)

    def changeTrackingMode(self, checked):
        if checked:
            self.imageLabel.tracking = True
            return
        self.imageLabel.tracking = False

    def changeEditMode(self, checked):
        if self.createRadiobox.isChecked():
            if self.imageLabel.editLabel:
                self.imageLabel.editLabel.editing_mode = CREATING
        elif self.moveRadiobox.isChecked():
            if self.imageLabel.editLabel:
                self.imageLabel.editLabel.editing_mode = MOVING
        elif self.adjustRadiobox.isChecked():
            if self.imageLabel.editLabel:
                self.imageLabel.editLabel.editing_mode = ADJUSTING

    def changeShapeMode(self, checked, text):
        self.imageLabel.shape_mode = text

    def setStatusBar(self):
        self.status = self.statusBar()

    def openImageDialog(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "All Files (*)", options=options)
        if fileName:
            self.fileName = fileName
            self.imageLabel.image = QImage(fileName)
            if self.imageLabel.image.isNull():
                QMessageBox.information(self, "Warning", "Cannot load %s." % fileName)
                return

            self.imageLabel.setPixmap(QPixmap.fromImage(self.imageLabel.image))
            self.imageLabel.adjustSize()
            self.setTable()

    def saveLabelDialog(self):
        options = QFileDialog.Options()
        default_name = None
        if self.fileName and self.imageLabel and \
            self.imageLabel.shape_mode == "Rect" and \
            self.imageLabel.labelDialog.writerType == SUPPORT_FMTS[0]:
            default_name = self.fileName.split(".")[0] + ".xml"
        elif self.fileName and self.imageLabel and \
            self.imageLabel.shape_mode == "Poly" and \
            self.imageLabel.labelDialog.writerType == SUPPORT_FMTS[2]:
            default_name = self.fileName.split(".")[0] + ".json"

        if default_name:
            name, _ = QFileDialog.getSaveFileName(self, "Save File", default_name, "All Files (*)", options=options)
            if name:
                self.saveLabel(name)

    def getFileName(self):
        path, fn = os.path.split(self.fileName)
        return {"File Name(including path)": self.fileName,
                "File Name(pure name)": fn,
                "Directory Name": path}

    def setTable(self):
        item22 = QStandardItem("{}".format(self.imageLabel.image.width()))
        item32 = QStandardItem("{}".format(self.imageLabel.image.height()))
        item42 = QStandardItem("{}".format(self.imageLabel.image.depth()))
        self.nameText.setText(self.getFileName()[str(self.nameCombox.currentText())])
        self.nameCombox.activated[str].connect(self.changeNameText)
        self.model.setItem(1, 1, item22)
        self.model.setItem(2, 1, item32)
        self.model.setItem(3, 1, item42)

        if not self.propertyDock.isVisible():
            self.propertyDock.show()

    def changeNameText(self, text):
        self.nameText.setText(self.getFileName()[text])

    def saveLabel(self, name):
        if self.imageLabel.editLabel and len(self.imageLabel.editLabel.classes) > 0:
            folder_path = os.path.dirname(self.fileName)
            folder_name = os.path.split(folder_path)[-1]
            file_name = os.path.basename(self.fileName)
            shape = [self.imageLabel.image.height(), 
                    self.imageLabel.image.width(),
                    1 if self.imageLabel.image.isGrayscale() else 3]

            if self.imageLabel.shape_mode == "Rect" and\
                self.imageLabel.labelDialog.writerType == SUPPORT_FMTS[0]:
                writer = PascalVocWriter(folder_name, file_name, shape,
                                        local_img_path=self.fileName)
                difficult = self.imageLabel.labelDialog.difficult
                for className, rectPoint in zip(self.imageLabel.editLabel.classes, 
                                                self.imageLabel.editLabel.shapes):
                    startP, endP = rectPoint
                    startP = self.imageLabel.image_pos(startP)
                    endP = self.imageLabel.image_pos(endP)
                    xmin, xmax = sorted([int(startP.x()), int(endP.x())])
                    ymin, ymax = sorted([int(startP.y()), int(endP.y())])
                    writer.add_bnd_box(xmin, ymin, xmax, ymax, className, difficult)
                
                writer.save(target_file=name)
            elif self.imageLabel.shape_mode == "Poly" and\
                self.imageLabel.labelDialog.writerType == SUPPORT_FMTS[2]:
                writer = JsonWriter(folder_name, file_name, shape,
                                        local_img_path=self.fileName)
                
                shape_list = []
                for className, shapePoint in zip(self.imageLabel.editLabel.classes, 
                                                self.imageLabel.editLabel.shapes):
                    shape_dict = {}
                    shapePoints = []
                    for vertexPoint in shapePoint:
                        imagePoint = self.imageLabel.image_pos(vertexPoint)
                        shapePoints.append([imagePoint.x(), imagePoint.y()])
                    shape_dict["label"] = className
                    shape_dict["points"] = shapePoints
                    shape_dict["group_id"] = writer.group_id
                    shape_dict["shape_type"] = writer.shape_type
                    shape_dict["flags"] = writer.flags
                    shape_list.append(shape_dict)

                writer.save(shape_list, name)

    def closeEvent(self, event):
        result = QMessageBox.question(self,
                      "Save before exit",
                      "Would you like to save the label format?",
                      QMessageBox.Yes| QMessageBox.No)
        event.ignore()

        if result == QMessageBox.Yes:
            self.saveLabelDialog()

        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PanyImage")
    win = MainWindow()
    win.show()
    app.exec_()