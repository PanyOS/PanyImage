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
#version 20:弹出编辑格式文件保存提示框QMessage;轮廓撤销,轮廓删减;
#version 21:鼠标接近,操作提示语;保存状态修复
#version 22:图像语义分割框(Poly);Rect & Poly类整合;XML & JSON
#version 23:载入标注文件(XML,JSON)
#version 24:设置package打包
#version 25:添加图像拖拽功能;图像缩放功能

import os
import sys
import math

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from lib.support_formats import FormatReader, PascalVocWriter, JsonWriter

DISTANCE_LIMIT = 4
CREATING, MOVING, ADJUSTING = list(range(3))
SUPPORT_FMTS = ["Pascal Voc", "Yolo", "Json"]
MIN_SCALE = 0.5
MAX_SCALE = 2.0

class PointCalculator(object):
    @staticmethod
    def pointInsideRect(imagePoint, rect):
        startPoint, endPoint = rect
        return (startPoint.x()-imagePoint.x()) * (endPoint.x()-imagePoint.x()) <= 0 and \
                 (startPoint.y()-imagePoint.y()) * (endPoint.y()-imagePoint.y()) <= 0

    @staticmethod
    def pointInsidePolygon(imagePoint, poly):
        qpoly = QPolygon(poly)
        return qpoly.containsPoint(imagePoint, Qt.OddEvenFill)

    @staticmethod
    def euclidDis(imagePoint, disPoint):
        return math.hypot(imagePoint.x() - disPoint.x(),
                        imagePoint.y() - disPoint.y())

    @staticmethod
    def rectDis(imagePoint, rect):
        return min([abs(imagePoint.x()-rect[0].x()),
                    abs(imagePoint.x()-rect[1].x()),
                    abs(imagePoint.y()-rect[0].y()),
                    abs(imagePoint.y()-rect[1].y())])

    @staticmethod
    def polyDis(imagePoint, poly):
        return min([PointCalculator.euclidDis(imagePoint, polyPoint) for polyPoint in poly])

    @staticmethod
    def nearestRectVertex(imagePoint, rects):
        rect_index = -1
        nearPoint = None
        distance = -1
        
        for i, rect in enumerate(rects):
            x1, x2, y1, y2 = rect[0].x(), rect[1].x(), rect[0].y(), rect[1].y()
            for vertexPoint in [QPoint(x1, y1), QPoint(x1, y2), QPoint(x2, y1), QPoint(x2, y2)]:
                current_distance = PointCalculator.euclidDis(imagePoint, vertexPoint)
                if distance == -1 or distance > current_distance:
                    distance = current_distance
                    nearPoint = vertexPoint
                    rect_index = i

        if distance <= DISTANCE_LIMIT:
            return nearPoint, rect_index
        return None, None

    @staticmethod
    def nearestVertex(imagePoint, shapes):
        shape_index = -1
        vertex_index = -1
        nearPoint = None
        distance = -1
        
        for i, shape in enumerate(shapes):
            for j, vertexPoint in enumerate(shape):
                current_distance = PointCalculator.euclidDis(imagePoint, vertexPoint)
                if distance == -1 or distance > current_distance:
                    distance = current_distance
                    nearPoint = vertexPoint
                    shape_index = i
                    vertex_index = j

        if distance <= DISTANCE_LIMIT:
            return nearPoint, shape_index, vertex_index
        return None, None, None

    @staticmethod
    def getReferPoint(imagePoint, rect):
        x, y = imagePoint.x(), imagePoint.y()
        x1, x2 = rect[0].x(), rect[1].x()
        y1, y2 = rect[0].y(), rect[1].y()
        nx = x1 if abs(x-x1) > abs(x-x2) else x2
        ny = y1 if abs(y-y1) > abs(y-y2) else y2
        return QPoint(nx, ny)

    @staticmethod
    def nearestRect(imagePoint, rects):
        index = -1
        distance = -1
        for i, rect in enumerate(rects):
            if PointCalculator.pointInsideRect(imagePoint, rect):
                distanceRect = PointCalculator.rectDis(imagePoint, rect)
                if distance == -1 or distance > distanceRect:
                    distance = distanceRect
                    index = i
        return index

    @staticmethod
    def nearestPoly(imagePoint, polys):
        index = -1
        distance = -1
        for i, poly in enumerate(polys):
            if PointCalculator.pointInsidePolygon(imagePoint, poly):
                distancePoly = PointCalculator.polyDis(imagePoint, poly)
                if distance == -1 or distance > distancePoly:
                    distance = distancePoly
                    index = i
        return index

