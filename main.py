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
#version 18:弹出标签框(图像class分类信息;编辑完成按钮;格式文件选项;截取功能) 轮廓编号i;图像内坐标XY信息 生成编辑文件
#version 19:添加图片拖拽功能

import os
import sys
import math

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

DISTANCE_LIMIT = 4

class RectLabel(object):

    def __init__(self):
        super().__init__()
        self.startPoint = None
        self.endPoint = None
        self.nearPoint = None
        self.near_index = -1
        self.referPoint = None
        self.editPoint = None
        self.creating = False
        self.moving = False
        self.adjusting = False
        self.scaling = False
        self.rectPoints = []
        self.rectLabels = []
        self.highlight_index = -1

    def addPoint(self, labelPoint):
        if not self.startPoint:
            self.startPoint = labelPoint
        elif not self.endPoint:
            self.endPoint = labelPoint

    def appendRectPoint(self):
        self.rectPoints.append([self.startPoint, self.endPoint])
        self.startPoint = None
        self.endPoint = None

    def euclidDis(self, labelPoint, startPoint, endPoint):
        return math.hypot(labelPoint.x() - (startPoint.x() + endPoint.x()) / 2.0,
                        labelPoint.y() - (startPoint.y() + endPoint.y()) / 2.0)

    def checkInsideRect(self, labelPoint, startPoint, endPoint):
        return (startPoint.x()-labelPoint.x()) * (endPoint.x()-labelPoint.x()) <= 0 and \
                 (startPoint.y()-labelPoint.y()) * (endPoint.y()-labelPoint.y()) <= 0

    def findNearestPoint(self, labelPoint):
        index = -1
        nearPoint = None
        distance = -1
        x, y = labelPoint.x(), labelPoint.y()
        
        for i, [startPoint, endPoint] in enumerate(self.rectPoints):
            x1, y1 = startPoint.x(), startPoint.y()
            x2, y2 = endPoint.x(), endPoint.y()
            dis11 = math.hypot(x-x1, y-y1)
            dis12 = math.hypot(x-x1, y-y2)
            dis21 = math.hypot(x-x2, y-y1)
            dis22 = math.hypot(x-x2, y-y2)

            if distance == -1 or distance > dis11:
                distance = dis11
                nearPoint = QPoint(x1, y1)
                index = i
            if distance > dis12:
                distance = dis12
                nearPoint = QPoint(x1, y2)
                index = i
            if distance > dis21:
                distance = dis21
                nearPoint = QPoint(x2, y1)
                index = i
            if distance > dis22:
                distance = dis22
                nearPoint = QPoint(x2, y2)
                index = i

        if distance <= DISTANCE_LIMIT:
            return nearPoint, index
        return None, None

    def findNearestRect(self, labelPoint):
        index = -1
        distance = -1
        for i, [startPoint, endPoint] in enumerate(self.rectPoints):
            if self.checkInsideRect(labelPoint, startPoint, endPoint):
                if distance == -1 or distance > self.euclidDis(labelPoint, startPoint, endPoint):
                    distance = self.euclidDis(labelPoint, startPoint, endPoint)
                    index = i
        return index

    def drawRect(self, painter, labelPoint):
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        for i, [startPoint, endPoint] in enumerate(self.rectPoints):
            if self.checkInsideRect(labelPoint, startPoint, endPoint):
                painter.setBrush(QBrush(QColor(0, 255, 0, 30), Qt.SolidPattern))
            else:
                painter.setBrush(QBrush(QColor(0, 255, 0, 0), Qt.SolidPattern))
            if i == self.highlight_index and self.moving:
                painter.setBrush(QBrush(QColor(0, 0, 255, 30), Qt.SolidPattern))
            if i != self.near_index:
                painter.drawRect(startPoint.x(), startPoint.y(), 
                                endPoint.x()-startPoint.x(),
                                endPoint.y()-startPoint.y())

        painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.blue, Qt.SolidPattern))
        for i, [startPoint, endPoint] in enumerate(self.rectPoints):
            if i != self.near_index:
                painter.drawEllipse(QPoint(startPoint.x(), startPoint.y()), 3, 3)
                painter.drawEllipse(QPoint(startPoint.x(), endPoint.y()), 3, 3)
                painter.drawEllipse(QPoint(endPoint.x(), endPoint.y()), 3, 3)
                painter.drawEllipse(QPoint(endPoint.x(), startPoint.y()), 3, 3)
        
        if self.creating:
            if self.startPoint:
                painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
                painter.setBrush(QBrush(Qt.red, Qt.BDiagPattern))
                painter.drawRect(self.startPoint.x(), self.startPoint.y(), 
                                labelPoint.x()-self.startPoint.x(),
                                labelPoint.y()-self.startPoint.y())
                painter.drawLine(self.startPoint.x(), self.startPoint.y(), 
                                labelPoint.x(), labelPoint.y())
                painter.setBrush(QBrush(Qt.green, Qt.SolidPattern))
                painter.drawEllipse(QPoint(self.startPoint.x(), self.startPoint.y()), 3, 3)
            if self.endPoint:
                painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
                painter.drawEllipse(QPoint(self.endPoint.x(), self.endPoint.y()), 3, 3)
        
        if self.adjusting and self.nearPoint:
            startPoint, endPoint = self.rectPoints[self.near_index]
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

