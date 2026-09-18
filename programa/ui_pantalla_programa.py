# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pantalla_programa.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QGraphicsView,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMenuBar, QPushButton, QSizePolicy,
    QStackedWidget, QStatusBar, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1958, 1072)
        MainWindow.setStyleSheet(u"background-color: #62CBC9")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.stackedWidget = QStackedWidget(self.centralwidget)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.stackedWidget.setGeometry(QRect(129, -1, 1831, 1061))
        self.stackedWidget.setStyleSheet(u"background-color: #3F4D4C\n"
"")
        self.menu = QWidget()
        self.menu.setObjectName(u"menu")
        self.menu.setStyleSheet(u"QWidget#menu{\n"
"	border: 3px solid #333333;\n"
"	border-radius: 10px\n"
"}")
        self.label = QLabel(self.menu)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(760, 60, 301, 91))
        self.label.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 48px;\n"
"font-weight: bold;\n"
"font-family: nunito;\n"
"text-align: center;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bt_pg_movimientos2 = QPushButton(self.menu)
        self.bt_pg_movimientos2.setObjectName(u"bt_pg_movimientos2")
        self.bt_pg_movimientos2.setGeometry(QRect(580, 340, 121, 71))
        self.bt_pg_movimientos2.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.bt_pg_programa_2 = QPushButton(self.menu)
        self.bt_pg_programa_2.setObjectName(u"bt_pg_programa_2")
        self.bt_pg_programa_2.setGeometry(QRect(850, 340, 121, 71))
        self.bt_pg_programa_2.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.stackedWidget.addWidget(self.menu)
        self.movimientos = QWidget()
        self.movimientos.setObjectName(u"movimientos")
        self.movimientos.setStyleSheet(u"QWidget#movimientos{\n"
"	border: 3px solid #333333;\n"
"	border-radius: 10px\n"
"}")
        self.label_2 = QLabel(self.movimientos)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(800, 80, 221, 91))
        self.label_2.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 36px;\n"
"font-weight: bold;\n"
"font-family: nunito;\n"
"text-align: center;")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.horizontalLayoutWidget = QWidget(self.movimientos)
        self.horizontalLayoutWidget.setObjectName(u"horizontalLayoutWidget")
        self.horizontalLayoutWidget.setGeometry(QRect(690, 550, 451, 91))
        self.horizontalLayout = QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.bt_mov_izquierda_rapido = QPushButton(self.horizontalLayoutWidget)
        self.bt_mov_izquierda_rapido.setObjectName(u"bt_mov_izquierda_rapido")
        self.bt_mov_izquierda_rapido.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding-top: 10px;\n"