class ShapeLabel(object):

    def __init__(self):
        super().__init__()
        # 存放当前轮廓的轮廓点
        self.currentShape = []
        self.editing_mode = None
        # Adjusting模式下的Adjusting状态;单个编辑点;编辑轮廓索引;编辑点索引
        self.adjustStatus = False
        self.nearPoint = None
        self.near_shape_index = -1
        self.near_vertex_index = -1
        # Moving模式下的轮廓索引;基准点
        self.move_index = -1
        self.movePoint = None
        self.benchShape = []
        # 轮廓及轮廓类别
        self.shapes = []
        self.classes = []

    def isAddPoint(self):
        return True

    def isAddShape(self):
        return True

    def addPoint(self, imagePoint):
        if self.isAddPoint():
            self.currentShape.append(imagePoint)

    def addShape(self):
        if self.isAddShape():
            self.shapes.append(self.currentShape)
            self.currentShape = []

    def clearShapes(self):
        self.shapes.clear()
        self.classes.clear()

    def createWithdrawal(self):
        if self.editing_mode == CREATING:
            if len(self.currentShape) > 0:
                self.currentShape.pop()

    def moveBench(self, imagePoint):
        if not self.benchShape:
            self.move_index = PointCalculator.nearestPoly(imagePoint, self.shapes)
            if self.move_index >= 0:
                self.movePoint = imagePoint
                self.benchShape = self.shapes[self.move_index]
        else:
            self.movePoint = None
            self.benchShape = None

    def moveUpdate(self, imagePoint):
        if self.move_index >= 0 and self.movePoint and self.benchShape:
            self.shapes[self.move_index] = \
                [imagePoint - self.movePoint + benchPoint for benchPoint in self.benchShape]

    def changeAdjustStatus(self):
        if not self.adjustStatus and self.nearPoint:
            self.adjustStatus = True
        elif self.adjustStatus:
            self.adjustStatus = False

    def adjustShape(self, imagePoint):
        if not self.adjustStatus:
            self.nearPoint, self.near_shape_index, self.near_vertex_index = PointCalculator.nearestVertex(imagePoint, self.shapes)
        else:
            if self.shapes and self.nearPoint:
                self.shapes[self.near_shape_index][self.near_vertex_index] = imagePoint

class RectLabel(ShapeLabel):

    def __init__(self):
        ShapeLabel.__init__(self)
        self.referPoint = None

    def isAddShape(self):
        if len(self.currentShape) == 2:
            return True
        return False

    def moveBench(self, imagePoint):
        if not self.benchShape:
            self.move_index = PointCalculator.nearestRect(imagePoint, self.shapes)
            if self.move_index >= 0:
                self.movePoint = imagePoint
                self.benchShape = self.shapes[self.move_index]
        else:
            self.movePoint = None
            self.benchShape = None

    def adjustShape(self, imagePoint):
        if not self.adjustStatus:
            self.nearPoint, self.near_shape_index = PointCalculator.nearestRectVertex(imagePoint, self.shapes)
            if self.shapes and self.nearPoint:
                self.referPoint = PointCalculator.getReferPoint(self.nearPoint, self.shapes[self.near_shape_index])
        else:
            if self.shapes and self.nearPoint:
                self.shapes[self.near_shape_index] = [imagePoint, self.referPoint]