class LabelDialog(QDialog):

    def __init__(self, parent):
        super(LabelDialog, self).__init__(parent)

        self.edit = QLineEdit()
        layout = QVBoxLayout()
        layout.addWidget(self.edit)
        self.combobox = QComboBox()
        self.combobox.addItem("Pascal Voc")
        self.combobox.addItem("Yolo")
        layout.addWidget(self.combobox)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def pop_up(self, text=''):
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
        self.movePoint = None
        self.benchPoints = []

        self.image = QImage()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def checkImageRange(self, pos):
        return pos.x() >= 0 and pos.x() < self.image.width() * self.scale and pos.y() >= 0 and \
            pos.y() < self.image.height() * self.scale

    def offset_to_center(self):
        s = self.scale
        area = super(ImageLabel, self).size()
        w, h = self.image.width() * s, self.image.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QPointF(x, y)

    def image_pos(self, point):
        return point / self.scale - self.offset_to_center()

    def canvas_pos(self, point):
        return (point + self.offset_to_center()) * self.scale

    def moveRect(self):
        if not self.benchPoints:
            index = self.editLabel.findNearestRect(self.labelPoint)
            if index >= 0:
                self.editLabel.highlight_index = index
                self.movePoint = self.labelPoint
                self.benchPoints = self.editLabel.rectPoints[self.editLabel.highlight_index]
            else:
                self.editLabel.highlight_index = -1
        else:
            self.movePoint = None
            self.benchPoints = None

    def changeRectPoints(self):
        if not self.editLabel.scaling:
            self.editLabel.nearPoint, self.editLabel.near_index = self.editLabel.findNearestPoint(self.labelPoint)
            if self.editLabel.rectPoints and self.editLabel.nearPoint:
                startPoint, endPoint = self.editLabel.rectPoints[self.editLabel.near_index]
                x, y = -1, -1
                x0, y0 = self.editLabel.nearPoint.x(), self.editLabel.nearPoint.y()
                x1, y1 = startPoint.x(), startPoint.y()
                x2, y2 = endPoint.x(), endPoint.y()
                if x1 == x0:
                    x = x2
                else:
                    x = x1
                
                if y1 == y0:
                    y = y2
                else:
                    y = y1
                self.editLabel.referPoint = QPoint(x, y)
        else:
            if self.editLabel.rectPoints and self.editLabel.nearPoint:
                self.editLabel.rectPoints[self.editLabel.near_index] = [self.labelPoint, self.editLabel.referPoint]

    def getImageRect(self):
        pos = self.canvas_pos(QPoint(0, 0))
        return pos.x(), pos.y(), self.image.width() * self.scale, self.image.height() * self.scale

    def drawCrossLine(self, painter):
        _, _, w0, h0 = self.getImageRect()
        hl1 = self.canvas_pos(QPoint(0, self.imagePoint.y()))
        hl2 = self.canvas_pos(QPoint(w0, self.imagePoint.y()))
        vl1 = self.canvas_pos(QPoint(self.imagePoint.x(), 0))
        vl2 = self.canvas_pos(QPoint(self.imagePoint.x(), h0))
        painter.drawLine(hl1.x(), hl1.y(), hl2.x(), hl2.y())
        painter.drawLine(vl1.x(), vl1.y(), vl2.x(), vl2.y())

    def paintEvent(self, event):
        super(ImageLabel, self).paintEvent(event)
        if self.image.width() and self.checkImageRange(self.imagePoint):
            painter = QPainter(self)
            if self.tracking:
                painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
                self.drawCrossLine(painter)
                painter.drawText(QRect(self.labelPoint.x(), self.labelPoint.y(), 80, -60), 
                                Qt.AlignCenter, "(%d, %d)" % (self.imagePoint.x(), self.imagePoint.y()))
            if self.shape_mode == "Rect":
                if not self.editLabel:
                    self.editLabel = RectLabel()
                    self.parent().window().createRadiobox.setEnabled(True)
                    self.parent().window().moveRadiobox.setEnabled(True)
                    self.parent().window().adjustRadiobox.setEnabled(True)
                    self.parent().window().createRadiobox.setChecked(True)
                self.editLabel.drawRect(painter, self.labelPoint)
        self.update()

    def mousePressEvent(self, event):
        self.labelPoint = event.pos()
        self.imagePoint = self.image_pos(self.labelPoint)
        super(ImageLabel, self).mousePressEvent(event)
        if self.shape_mode == "Rect" and self.editLabel:
            if self.editLabel.creating:
                self.editLabel.addPoint(self.labelPoint)
            elif self.editLabel.moving:
                self.moveRect()
            elif self.editLabel.adjusting:
                if not self.editLabel.scaling and self.editLabel.nearPoint:
                    self.editLabel.scaling = True
                elif self.editLabel.scaling:
                    self.editLabel.scaling = False

        self.update()

    def mouseMoveEvent(self, event):
        self.labelPoint = event.pos()
        self.imagePoint = self.image_pos(self.labelPoint)
        if self.image.width() and self.checkImageRange(self.imagePoint):
            self.parent().window().status.showMessage("X: %d Y: %d" % (self.imagePoint.x(), self.imagePoint.y()))
        else:
            self.parent().window().status.showMessage("")
        if self.shape_mode == "Rect" and self.editLabel:
            if self.editLabel.creating:
                if self.editLabel.startPoint and self.editLabel.endPoint:
                    self.editLabel.appendRectPoint()
            elif self.editLabel.moving:
                if self.editLabel.highlight_index >= 0 and self.movePoint and self.benchPoints:
                    self.editLabel.rectPoints[self.editLabel.highlight_index] = \
                        [self.labelPoint - self.movePoint + self.benchPoints[0],
                        self.labelPoint - self.movePoint + self.benchPoints[1]]
            elif self.editLabel.adjusting:
                self.changeRectPoints()
                
        super(ImageLabel, self).mouseMoveEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        self.labelPoint = event.pos()
        self.imagePoint = self.image_pos(self.labelPoint)
        if self.shape_mode == "Rect" and self.editLabel:
            if self.editLabel.creating:
                if self.editLabel.startPoint and self.editLabel.endPoint:
                    text = self.labelDialog.pop_up()
                    self.editLabel.appendRectPoint()
                    if not text or len(text) == 0:
                        self.editLabel.rectPoints.pop()
        super(ImageLabel, self).mouseReleaseEvent(event)
        self.update()

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
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
        fileMenu.addAction(openAction)

    def setToolBar(self):
        self.toolbar = self.addToolBar('Exit')
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
        self.createRadiobox.toggled.connect(self.changeCreatingMode)
        self.createRadiobox.setEnabled(False)
        operation_layout.addWidget(self.createRadiobox)

        self.moveRadiobox = QRadioButton('Moving', self)
        self.moveRadiobox.toggled.connect(self.changeMovingMode)
        self.moveRadiobox.setEnabled(False)
        operation_layout.addWidget(self.moveRadiobox)

        self.adjustRadiobox = QRadioButton('Adjusting', self)
        self.adjustRadiobox.toggled.connect(self.changeAdjustMode)
        self.adjustRadiobox.setEnabled(False)
        operation_layout.addWidget(self.adjustRadiobox)

        operationGroup.setLayout(operation_layout)
        whole_layout.addWidget(operationGroup)
        
        shapeGroup = QGroupBox('Shape Mode:', self)
        shape_layout = QVBoxLayout()
        rectRadio = QRadioButton('Rect', self)
        rectRadio.clicked.connect(lambda checked, text=rectRadio.text():self.changeShapeMode(checked, text))

        shape_layout.addWidget(rectRadio)
        polyRadio = QRadioButton('Poly', self)
        polyRadio.clicked.connect(lambda checked, text=polyRadio.text():self.changeShapeMode(checked, text))

        shape_layout.addWidget(polyRadio)
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

    def changeCreatingMode(self):
        if self.createRadiobox.isChecked():
            if self.imageLabel.editLabel:
                self.imageLabel.editLabel.creating = True
        else:
            if self.imageLabel.editLabel:
                self.imageLabel.editLabel.creating = False

    def changeMovingMode(self):
        if self.moveRadiobox.isChecked():
            if self.imageLabel.editLabel:
                self.imageLabel.editLabel.moving = True
        else:
            if self.imageLabel.editLabel:
                self.imageLabel.editLabel.moving = False

    def changeAdjustMode(self):
        if self.adjustRadiobox.isChecked():
            if self.imageLabel.editLabel:
                self.imageLabel.editLabel.adjusting = True
        else:
            if self.imageLabel.editLabel:
                self.imageLabel.editLabel.adjusting = False

    def changeShapeMode(self, checked, text):
        self.imageLabel.shape_mode = text

    def setStatusBar(self):
        self.status = self.statusBar()

    def openImageDialog(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "","All Files (*)", options=options)
        if fileName:
            self.fileName = fileName
            self.imageLabel.image = QImage(fileName)
            if self.imageLabel.image.isNull():
                QMessageBox.information(self, "Warning", "Cannot load %s." % fileName)
                return

            self.imageLabel.setPixmap(QPixmap.fromImage(self.imageLabel.image))
            self.imageLabel.adjustSize()
            self.setTable()

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PanyImage")
    win = MainWindow()
    win.show()
    app.exec_()