"	padding-bottom: 10px;\n"
"	padding-right: 1px;\n"
"	padding-left: 1px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        icon = QIcon()
        icon.addFile(u"../../../../.designer/imagenes/doble_flecha_izquierda.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bt_mov_izquierda_rapido.setIcon(icon)
        self.bt_mov_izquierda_rapido.setIconSize(QSize(36, 36))

        self.horizontalLayout.addWidget(self.bt_mov_izquierda_rapido)

        self.bt_mov_izquierda = QPushButton(self.horizontalLayoutWidget)
        self.bt_mov_izquierda.setObjectName(u"bt_mov_izquierda")
        self.bt_mov_izquierda.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        icon1 = QIcon()
        icon1.addFile(u"../../../../.designer/imagenes/play_redondeado_izquierda.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bt_mov_izquierda.setIcon(icon1)
        self.bt_mov_izquierda.setIconSize(QSize(36, 36))

        self.horizontalLayout.addWidget(self.bt_mov_izquierda)

        self.bt_mov_derecha = QPushButton(self.horizontalLayoutWidget)
        self.bt_mov_derecha.setObjectName(u"bt_mov_derecha")
        self.bt_mov_derecha.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        icon2 = QIcon()
        icon2.addFile(u"../../../../.designer/imagenes/play_redondeado_derecha.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bt_mov_derecha.setIcon(icon2)
        self.bt_mov_derecha.setIconSize(QSize(36, 36))

        self.horizontalLayout.addWidget(self.bt_mov_derecha)

        self.bt_mov_derecha_rapido = QPushButton(self.horizontalLayoutWidget)
        self.bt_mov_derecha_rapido.setObjectName(u"bt_mov_derecha_rapido")
        self.bt_mov_derecha_rapido.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        icon3 = QIcon()
        icon3.addFile(u"../../../../.designer/imagenes/doble_flecha_derecha.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bt_mov_derecha_rapido.setIcon(icon3)
        self.bt_mov_derecha_rapido.setIconSize(QSize(36, 36))

        self.horizontalLayout.addWidget(self.bt_mov_derecha_rapido)

        self.verticalLayoutWidget = QWidget(self.movimientos)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(580, 310, 160, 191))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.bt_mov_reposo = QPushButton(self.verticalLayoutWidget)
        self.bt_mov_reposo.setObjectName(u"bt_mov_reposo")
        self.bt_mov_reposo.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")

        self.verticalLayout.addWidget(self.bt_mov_reposo)

        self.bt_home = QPushButton(self.verticalLayoutWidget)
        self.bt_home.setObjectName(u"bt_home")
        self.bt_home.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")

        self.verticalLayout.addWidget(self.bt_home)

        self.gridLayoutWidget = QWidget(self.movimientos)
        self.gridLayoutWidget.setObjectName(u"gridLayoutWidget")
        self.gridLayoutWidget.setGeometry(QRect(770, 310, 281, 191))
        self.gridLayout = QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.gridLayoutWidget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")

        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)

        self.posicion = QLineEdit(self.gridLayoutWidget)
        self.posicion.setObjectName(u"posicion")
        self.posicion.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout.addWidget(self.posicion, 1, 1, 1, 1)

        self.objetivo = QLineEdit(self.gridLayoutWidget)
        self.objetivo.setObjectName(u"objetivo")
        self.objetivo.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout.addWidget(self.objetivo, 0, 1, 1, 1)

        self.label_4 = QLabel(self.gridLayoutWidget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setStyleSheet(u"color: #62CBC9;;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")

        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)

        self.bt_ir_objetivo = QPushButton(self.movimientos)
        self.bt_ir_objetivo.setObjectName(u"bt_ir_objetivo")
        self.bt_ir_objetivo.setGeometry(QRect(1080, 340, 151, 51))
        self.bt_ir_objetivo.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.label_5 = QLabel(self.movimientos)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(840, 520, 151, 16))
        self.label_5.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.formLayoutWidget = QWidget(self.movimientos)
        self.formLayoutWidget.setObjectName(u"formLayoutWidget")
        self.formLayoutWidget.setGeometry(QRect(1390, 340, 271, 188))
        self.formLayout = QFormLayout(self.formLayoutWidget)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.label_7 = QLabel(self.formLayoutWidget)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_7)

        self.vel_objetivo = QLineEdit(self.formLayoutWidget)
        self.vel_objetivo.setObjectName(u"vel_objetivo")
        self.vel_objetivo.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.vel_objetivo)

        self.label_8 = QLabel(self.formLayoutWidget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_8)

        self.aceleracion = QLineEdit(self.formLayoutWidget)
        self.aceleracion.setObjectName(u"aceleracion")
        self.aceleracion.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.aceleracion)

        self.label_9 = QLabel(self.formLayoutWidget)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_9)

        self.deceleracion = QLineEdit(self.formLayoutWidget)
        self.deceleracion.setObjectName(u"deceleracion")
        self.deceleracion.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.deceleracion)

        self.label_6 = QLabel(self.movimientos)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setGeometry(QRect(1410, 300, 231, 19))
        self.label_6.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stackedWidget.addWidget(self.movimientos)
        self.PMB8 = QWidget()
        self.PMB8.setObjectName(u"PMB8")
        self.label_28 = QLabel(self.PMB8)
        self.label_28.setObjectName(u"label_28")
        self.label_28.setGeometry(QRect(20, 610, 25, 25))
        self.label_28.setStyleSheet(u"color: #62CBC9;;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_29 = QLabel(self.PMB8)
        self.label_29.setObjectName(u"label_29")
        self.label_29.setGeometry(QRect(20, 560, 25, 25))
        self.label_29.setStyleSheet(u"color: #62CBC9;;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.lblCoordsText = QLabel(self.PMB8)
        self.lblCoordsText.setObjectName(u"lblCoordsText")
        self.lblCoordsText.setGeometry(QRect(30, 410, 130, 20))
        self.lblCoordsText.setStyleSheet(u"color: #62CBC9;;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.btnMirrorY = QPushButton(self.PMB8)
        self.btnMirrorY.setObjectName(u"btnMirrorY")
        self.btnMirrorY.setGeometry(QRect(70, 250, 111, 61))
        self.btnMirrorY.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.systemode = QComboBox(self.PMB8)
        self.systemode.setObjectName(u"systemode")
        self.systemode.setGeometry(QRect(240, 9, 370, 41))
        self.systemode.setStyleSheet(u" background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.rip2 = QLabel(self.PMB8)
        self.rip2.setObjectName(u"rip2")
        self.rip2.setGeometry(QRect(1510, 290, 300, 210))
        self.rip2.setStyleSheet(u"background-color: rgb(255, 255, 255);\n"
"border: 2px solid #62CBC9;\n"
"border-radius: 5px;")
        self.pos_x_target = QLineEdit(self.PMB8)
        self.pos_x_target.setObjectName(u"pos_x_target")
        self.pos_x_target.setGeometry(QRect(60, 550, 161, 41))
        self.pos_x_target.setStyleSheet(u"background-color: rgb(255, 255, 255);\n"
"color: rgb(0, 0, 0);\n"
"border: 2px solid #62CBC9;\n"
"border-radius: 5px;\n"
"padding: 10px;\n"
"font-size: 20px;\n"
"font-family: nunito;")
        self.btnPrint = QPushButton(self.PMB8)
        self.btnPrint.setObjectName(u"btnPrint")
        self.btnPrint.setGeometry(QRect(1390, 550, 100, 100))
        self.btnPrint.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.label_30 = QLabel(self.PMB8)
        self.label_30.setObjectName(u"label_30")
        self.label_30.setGeometry(QRect(20, 450, 25, 25))
        self.label_30.setStyleSheet(u"color: #62CBC9;;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.btnSelect = QPushButton(self.PMB8)
        self.btnSelect.setObjectName(u"btnSelect")
        self.btnSelect.setGeometry(QRect(1390, 190, 100, 100))
        font = QFont()
        font.setFamilies([u"nunito"])
        self.btnSelect.setFont(font)
        self.btnSelect.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.btn_clear = QPushButton(self.PMB8)
        self.btn_clear.setObjectName(u"btn_clear")
        self.btn_clear.setGeometry(QRect(1610, 970, 100, 41))
        self.btn_clear.setStyleSheet(u"QPushButton {\n"
"	background-color: rgb(227, 0, 0);\n"
"	border: 2px solid #333333;\n"
"	border-radius: 5px;\n"
"	padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(255, 0, 0)\n"
"}\n"
"QPushButton:pressed {rgb(229, 13, 35)\n"
"}")
        self.labelImage = QLabel(self.PMB8)
        self.labelImage.setObjectName(u"labelImage")
        self.labelImage.setGeometry(QRect(240, 60, 1131, 800))
        self.labelImage.setAutoFillBackground(False)
        self.labelImage.setStyleSheet(u"background-color: white;\n"
"border: 2px solid #62CBC9;\n"
"border-radius: 5px;")
        self.labelImage.setScaledContents(False)
        self.rip4 = QLabel(self.PMB8)
        self.rip4.setObjectName(u"rip4")
        self.rip4.setGeometry(QRect(1510, 750, 300, 210))
        self.rip4.setStyleSheet(u"background-color: rgb(255, 255, 255);\n"
"border: 2px solid #62CBC9;\n"
"border-radius: 5px;")
        self.btnRotate = QPushButton(self.PMB8)
        self.btnRotate.setObjectName(u"btnRotate")
        self.btnRotate.setGeometry(QRect(70, 110, 111, 61))
        self.btnRotate.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.pos_y_target = QLineEdit(self.PMB8)
        self.pos_y_target.setObjectName(u"pos_y_target")
        self.pos_y_target.setGeometry(QRect(60, 600, 161, 41))
        self.pos_y_target.setStyleSheet(u"background-color: rgb(255, 255, 255);\n"
"color: rgb(0, 0, 0);\n"
"border: 2px solid #62CBC9;\n"
"border-radius: 5px;\n"
"padding: 10px;\n"
"font-size: 20px;\n"
"font-family: nunito;")
        self.rip1 = QLabel(self.PMB8)
        self.rip1.setObjectName(u"rip1")
        self.rip1.setGeometry(QRect(1510, 60, 300, 210))
        self.rip1.setStyleSheet(u"background-color: rgb(255, 255, 255);\n"
"border: 2px solid #62CBC9;\n"
"border-radius: 5px;")
        self.lblSizeValue = QLabel(self.PMB8)
        self.lblSizeValue.setObjectName(u"lblSizeValue")
        self.lblSizeValue.setGeometry(QRect(1210, 10, 160, 40))
        self.lblSizeValue.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.rip3 = QLabel(self.PMB8)
        self.rip3.setObjectName(u"rip3")
        self.rip3.setGeometry(QRect(1510, 520, 300, 210))
        self.rip3.setStyleSheet(u"background-color: rgb(255, 255, 255);\n"
"border: 2px solid #62CBC9;\n"
"border-radius: 5px;")
        self.pos_x_real = QLabel(self.PMB8)
        self.pos_x_real.setObjectName(u"pos_x_real")
        self.pos_x_real.setGeometry(QRect(60, 444, 161, 41))
        self.pos_x_real.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 20px;\n"
"	font-family: nunito;")
        self.btnUpdateMode = QPushButton(self.PMB8)
        self.btnUpdateMode.setObjectName(u"btnUpdateMode")
        self.btnUpdateMode.setGeometry(QRect(60, 10, 130, 41))
        self.btnUpdateMode.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.btnNewjob = QPushButton(self.PMB8)
        self.btnNewjob.setObjectName(u"btnNewjob")
        self.btnNewjob.setGeometry(QRect(1390, 70, 100, 100))
        self.btnNewjob.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.btnRip = QPushButton(self.PMB8)
        self.btnRip.setObjectName(u"btnRip")
        self.btnRip.setGeometry(QRect(1390, 410, 100, 100))
        self.btnRip.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.txtMessage = QTextEdit(self.PMB8)
        self.txtMessage.setObjectName(u"txtMessage")
        self.txtMessage.setGeometry(QRect(240, 870, 1131, 151))
        self.txtMessage.setStyleSheet(u"background-color: rgb(174, 199, 232);\n"
"color: rgb(0, 0, 0);\n"
"border: 2px solid #62CBC9;\n"
"border-radius: 5px;")
        self.txtMessage.setReadOnly(True)
        self.pos_y_real = QLabel(self.PMB8)
        self.pos_y_real.setObjectName(u"pos_y_real")
        self.pos_y_real.setGeometry(QRect(60, 494, 161, 41))
        self.pos_y_real.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 20px;\n"
"	font-family: nunito;")
        self.btnMirrorX = QPushButton(self.PMB8)
        self.btnMirrorX.setObjectName(u"btnMirrorX")
        self.btnMirrorX.setGeometry(QRect(70, 180, 111, 61))
        self.btnMirrorX.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.lblSizeText = QLabel(self.PMB8)
        self.lblSizeText.setObjectName(u"lblSizeText")
        self.lblSizeText.setGeometry(QRect(1110, 30, 81, 20))
        self.lblSizeText.setStyleSheet(u"color: #62CBC9;;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_31 = QLabel(self.PMB8)
        self.label_31.setObjectName(u"label_31")
        self.label_31.setGeometry(QRect(20, 500, 25, 25))
        self.label_31.setStyleSheet(u"color: #62CBC9;;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.btnAbort = QPushButton(self.PMB8)
        self.btnAbort.setObjectName(u"btnAbort")
        self.btnAbort.setGeometry(QRect(1390, 690, 100, 100))
        self.btnAbort.setStyleSheet(u"QPushButton {\n"
"    background-color: rgb(227, 0, 0);\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")
        self.stackedWidget.addWidget(self.PMB8)
        self.programa = QWidget()
        self.programa.setObjectName(u"programa")
        self.label_10 = QLabel(self.programa)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setGeometry(QRect(750, 100, 221, 61))
        self.label_10.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 36px;\n"
"font-weight: bold;\n"
"font-family: nunito;\n"
"text-align: center;")
        self.label_10.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.formLayoutWidget_2 = QWidget(self.programa)
        self.formLayoutWidget_2.setObjectName(u"formLayoutWidget_2")
        self.formLayoutWidget_2.setGeometry(QRect(1490, 190, 311, 514))
        self.formLayout_2 = QFormLayout(self.formLayoutWidget_2)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.formLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_11 = QLabel(self.formLayoutWidget_2)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_11.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_11)

        self.pg_prog_vel_impresion = QLineEdit(self.formLayoutWidget_2)
        self.pg_prog_vel_impresion.setObjectName(u"pg_prog_vel_impresion")
        self.pg_prog_vel_impresion.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.FieldRole, self.pg_prog_vel_impresion)

        self.label_12 = QLabel(self.formLayoutWidget_2)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_12.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.formLayout_2.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_12)

        self.pg_prog_acel_impresion = QLineEdit(self.formLayoutWidget_2)
        self.pg_prog_acel_impresion.setObjectName(u"pg_prog_acel_impresion")
        self.pg_prog_acel_impresion.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout_2.setWidget(1, QFormLayout.ItemRole.FieldRole, self.pg_prog_acel_impresion)

        self.label_14 = QLabel(self.formLayoutWidget_2)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_14)

        self.pg_prog_decel_impresion = QLineEdit(self.formLayoutWidget_2)
        self.pg_prog_decel_impresion.setObjectName(u"pg_prog_decel_impresion")
        self.pg_prog_decel_impresion.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.FieldRole, self.pg_prog_decel_impresion)

        self.label_13 = QLabel(self.formLayoutWidget_2)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_13.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.formLayout_2.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_13)

        self.pg_prog_vel_curado = QLineEdit(self.formLayoutWidget_2)
        self.pg_prog_vel_curado.setObjectName(u"pg_prog_vel_curado")
        self.pg_prog_vel_curado.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout_2.setWidget(4, QFormLayout.ItemRole.FieldRole, self.pg_prog_vel_curado)

        self.label_16 = QLabel(self.formLayoutWidget_2)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_16.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.formLayout_2.setWidget(5, QFormLayout.ItemRole.LabelRole, self.label_16)

        self.pg_prog_acel_curado = QLineEdit(self.formLayoutWidget_2)
        self.pg_prog_acel_curado.setObjectName(u"pg_prog_acel_curado")
        self.pg_prog_acel_curado.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout_2.setWidget(5, QFormLayout.ItemRole.FieldRole, self.pg_prog_acel_curado)

        self.label_15 = QLabel(self.formLayoutWidget_2)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_15.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.formLayout_2.setWidget(6, QFormLayout.ItemRole.LabelRole, self.label_15)

        self.pg_prog_decel_curado = QLineEdit(self.formLayoutWidget_2)
        self.pg_prog_decel_curado.setObjectName(u"pg_prog_decel_curado")
        self.pg_prog_decel_curado.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout_2.setWidget(6, QFormLayout.ItemRole.FieldRole, self.pg_prog_decel_curado)

        self.label_22 = QLabel(self.formLayoutWidget_2)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_22.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.formLayout_2.setWidget(8, QFormLayout.ItemRole.LabelRole, self.label_22)

        self.pg_prog_cant_pasadas_curado = QLineEdit(self.formLayoutWidget_2)
        self.pg_prog_cant_pasadas_curado.setObjectName(u"pg_prog_cant_pasadas_curado")
        self.pg_prog_cant_pasadas_curado.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout_2.setWidget(8, QFormLayout.ItemRole.FieldRole, self.pg_prog_cant_pasadas_curado)

        self.label_27 = QLabel(self.formLayoutWidget_2)
        self.label_27.setObjectName(u"label_27")
        self.label_27.setStyleSheet(u"color: #62CBC9;\n"
"	font-size: 16px;\n"
"	font-family: nunito;")
        self.label_27.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.formLayout_2.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_27)

        self.pg_prog_inicio_curado = QLineEdit(self.formLayoutWidget_2)
        self.pg_prog_inicio_curado.setObjectName(u"pg_prog_inicio_curado")
        self.pg_prog_inicio_curado.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.formLayout_2.setWidget(3, QFormLayout.ItemRole.FieldRole, self.pg_prog_inicio_curado)

        self.verticalLayoutWidget_3 = QWidget(self.programa)
        self.verticalLayoutWidget_3.setObjectName(u"verticalLayoutWidget_3")
        self.verticalLayoutWidget_3.setGeometry(QRect(40, 360, 221, 152))
        self.verticalLayout_3 = QVBoxLayout(self.verticalLayoutWidget_3)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.bt_pg_prog_start = QPushButton(self.verticalLayoutWidget_3)
        self.bt_pg_prog_start.setObjectName(u"bt_pg_prog_start")
        self.bt_pg_prog_start.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")

        self.verticalLayout_3.addWidget(self.bt_pg_prog_start)

        self.bt_pg_prog_stop = QPushButton(self.verticalLayoutWidget_3)
        self.bt_pg_prog_stop.setObjectName(u"bt_pg_prog_stop")
        self.bt_pg_prog_stop.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")

        self.verticalLayout_3.addWidget(self.bt_pg_prog_stop)

        self.bt_pg_prog_simulacion = QPushButton(self.verticalLayoutWidget_3)
        self.bt_pg_prog_simulacion.setObjectName(u"bt_pg_prog_simulacion")
        self.bt_pg_prog_simulacion.setStyleSheet(u"QPushButton {\n"
"    background-color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(170, 255, 255);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(206, 255, 252);\n"
"}")

        self.verticalLayout_3.addWidget(self.bt_pg_prog_simulacion)

        self.gridLayoutWidget_2 = QWidget(self.programa)
        self.gridLayoutWidget_2.setObjectName(u"gridLayoutWidget_2")
        self.gridLayoutWidget_2.setGeometry(QRect(440, 720, 851, 121))
        self.gridLayout_2 = QGridLayout(self.gridLayoutWidget_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.M8D = QLineEdit(self.gridLayoutWidget_2)
        self.M8D.setObjectName(u"M8D")
        self.M8D.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout_2.addWidget(self.M8D, 1, 7, 1, 1)

        self.M5D = QLineEdit(self.gridLayoutWidget_2)
        self.M5D.setObjectName(u"M5D")
        self.M5D.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout_2.addWidget(self.M5D, 1, 4, 1, 1)

        self.M6D = QLineEdit(self.gridLayoutWidget_2)
        self.M6D.setObjectName(u"M6D")
        self.M6D.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout_2.addWidget(self.M6D, 1, 5, 1, 1)

        self.M7D = QLineEdit(self.gridLayoutWidget_2)
        self.M7D.setObjectName(u"M7D")
        self.M7D.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout_2.addWidget(self.M7D, 1, 6, 1, 1)

        self.M1D = QLineEdit(self.gridLayoutWidget_2)
        self.M1D.setObjectName(u"M1D")
        self.M1D.setStyleSheet(u"  background-color: #3F4D4C;\n"
"  color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout_2.addWidget(self.M1D, 1, 0, 1, 1)

        self.M4D = QLineEdit(self.gridLayoutWidget_2)
        self.M4D.setObjectName(u"M4D")
        self.M4D.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout_2.addWidget(self.M4D, 1, 3, 1, 1)

        self.M2D = QLineEdit(self.gridLayoutWidget_2)
        self.M2D.setObjectName(u"M2D")
        self.M2D.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout_2.addWidget(self.M2D, 1, 1, 1, 1)

        self.M3D = QLineEdit(self.gridLayoutWidget_2)
        self.M3D.setObjectName(u"M3D")
        self.M3D.setStyleSheet(u"  background-color: #3F4D4C;\n"
"color: #62CBC9;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 24px;\n"
"	font-family: nunito;")

        self.gridLayout_2.addWidget(self.M3D, 1, 2, 1, 1)

        self.modulo1 = QComboBox(self.gridLayoutWidget_2)
        self.modulo1.addItem("")
        self.modulo1.addItem("")
        self.modulo1.addItem("")
        self.modulo1.addItem("")
        self.modulo1.addItem("")
        self.modulo1.addItem("")
        self.modulo1.addItem("")
        self.modulo1.setObjectName(u"modulo1")
        self.modulo1.setStyleSheet(u" border: 1px solid #62CBC9;\n"
"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"")

        self.gridLayout_2.addWidget(self.modulo1, 2, 0, 1, 1)

        self.modulo2 = QComboBox(self.gridLayoutWidget_2)
        self.modulo2.addItem("")
        self.modulo2.addItem("")
        self.modulo2.addItem("")
        self.modulo2.addItem("")
        self.modulo2.addItem("")
        self.modulo2.addItem("")
        self.modulo2.addItem("")
        self.modulo2.setObjectName(u"modulo2")
        self.modulo2.setStyleSheet(u" border: 1px solid #62CBC9;\n"
"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"")

        self.gridLayout_2.addWidget(self.modulo2, 2, 1, 1, 1)

        self.modulo3 = QComboBox(self.gridLayoutWidget_2)
        self.modulo3.addItem("")
        self.modulo3.addItem("")
        self.modulo3.addItem("")
        self.modulo3.addItem("")
        self.modulo3.addItem("")
        self.modulo3.addItem("")
        self.modulo3.addItem("")
        self.modulo3.setObjectName(u"modulo3")
        self.modulo3.setStyleSheet(u" border: 1px solid #62CBC9;\n"
"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"")

        self.gridLayout_2.addWidget(self.modulo3, 2, 2, 1, 1)

        self.modulo4 = QComboBox(self.gridLayoutWidget_2)
        self.modulo4.addItem("")
        self.modulo4.addItem("")
        self.modulo4.addItem("")
        self.modulo4.addItem("")
        self.modulo4.addItem("")
        self.modulo4.addItem("")
        self.modulo4.addItem("")
        self.modulo4.setObjectName(u"modulo4")
        self.modulo4.setStyleSheet(u" border: 1px solid #62CBC9;\n"
"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"")

        self.gridLayout_2.addWidget(self.modulo4, 2, 3, 1, 1)

        self.modulo5 = QComboBox(self.gridLayoutWidget_2)
        self.modulo5.addItem("")
        self.modulo5.addItem("")
        self.modulo5.addItem("")
        self.modulo5.addItem("")
        self.modulo5.addItem("")
        self.modulo5.addItem("")
        self.modulo5.addItem("")
        self.modulo5.setObjectName(u"modulo5")
        self.modulo5.setStyleSheet(u" border: 1px solid #62CBC9;\n"
"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"")

        self.gridLayout_2.addWidget(self.modulo5, 2, 4, 1, 1)

        self.modulo6 = QComboBox(self.gridLayoutWidget_2)
        self.modulo6.addItem("")
        self.modulo6.addItem("")
        self.modulo6.addItem("")
        self.modulo6.addItem("")
        self.modulo6.addItem("")
        self.modulo6.addItem("")
        self.modulo6.addItem("")
        self.modulo6.setObjectName(u"modulo6")
        self.modulo6.setStyleSheet(u" border: 1px solid #62CBC9;\n"
"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"")

        self.gridLayout_2.addWidget(self.modulo6, 2, 5, 1, 1)

        self.modulo7 = QComboBox(self.gridLayoutWidget_2)
        self.modulo7.addItem("")
        self.modulo7.addItem("")
        self.modulo7.addItem("")
        self.modulo7.addItem("")
        self.modulo7.addItem("")
        self.modulo7.addItem("")
        self.modulo7.addItem("")
        self.modulo7.setObjectName(u"modulo7")
        self.modulo7.setStyleSheet(u" border: 1px solid #62CBC9;\n"
"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"")

        self.gridLayout_2.addWidget(self.modulo7, 2, 6, 1, 1)

        self.modulo8 = QComboBox(self.gridLayoutWidget_2)
        self.modulo8.addItem("")
        self.modulo8.addItem("")
        self.modulo8.addItem("")
        self.modulo8.addItem("")
        self.modulo8.addItem("")
        self.modulo8.addItem("")
        self.modulo8.addItem("")
        self.modulo8.setObjectName(u"modulo8")
        self.modulo8.setStyleSheet(u" border: 1px solid #62CBC9;\n"
"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"")

        self.gridLayout_2.addWidget(self.modulo8, 2, 7, 1, 1)

        self.label_17 = QLabel(self.gridLayoutWidget_2)
        self.label_17.setObjectName(u"label_17")
        self.label_17.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_17.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_17, 0, 0, 1, 1)

        self.label_18 = QLabel(self.gridLayoutWidget_2)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_18.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_18, 0, 1, 1, 1)

        self.label_19 = QLabel(self.gridLayoutWidget_2)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_19.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_19, 0, 2, 1, 1)

        self.label_20 = QLabel(self.gridLayoutWidget_2)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_20.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_20, 0, 3, 1, 1)

        self.label_21 = QLabel(self.gridLayoutWidget_2)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_21.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_21, 0, 4, 1, 1)

        self.label_23 = QLabel(self.gridLayoutWidget_2)
        self.label_23.setObjectName(u"label_23")
        self.label_23.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_23.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_23, 0, 5, 1, 1)

        self.label_24 = QLabel(self.gridLayoutWidget_2)
        self.label_24.setObjectName(u"label_24")
        self.label_24.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_24.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_24, 0, 6, 1, 1)

        self.label_25 = QLabel(self.gridLayoutWidget_2)
        self.label_25.setObjectName(u"label_25")
        self.label_25.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_25.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label_25, 0, 7, 1, 1)

        self.label_26 = QLabel(self.programa)
        self.label_26.setObjectName(u"label_26")
        self.label_26.setGeometry(QRect(750, 660, 231, 29))
        self.label_26.setStyleSheet(u"color: #62CBC9;\n"
"font-size: 16px;\n"
"font-family: nunito;\n"
"font-weight: bold;")
        self.label_26.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pg_vista = QGraphicsView(self.programa)
        self.pg_vista.setObjectName(u"pg_vista")
        self.pg_vista.setGeometry(QRect(300, 330, 1121, 211))
        self.pg_vista.setStyleSheet(u"QGraphicsView {\n"
"    background-color: #3F4D4C;\n"
"    border: 2px solid #62CBC9;\n"
"    border-radius: 5px;\n"
"}")
        self.stackedWidget.addWidget(self.programa)
        self.verticalLayoutWidget_2 = QWidget(self.centralwidget)
        self.verticalLayoutWidget_2.setObjectName(u"verticalLayoutWidget_2")
        self.verticalLayoutWidget_2.setGeometry(QRect(10, 0, 118, 204))
        self.verticalLayout_2 = QVBoxLayout(self.verticalLayoutWidget_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.bt_pg_menu = QPushButton(self.verticalLayoutWidget_2)
        self.bt_pg_menu.setObjectName(u"bt_pg_menu")
        self.bt_pg_menu.setStyleSheet(u"QPushButton {\n"
"    background-color: #3F4D4C;\n"
"	color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"	\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(74, 90, 88);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(89, 108, 105);\n"
"}")

        self.verticalLayout_2.addWidget(self.bt_pg_menu)

        self.bt_pg_movimientos1 = QPushButton(self.verticalLayoutWidget_2)
        self.bt_pg_movimientos1.setObjectName(u"bt_pg_movimientos1")
        self.bt_pg_movimientos1.setStyleSheet(u"QPushButton {\n"
"    background-color: #3F4D4C;\n"
"	color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"	\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(74, 90, 88);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(89, 108, 105);\n"
"}")

        self.verticalLayout_2.addWidget(self.bt_pg_movimientos1)

        self.bt_pg_programa = QPushButton(self.verticalLayoutWidget_2)
        self.bt_pg_programa.setObjectName(u"bt_pg_programa")
        self.bt_pg_programa.setStyleSheet(u"QPushButton {\n"
"    background-color: #3F4D4C;\n"
"	color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"	\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(74, 90, 88);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(89, 108, 105);\n"
"}")

        self.verticalLayout_2.addWidget(self.bt_pg_programa)

        self.pushButton = QPushButton(self.verticalLayoutWidget_2)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setStyleSheet(u"QPushButton {\n"
"    background-color: #3F4D4C;\n"
"	color: #62CBC9;\n"
"    border: 2px solid #333333;\n"
"    border-radius: 5px;\n"
"    padding: 10px;\n"
"	font-size: 16px;\n"
"	font-family: nunito;\n"
"	\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: rgb(74, 90, 88);\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: rgb(89, 108, 105);\n"
"}")

        self.verticalLayout_2.addWidget(self.pushButton)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1958, 23))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        self.stackedWidget.setCurrentIndex(3)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"materialight", None))
        self.bt_pg_movimientos2.setText(QCoreApplication.translate("MainWindow", u"Movimientos", None))
        self.bt_pg_programa_2.setText(QCoreApplication.translate("MainWindow", u"Programa", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Movimientos", None))
        self.bt_mov_izquierda_rapido.setText("")
        self.bt_mov_izquierda.setText("")
        self.bt_mov_derecha.setText("")
        self.bt_mov_derecha_rapido.setText("")
        self.bt_mov_reposo.setText(QCoreApplication.translate("MainWindow", u"Reposo", None))
        self.bt_home.setText(QCoreApplication.translate("MainWindow", u"Home", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Posici\u00f3n", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Objetivo", None))
        self.bt_ir_objetivo.setText(QCoreApplication.translate("MainWindow", u"Ir a objetivo", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Movimiento manual", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Velocidad objetivo", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Aceleraci\u00f3n", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Deceleraci\u00f3n", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Parametros de movimiento", None))
        self.label_28.setText(QCoreApplication.translate("MainWindow", u"Y:", None))
        self.label_29.setText(QCoreApplication.translate("MainWindow", u"X:", None))
        self.lblCoordsText.setText(QCoreApplication.translate("MainWindow", u"Position:", None))
        self.btnMirrorY.setText(QCoreApplication.translate("MainWindow", u"Mirror Y", None))
        self.rip2.setText("")
        self.btnPrint.setText(QCoreApplication.translate("MainWindow", u"Print", None))
        self.label_30.setText(QCoreApplication.translate("MainWindow", u"X:", None))
        self.btnSelect.setText(QCoreApplication.translate("MainWindow", u"Select\n"
"job", None))
        self.btn_clear.setText(QCoreApplication.translate("MainWindow", u"Clear", None))
        self.labelImage.setText("")
        self.rip4.setText("")
        self.btnRotate.setText(QCoreApplication.translate("MainWindow", u"Rotate", None))
        self.rip1.setText("")
        self.lblSizeValue.setText("")
        self.rip3.setText("")
        self.pos_x_real.setText("")
        self.btnUpdateMode.setText(QCoreApplication.translate("MainWindow", u"Load mode", None))
        self.btnNewjob.setText(QCoreApplication.translate("MainWindow", u"New\n"
"image", None))
        self.btnRip.setText(QCoreApplication.translate("MainWindow", u"Render", None))
        self.pos_y_real.setText("")
        self.btnMirrorX.setText(QCoreApplication.translate("MainWindow", u"Mirror X", None))
        self.lblSizeText.setText(QCoreApplication.translate("MainWindow", u"Size (mm):", None))
        self.label_31.setText(QCoreApplication.translate("MainWindow", u"Y:", None))
        self.btnAbort.setText(QCoreApplication.translate("MainWindow", u"Abort", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Programa", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"Velocidad impresi\u00f3n", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"Aceleracion impresi\u00f3n", None))
        self.label_14.setText(QCoreApplication.translate("MainWindow", u"Deceleraci\u00f3n impresion", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"Velocidad curado", None))
        self.label_16.setText(QCoreApplication.translate("MainWindow", u"Aceleraci\u00f3n curado", None))
        self.label_15.setText(QCoreApplication.translate("MainWindow", u"Deceleraci\u00f3n curado", None))
        self.label_22.setText(QCoreApplication.translate("MainWindow", u"Pasadas curado", None))
        self.label_27.setText(QCoreApplication.translate("MainWindow", u"Inicio de curado", None))
        self.bt_pg_prog_start.setText(QCoreApplication.translate("MainWindow", u"Iniciar programa", None))
        self.bt_pg_prog_stop.setText(QCoreApplication.translate("MainWindow", u"Parar programa", None))
        self.bt_pg_prog_simulacion.setText(QCoreApplication.translate("MainWindow", u"SIMULACI\u00d3N", None))
        self.modulo1.setItemText(0, QCoreApplication.translate("MainWindow", u"-", None))
        self.modulo1.setItemText(1, QCoreApplication.translate("MainWindow", u"PMB-C8", None))
        self.modulo1.setItemText(2, QCoreApplication.translate("MainWindow", u"PMB-C2", None))
        self.modulo1.setItemText(3, QCoreApplication.translate("MainWindow", u"APMB4", None))
        self.modulo1.setItemText(4, QCoreApplication.translate("MainWindow", u"SM-200", None))
        self.modulo1.setItemText(5, QCoreApplication.translate("MainWindow", u"NIR", None))
        self.modulo1.setItemText(6, QCoreApplication.translate("MainWindow", u"Air dryver", None))

        self.modulo2.setItemText(0, QCoreApplication.translate("MainWindow", u"-", None))
        self.modulo2.setItemText(1, QCoreApplication.translate("MainWindow", u"PMB-C8", None))
        self.modulo2.setItemText(2, QCoreApplication.translate("MainWindow", u"PMB-C2", None))
        self.modulo2.setItemText(3, QCoreApplication.translate("MainWindow", u"APMB4", None))
        self.modulo2.setItemText(4, QCoreApplication.translate("MainWindow", u"SM-200", None))
        self.modulo2.setItemText(5, QCoreApplication.translate("MainWindow", u"NIR", None))
        self.modulo2.setItemText(6, QCoreApplication.translate("MainWindow", u"Air dryver", None))

        self.modulo3.setItemText(0, QCoreApplication.translate("MainWindow", u"-", None))
        self.modulo3.setItemText(1, QCoreApplication.translate("MainWindow", u"PMB-C8", None))
        self.modulo3.setItemText(2, QCoreApplication.translate("MainWindow", u"PMB-C2", None))
        self.modulo3.setItemText(3, QCoreApplication.translate("MainWindow", u"APMB4", None))
        self.modulo3.setItemText(4, QCoreApplication.translate("MainWindow", u"SM-200", None))
        self.modulo3.setItemText(5, QCoreApplication.translate("MainWindow", u"NIR", None))
        self.modulo3.setItemText(6, QCoreApplication.translate("MainWindow", u"Air dryver", None))

        self.modulo4.setItemText(0, QCoreApplication.translate("MainWindow", u"-", None))
        self.modulo4.setItemText(1, QCoreApplication.translate("MainWindow", u"PMB-C8", None))
        self.modulo4.setItemText(2, QCoreApplication.translate("MainWindow", u"PMB-C2", None))
        self.modulo4.setItemText(3, QCoreApplication.translate("MainWindow", u"APMB4", None))
        self.modulo4.setItemText(4, QCoreApplication.translate("MainWindow", u"SM-200", None))
        self.modulo4.setItemText(5, QCoreApplication.translate("MainWindow", u"NIR", None))
        self.modulo4.setItemText(6, QCoreApplication.translate("MainWindow", u"Air dryver", None))

        self.modulo5.setItemText(0, QCoreApplication.translate("MainWindow", u"-", None))
        self.modulo5.setItemText(1, QCoreApplication.translate("MainWindow", u"PMB-C8", None))
        self.modulo5.setItemText(2, QCoreApplication.translate("MainWindow", u"PMB-C2", None))
        self.modulo5.setItemText(3, QCoreApplication.translate("MainWindow", u"APMB4", None))
        self.modulo5.setItemText(4, QCoreApplication.translate("MainWindow", u"SM-200", None))
        self.modulo5.setItemText(5, QCoreApplication.translate("MainWindow", u"NIR", None))
        self.modulo5.setItemText(6, QCoreApplication.translate("MainWindow", u"Air dryver", None))

        self.modulo6.setItemText(0, QCoreApplication.translate("MainWindow", u"-", None))
        self.modulo6.setItemText(1, QCoreApplication.translate("MainWindow", u"PMB-C8", None))
        self.modulo6.setItemText(2, QCoreApplication.translate("MainWindow", u"PMB-C2", None))
        self.modulo6.setItemText(3, QCoreApplication.translate("MainWindow", u"APMB4", None))
        self.modulo6.setItemText(4, QCoreApplication.translate("MainWindow", u"SM-200", None))
        self.modulo6.setItemText(5, QCoreApplication.translate("MainWindow", u"NIR", None))
        self.modulo6.setItemText(6, QCoreApplication.translate("MainWindow", u"Air dryver", None))

        self.modulo7.setItemText(0, QCoreApplication.translate("MainWindow", u"-", None))
        self.modulo7.setItemText(1, QCoreApplication.translate("MainWindow", u"PMB-C8", None))
        self.modulo7.setItemText(2, QCoreApplication.translate("MainWindow", u"PMB-C2", None))
        self.modulo7.setItemText(3, QCoreApplication.translate("MainWindow", u"APMB4", None))
        self.modulo7.setItemText(4, QCoreApplication.translate("MainWindow", u"SM-200", None))
        self.modulo7.setItemText(5, QCoreApplication.translate("MainWindow", u"NIR", None))
        self.modulo7.setItemText(6, QCoreApplication.translate("MainWindow", u"Air dryver", None))

        self.modulo8.setItemText(0, QCoreApplication.translate("MainWindow", u"-", None))
        self.modulo8.setItemText(1, QCoreApplication.translate("MainWindow", u"PMB-C8", None))
        self.modulo8.setItemText(2, QCoreApplication.translate("MainWindow", u"PMB-C2", None))
        self.modulo8.setItemText(3, QCoreApplication.translate("MainWindow", u"APMB4", None))
        self.modulo8.setItemText(4, QCoreApplication.translate("MainWindow", u"SM-200", None))
        self.modulo8.setItemText(5, QCoreApplication.translate("MainWindow", u"NIR", None))
        self.modulo8.setItemText(6, QCoreApplication.translate("MainWindow", u"Air dryver", None))

        self.label_17.setText(QCoreApplication.translate("MainWindow", u"1", None))
        self.label_18.setText(QCoreApplication.translate("MainWindow", u"2", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"3", None))
        self.label_20.setText(QCoreApplication.translate("MainWindow", u"4", None))
        self.label_21.setText(QCoreApplication.translate("MainWindow", u"5", None))
        self.label_23.setText(QCoreApplication.translate("MainWindow", u"6", None))
        self.label_24.setText(QCoreApplication.translate("MainWindow", u"7", None))
        self.label_25.setText(QCoreApplication.translate("MainWindow", u"8", None))
        self.label_26.setText(QCoreApplication.translate("MainWindow", u"Configuraci\u00f3n de m\u00f3dulos", None))
        self.bt_pg_menu.setText(QCoreApplication.translate("MainWindow", u"Menu", None))
        self.bt_pg_movimientos1.setText(QCoreApplication.translate("MainWindow", u"Movimientos", None))
        self.bt_pg_programa.setText(QCoreApplication.translate("MainWindow", u"Programa", None))
        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"PMB-8", None))
    # retranslateUi

