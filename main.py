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
#version 14:轮廓编辑模式

import os
import sys
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

class ImageLabel(QLabel):

    def __init__(self):
        super().__init__()
        self.tracking = False
        self.editing = False
        self.editing_mode = None
        self.scale = 1
        self.labelPoint = QPoint()
        self.imagePoint = QPoint()

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
            painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
            if self.tracking:
                self.drawCrossLine(painter)
                painter.drawText(QRect(self.labelPoint.x(), self.labelPoint.y(), 80, -60), 
                                Qt.AlignCenter, "(%d, %d)" % (self.imagePoint.x(), self.imagePoint.y()))
                painter.drawEllipse(QPoint(self.labelPoint.x(), self.labelPoint.y()), 10, 10)

        self.update()

    def mousePressEvent(self, event):
        self.labelPoint = event.pos()
        self.imagePoint = self.image_pos(self.labelPoint)
        super(ImageLabel, self).mousePressEvent(event)
        self.update()

    def mouseMoveEvent(self, event):
        self.labelPoint = event.pos()
        self.imagePoint = self.image_pos(self.labelPoint)
        if self.image.width() and self.checkImageRange(self.imagePoint):
            self.parent().window().status.showMessage("X: %d Y: %d" % (self.imagePoint.x(), self.imagePoint.y()))
        else:
            self.parent().window().status.showMessage("")
        super(ImageLabel, self).mouseMoveEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        self.labelPoint = event.pos()
        self.imagePoint = self.image_pos(self.labelPoint)
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
        
        editingGroup = QGroupBox('Editing Mode:', self)
        editing_layout = QVBoxLayout()
        rectRadio = QRadioButton('Rect', self)
        rectRadio.clicked.connect(lambda checked, text=rectRadio.text():self.changeEditingMode(checked, text))

        editing_layout.addWidget(rectRadio)
        polyRadio = QRadioButton('Poly', self)
        polyRadio.clicked.connect(lambda checked, text=polyRadio.text():self.changeEditingMode(checked, text))

        editing_layout.addWidget(polyRadio)
        editingGroup.setLayout(editing_layout)
        whole_layout.addWidget(editingGroup)
        self.trackingWidget.setLayout(whole_layout)

        self.trackingDock.setWidget(self.trackingWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.trackingDock)

    def changeTrackingMode(self, checked):
        if checked:
            self.imageLabel.tracking = True
            return
        self.imageLabel.tracking = False

    def changeEditingMode(self, checked, text):
        self.imageLabel.editing_mode = text

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