class PolyLabel(ShapeLabel):

    def __init__(self):
        ShapeLabel.__init__(self)
        self.currentClosed = False

    def isClosePoint(self, imagePoint):
        return len(self.currentShape) >= 2 and PointCalculator.euclidDis(imagePoint, self.currentShape[0]) <= DISTANCE_LIMIT

    def addPoint(self, imagePoint):
        if not self.isClosePoint(imagePoint):
            self.currentShape.append(imagePoint)
        else:
            self.currentClosed = True

    def addShape(self):
        if self.currentClosed:
            self.shapes.append(self.currentShape)
            self.currentShape = []
            self.currentClosed = False

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
        self.setAcceptDrops(True)

        self.tracking = False
        self.openStatus = False
        self.shape_mode = None
        self.editLabel = None
        self.labelDialog = LabelDialog(self)

        self.scale = 1
        self.delta_scale = 0.1
        self.labelPoint = QPoint()
        self.imagePoint = QPoint()

        self.image = QImage()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        self.withdrawalShortcut = QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.withdrawalShape)
        self.deleteShortcut = QShortcut(QKeySequence(Qt.Key_Delete), self, activated=self.deleteShape)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            localPath = event.mimeData().urls()[0].toLocalFile()
            self.parent().window().openImageFile(localPath)

    def resetStatus(self):
        self.tracking = False
        self.openStatus = False
        self.shape_mode = None
        self.editLabel = None

        self.scale = 1
        self.delta_scale = 0.1
        self.labelPoint = QPoint()
        self.imagePoint = QPoint()
        self.image = QImage()
    
    def withdrawalShape(self):
        if self.editLabel:
            self.editLabel.createWithdrawal()
    
    def deleteShape(self):
        if self.editLabel:
            if self.editLabel.editing_mode == MOVING:
                if self.editLabel.move_index >= 0:
                    self.editLabel.shapes.pop(self.editLabel.move_index)
                    self.editLabel.classes.pop(self.editLabel.move_index)
                    self.parent().window().shape_list.takeItem(self.editLabel.move_index)
                    self.editLabel.move_index = -1
            elif self.editLabel.editing_mode == ADJUSTING and self.editLabel.adjustStatus and self.editLabel.nearPoint:
                adjust_shape = self.editLabel.shapes[self.editLabel.near_shape_index]
                adjust_shape.pop(self.editLabel.near_vertex_index)
                self.editLabel.shapes[self.editLabel.near_shape_index] = adjust_shape
                self.editLabel.adjustStatus = False

    def loadLabel(self, labelName):
        data_dict = None
        if labelName and labelName.endswith(".xml"):
            data_dict = FormatReader.load_xml(labelName)
            data_dict['ext'] = ".xml"
        elif labelName and labelName.endswith(".json"):
            data_dict = FormatReader.load_json(labelName)
            data_dict['ext'] = ".json"
        return data_dict

    def loadShapes(self, data_dict):
        if data_dict and data_dict['ext'] == ".xml":
            for label, points, _, _, _ in data_dict['shapes']:
                x1, y1 = points[0]
                x2, y2 = points[2]
                self.editLabel.classes.append(label)
                self.editLabel.shapes.append([QPoint(x1, y1), QPoint(x2, y2)])
                self.parent().window().addShapeItem(label)
        elif data_dict and data_dict['ext'] == ".json":
            for shape_dict in data_dict['shapes']:
                self.editLabel.classes.append(shape_dict["label"])
                shape = []
                for x, y in shape_dict["points"]:
                    shape.append(QPoint(x, y))
                self.editLabel.shapes.append(shape)
                self.parent().window().addShapeItem(shape_dict["label"])

    def checkNullImage(self):
        return self.image.isNull()
    
    def checkImageRange(self, pos):
        return pos.x() >= 0 and pos.x() < self.image.width() and pos.y() >= 0 and \
            pos.y() < self.image.height()
                
    def resizeImage(self):
        pixmap = QPixmap.fromImage(self.image)
        scaled_pixmap = pixmap.scaled(self.scale * pixmap.size())
        self.setPixmap(scaled_pixmap)
        self.adjustSize()
    
    def zoomIn(self):
        if not self.checkNullImage():
            new_scale = self.scale + self.delta_scale
            if new_scale <= MAX_SCALE:
                self.scale = new_scale
                self.labelPoint = self.canvas_pos(self.imagePoint)
                self.resizeImage()

    def zoomOut(self):
        if not self.checkNullImage():
            new_scale = self.scale - self.delta_scale
            if new_scale >= MIN_SCALE:
                self.scale = new_scale
                self.labelPoint = self.canvas_pos(self.imagePoint)
                self.resizeImage()

    def offset_to_center(self):
        s = self.scale
        area = super().size()
        w, h = self.image.width() * s, self.image.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QPoint(x, y)

    def image_pos(self, point):
        return point / self.scale - self.offset_to_center()

    def canvas_pos(self, point):
        return (point + self.offset_to_center()) * self.scale

    def canvas_shape(self, shape):
        return [self.canvas_pos(imagePoint) for imagePoint in shape]

    def getImageRect(self):
        pos = self.canvas_pos(QPoint(0, 0))
        return pos.x(), pos.y(), self.image.width(), self.image.height()

    def drawTrackingLine(self, painter):
        _, _, w0, h0 = self.getImageRect()
        painterpath = QPainterPath()
        painterpath.moveTo(self.canvas_pos(QPoint(0, self.imagePoint.y())))
        painterpath.lineTo(self.canvas_pos(QPoint(w0, self.imagePoint.y())))
        painterpath.moveTo(self.canvas_pos(QPoint(self.imagePoint.x(), 0)))
        painterpath.lineTo(self.canvas_pos(QPoint(self.imagePoint.x(), h0)))
        painter.drawPath(painterpath)

    def drawCreateRect(self, painter):
        startPoint = None
        endPoint = None
        
        if len(self.editLabel.currentShape) == 2:
            startPoint, endPoint = self.canvas_shape(self.editLabel.currentShape)
        elif len(self.editLabel.currentShape) == 1:
            startPoint = self.canvas_pos(self.editLabel.currentShape[0])

        if startPoint:
            painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
            painter.setBrush(QBrush(Qt.red, Qt.BDiagPattern))
            painterpath1 = QPainterPath()
            painterpath1.addRect(startPoint.x(), startPoint.y(), 
                            self.labelPoint.x()-startPoint.x(),
                            self.labelPoint.y()-startPoint.y())
            painterpath1.moveTo(startPoint)
            painterpath1.lineTo(self.labelPoint)
            painter.drawPath(painterpath1)

            painter.setBrush(QBrush(Qt.green, Qt.SolidPattern))
            painterpath2 = QPainterPath()
            painterpath2.addEllipse(startPoint, 3, 3)
            painter.drawPath(painterpath2)
        if endPoint:
            painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
            painterpath2 = QPainterPath()
            painterpath2.addEllipse(endPoint, 3, 3)
            painter.drawPath(painterpath2)

    def drawCreatePoly(self, painter):
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.green, Qt.NoBrush))
        currentShape = self.canvas_shape(self.editLabel.currentShape)
        painterpath1 = QPainterPath()
        painterpath1.addPolygon(QPolygonF(currentShape))

        if len(currentShape) > 0:
            painterpath1.moveTo(currentShape[-1])
            painterpath1.lineTo(self.labelPoint)
        painter.drawPath(painterpath1)

        painter.setBrush(QBrush(Qt.green, Qt.SolidPattern))
        painterpath2 = QPainterPath()
        for labelPoint in currentShape:
            painterpath2.addEllipse(labelPoint, 3, 3)
        painter.drawPath(painterpath2)

    def drawAdjustRect(self, painter):
        startPoint, endPoint = self.canvas_shape(self.editLabel.shapes[self.editLabel.near_shape_index])
        painterpath1 = QPainterPath()
        painterpath1.addRect(startPoint.x(), startPoint.y(), endPoint.x()-startPoint.x(), endPoint.y()-startPoint.y())
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(0, 255, 0, 30), Qt.SolidPattern))
        painter.drawPath(painterpath1)
        
        painterpath2 = QPainterPath()
        painterpath2.addRect(startPoint.x()-5, startPoint.y()-5, 10, 10)
        painterpath2.addRect(endPoint.x()-5, startPoint.y()-5, 10, 10)
        painterpath2.addRect(startPoint.x()-5, endPoint.y()-5, 10, 10)
        painterpath2.addRect(endPoint.x()-5, endPoint.y()-5, 10, 10)
        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.red, Qt.SolidPattern))
        painter.drawPath(painterpath2)

    def paintRect(self, painter):
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        for i, shape in enumerate(self.editLabel.shapes):
            if PointCalculator.pointInsideRect(self.imagePoint, shape):
                painter.setBrush(QBrush(QColor(0, 255, 0, 30), Qt.SolidPattern))
            else:
                painter.setBrush(QBrush(QColor(0, 255, 0, 0), Qt.SolidPattern))
            if i == self.editLabel.move_index and self.editLabel.editing_mode == MOVING:
                painter.setBrush(QBrush(QColor(0, 0, 255, 30), Qt.SolidPattern))
            if i != self.editLabel.near_shape_index:
                startPoint, endPoint = self.canvas_shape(shape)
                painterpath0 = QPainterPath()
                painterpath0.addRect(startPoint.x(), startPoint.y(), 
                                    endPoint.x()-startPoint.x(),
                                    endPoint.y()-startPoint.y())
                painter.drawPath(painterpath0)

        painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.blue, Qt.SolidPattern))
        for i, shape in enumerate(self.editLabel.shapes):
            startPoint, endPoint = self.canvas_shape(shape)
            if i != self.editLabel.near_shape_index:
                painterpath1 = QPainterPath()
                painterpath1.addEllipse(QPoint(startPoint.x(), startPoint.y()), 3, 3)
                painterpath1.addEllipse(QPoint(startPoint.x(), endPoint.y()), 3, 3)
                painterpath1.addEllipse(QPoint(endPoint.x(), endPoint.y()), 3, 3)
                painterpath1.addEllipse(QPoint(endPoint.x(), startPoint.y()), 3, 3)
                painter.drawPath(painterpath1)
        
        if self.editLabel.editing_mode == CREATING:
            self.drawCreateRect(painter)
        
        if self.editLabel.editing_mode == ADJUSTING and self.editLabel.nearPoint:
            self.drawAdjustRect(painter)

    def drawCreateShape(self, painter):
        self.drawCreatePoly(painter)
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.red, Qt.BDiagPattern))
        if len(self.editLabel.currentShape) >= 1 and self.editLabel.isClosePoint(self.imagePoint):
            painter.setBrush(QBrush(Qt.green, Qt.SolidPattern))
            painterpath = QPainterPath()
            painterpath.addEllipse(self.canvas_pos(self.editLabel.currentShape[0]), 8, 8)
            painter.drawPath(painterpath)

    def drawAdjustShape(self, painter):
        shape = self.canvas_shape(self.editLabel.shapes[self.editLabel.near_shape_index])
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(0, 255, 0, 30), Qt.SolidPattern))
        painterpath1 = QPainterPath()
        painterpath1.addPolygon(QPolygonF(shape))
        painterpath1.moveTo(painterpath1.currentPosition())
        painterpath1.lineTo(QPointF(shape[0]))
        painter.drawPath(painterpath1)

        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.red, Qt.SolidPattern))
        painterpath2 = QPainterPath()
        for vertexPoint in shape:
            painterpath2.addRect(vertexPoint.x()-5, vertexPoint.y()-5, 10, 10)
        painter.drawPath(painterpath2)

    def paintPoly(self, painter):
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        for i, shape in enumerate(self.editLabel.shapes):
            if PointCalculator.pointInsidePolygon(self.imagePoint, shape):
                painter.setBrush(QBrush(QColor(0, 255, 0, 30), Qt.SolidPattern))
            else:
                painter.setBrush(QBrush(QColor(0, 255, 0, 0), Qt.SolidPattern))
            if i == self.editLabel.move_index and self.editLabel.editing_mode == MOVING:
                painter.setBrush(QBrush(QColor(0, 0, 255, 30), Qt.SolidPattern))
            if i != self.editLabel.near_shape_index:
                painterpath = QPainterPath()
                painterpath.addPolygon(QPolygonF(self.canvas_shape(shape)))
                painter.drawPath(painterpath)
                painterpath.lineTo(QPointF(self.canvas_pos(shape[0])))
                painter.drawPath(painterpath)

        painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.blue, Qt.SolidPattern))
        for i, shape in enumerate(self.editLabel.shapes):
            if i != self.editLabel.near_shape_index:
                painterpath = QPainterPath()
                for vertexPoint in shape:
                    painterpath.addEllipse(self.canvas_pos(vertexPoint), 3, 3)
                painter.drawPath(painterpath)
        
        if self.editLabel.editing_mode == CREATING:
            self.drawCreateShape(painter)
        
        if self.editLabel.editing_mode == ADJUSTING and self.editLabel.nearPoint:
            self.drawAdjustShape(painter)

    def paintShape(self, painter):
        if self.shape_mode == "Rect":
            if not self.editLabel and self.openStatus:
                self.editLabel = RectLabel()
                self.parent().window().createRadiobox.setEnabled(True)
                self.parent().window().moveRadiobox.setEnabled(True)
                self.parent().window().adjustRadiobox.setEnabled(True)
                self.parent().window().createRadiobox.setChecked(True)
                self.parent().window().polyRadio.setEnabled(False)
                self.parent().window().setLabelName()
                self.labelDialog.formatCombobox.setCurrentIndex(0)
                self.openStatus = False
            elif self.editLabel and self.openStatus:
                self.editLabel.clearShapes()
                self.parent().window().setLabelName()
                self.openStatus = False
            self.paintRect(painter)
        elif self.shape_mode == "Poly":
            if not self.editLabel and self.openStatus:
                self.editLabel = PolyLabel()
                self.parent().window().createRadiobox.setEnabled(True)
                self.parent().window().moveRadiobox.setEnabled(True)
                self.parent().window().adjustRadiobox.setEnabled(True)
                self.parent().window().createRadiobox.setChecked(True)
                self.parent().window().rectRadio.setEnabled(False)
                self.parent().window().setLabelName()
                self.labelDialog.formatCombobox.setCurrentIndex(2)
                self.openStatus = False
            elif self.editLabel and self.openStatus:
                self.editLabel.clearShapes()
                self.parent().window().setLabelName()
                self.openStatus = False
            self.paintPoly(painter)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.image.width() and self.checkImageRange(self.imagePoint):
            painter = QPainter(self)
            if self.tracking:
                painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
                self.drawTrackingLine(painter)
                painter.drawText(QRect(self.labelPoint.x(), self.labelPoint.y(), 80, -60), 
                                Qt.AlignCenter, "(%d, %d)" % (self.imagePoint.x(), self.imagePoint.y()))
            self.paintShape(painter)

        self.update()

    def mousePressEvent(self, event):
        labelPoint = event.pos()
        imagePoint = self.image_pos(labelPoint)
        if self.checkImageRange(imagePoint):
            self.labelPoint = labelPoint
            self.imagePoint = imagePoint

            if self.shape_mode == "Rect" and self.editLabel:
                if self.editLabel.editing_mode == CREATING:
                    self.editLabel.addPoint(self.imagePoint)
                elif self.editLabel.editing_mode == MOVING:
                    self.editLabel.moveBench(self.imagePoint)
                elif self.editLabel.editing_mode == ADJUSTING:
                    self.editLabel.changeAdjustStatus()
            elif self.shape_mode == "Poly" and self.editLabel:
                if self.editLabel.editing_mode == CREATING:
                    self.editLabel.addPoint(self.imagePoint)
                elif self.editLabel.editing_mode == MOVING:
                    self.editLabel.moveBench(self.imagePoint)
                elif self.editLabel.editing_mode == ADJUSTING:
                    self.editLabel.changeAdjustStatus()

        super().mousePressEvent(event)
        self.update()

    def mouseMoveEvent(self, event):
        labelPoint = event.pos()
        imagePoint = self.image_pos(labelPoint)
        if self.checkImageRange(imagePoint):
            self.labelPoint = labelPoint
            self.imagePoint = imagePoint

            if self.image.width() and self.checkImageRange(self.imagePoint):
                self.parent().window().status.showMessage("X: %d Y: %d" % (self.imagePoint.x(), self.imagePoint.y()))
            else:
                self.parent().window().status.showMessage("")
            if self.shape_mode == "Rect" and self.editLabel:
                if self.editLabel.editing_mode == MOVING:
                    self.editLabel.moveUpdate(self.imagePoint)
                elif self.editLabel.editing_mode == ADJUSTING:
                    self.editLabel.adjustShape(self.imagePoint)
            if self.shape_mode == "Poly" and self.editLabel:
                if self.editLabel.editing_mode == MOVING:
                    self.editLabel.moveUpdate(self.imagePoint)
                elif self.editLabel.editing_mode == ADJUSTING:
                    self.editLabel.adjustShape(self.imagePoint)
                
        super().mouseMoveEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        labelPoint = event.pos()
        imagePoint = self.image_pos(labelPoint)
        if self.checkImageRange(imagePoint):
            self.labelPoint = labelPoint
            self.imagePoint = imagePoint

            if self.shape_mode == "Rect" and self.editLabel:
                if self.editLabel.editing_mode == CREATING:
                    if len(self.editLabel.currentShape) == 2:
                        text = self.labelDialog.popUp()
                        self.editLabel.addShape()
                        if not text or len(text) == 0:
                            self.editLabel.shapes.pop()
                        else:
                            self.editLabel.classes.append(text)
                            self.parent().window().addShapeItem(text)
                            self.labelDialog.update(text)
            elif self.shape_mode == "Poly" and self.editLabel:
                if self.editLabel.editing_mode == CREATING:
                    if self.editLabel.isClosePoint(self.imagePoint):
                        text = self.labelDialog.popUp()
                        self.editLabel.addShape()
                        if not text or len(text) == 0:
                            self.editLabel.shapes.pop()
                        else:
                            self.editLabel.classes.append(text)
                            self.parent().window().addShapeItem(text)
                            self.labelDialog.update(text)

        super().mouseReleaseEvent(event)
        self.update()

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.version = "1.0.0"
        self.fileName = None
        self.labelName = None
        self.setMouseTracking(False)
        self.setMenuBar()
        self.setToolBar()
        self.setScrollArea()
        self.setPropertyDock()
        self.setTrackingDock()
        self.setShapeDock()
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
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        zoomInAction = QAction("&Zoom In...", self, shortcut="Ctrl++", triggered=self.zoomIn)
        zoomOutAction = QAction("&Zoom Out...", self, shortcut="Ctrl+-", triggered=self.zoomOut)
        
        zoomInButton = QToolButton()
        zoomInButton.setText("Zoom In")
        zoomInButton.setCheckable(True)
        zoomInButton.setAutoExclusive(True)
        zoomInButton.setToolButtonStyle(self.toolbar.toolButtonStyle())
        zoomInButton.setDefaultAction(zoomInAction)
        self.toolbar.addWidget(zoomInButton)

        zoomOutButton = QToolButton()
        zoomOutButton.setText("Zoom Out")
        zoomOutButton.setCheckable(True)
        zoomOutButton.setAutoExclusive(True)
        zoomOutButton.setToolButtonStyle(self.toolbar.toolButtonStyle())
        zoomOutButton.setDefaultAction(zoomOutAction)
        self.toolbar.addWidget(zoomOutButton)

    def zoomIn(self):
        self.imageLabel.zoomIn()

    def zoomOut(self):
        self.imageLabel.zoomOut()

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

        self.trackCheckbox = QCheckBox('Tracking', self)
        self.trackCheckbox.clicked.connect(self.changeTrackingMode)
        whole_layout.addWidget(self.trackCheckbox)

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

    def setShapeDock(self):
        self.shapeDock = QDockWidget("Image Shapes", self)
        shapeWidget = QWidget()
        shape_layout = QVBoxLayout()
        # 对齐左上角
        shape_layout.setContentsMargins(0, 0, 0, 0)
        self.shape_list = QListWidget()
        shape_layout.addWidget(self.shape_list)
        shapeWidget.setLayout(shape_layout)
        self.shapeDock.setWidget(shapeWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.shapeDock)

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
        if text == "Rect":
            self.imageLabel.labelDialog.writerType = SUPPORT_FMTS[0]
        elif text == "Poly":
            self.imageLabel.labelDialog.writerType = SUPPORT_FMTS[2]

    def setStatusBar(self):
        self.status = self.statusBar()

    def resetStatus(self):
        self.trackCheckbox.setChecked(False)
        self.createRadiobox.setAutoExclusive(False)
        self.createRadiobox.setChecked(False)
        self.createRadiobox.setAutoExclusive(True)
        self.moveRadiobox.setAutoExclusive(False)
        self.moveRadiobox.setChecked(False)
        self.moveRadiobox.setAutoExclusive(True)
        self.adjustRadiobox.setAutoExclusive(False)
        self.adjustRadiobox.setChecked(False)
        self.adjustRadiobox.setAutoExclusive(True)
        self.createRadiobox.setEnabled(False)
        self.moveRadiobox.setEnabled(False)
        self.adjustRadiobox.setEnabled(False)
        self.polyRadio.setAutoExclusive(False)
        self.polyRadio.setChecked(False)
        self.polyRadio.setAutoExclusive(True)
        self.polyRadio.setEnabled(True)
        self.rectRadio.setAutoExclusive(False)
        self.rectRadio.setChecked(False)
        self.rectRadio.setAutoExclusive(True)
        self.rectRadio.setEnabled(True)
        self.shape_list.clear()

    def openImageFile(self, fileName):
        if fileName:
            self.saveLabelDialog()
            self.imageLabel.resetStatus()
            self.resetStatus()
            self.fileName = fileName
            self.imageLabel.image = QImage(fileName)
            if self.imageLabel.checkNullImage():
                QMessageBox.information(self, "Warning", "Cannot load %s." % fileName)
                return

            self.imageLabel.setPixmap(QPixmap.fromImage(self.imageLabel.image))
            self.imageLabel.adjustSize()
            self.setTable()
            self.imageLabel.openStatus = True

    def openImageDialog(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "All Files (*)", options=options)
        self.openImageFile(fileName)

    def loadLabel(self):
        if os.path.exists(self.labelName):
            data_dict = self.imageLabel.loadLabel(self.labelName)
            self.imageLabel.loadShapes(data_dict)

    def addShapeItem(self, shape_class):
        shape_item = QListWidgetItem()
        shape_item.setText(shape_class)
        shape_item.setFlags(shape_item.flags() | Qt.ItemIsUserCheckable)
        shape_item.setCheckState(Qt.Checked)
        self.shape_list.addItem(shape_item)

    def setLabelName(self):
        if self.fileName and self.imageLabel and \
            self.imageLabel.shape_mode == "Rect" and \
            self.imageLabel.labelDialog.writerType == SUPPORT_FMTS[0]:
            self.labelName = self.fileName.split(".")[0] + ".xml"
        elif self.fileName and self.imageLabel and \
            self.imageLabel.shape_mode == "Poly" and \
            self.imageLabel.labelDialog.writerType == SUPPORT_FMTS[2]:
            self.labelName = self.fileName.split(".")[0] + ".json"
        self.loadLabel()

    def saveLabelDialog(self):
        if self.labelName:
            result = QMessageBox.question(self,
                      "Save before exit",
                      "Would you like to save the label format?",
                      QMessageBox.Yes| QMessageBox.No)

            if result == QMessageBox.Yes:
                if not os.path.exists(self.labelName):
                    options = QFileDialog.Options()
                    name, _ = QFileDialog.getSaveFileName(self, "Save File", self.labelName, "All Files (*)", options=options)
                    if name:
                        self.saveLabel(name)
                else:
                    self.saveLabel(self.labelName)

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
                    xmin, xmax = sorted([int(startP.x()), int(endP.x())])
                    ymin, ymax = sorted([int(startP.y()), int(endP.y())])
                    writer.add_bnd_box(xmin, ymin, xmax, ymax, className, difficult)
                
                writer.save(target_file=name)
            elif self.imageLabel.shape_mode == "Poly" and\
                self.imageLabel.labelDialog.writerType == SUPPORT_FMTS[2]:
                writer = JsonWriter(folder_name, file_name, shape,
                                        local_img_path=self.fileName)
                
                shape_list = []
                for className, shape in zip(self.imageLabel.editLabel.classes, 
                                                self.imageLabel.editLabel.shapes):
                    shape_dict = {}
                    shapePoints = []
                    for vertexPoint in shape:
                        shapePoints.append([vertexPoint.x(), vertexPoint.y()])
                    shape_dict["label"] = className
                    shape_dict["points"] = shapePoints
                    shape_dict["group_id"] = writer.group_id
                    shape_dict["shape_type"] = writer.shape_type
                    shape_dict["flags"] = writer.flags
                    shape_list.append(shape_dict)

                writer.save(shape_list, name)

    def closeEvent(self, event):
        self.saveLabelDialog()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PanyImage")
    win = MainWindow()
    win.show()
    app.exec_()