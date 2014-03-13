import sys
import sip
sip.setapi('QVariant', 1)
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from EagleFile import *
import os

class TableModel(QAbstractTableModel):
    def __init__(self, bom, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.bom = bom
        self.headers = ["Name", "Value", "Sheets", "Library", "DeviceSet", "Device", "Manufacturer", "MPN", "OC_Farnell", "OC_Mouser", "OC_Digikey"]
        self.columnAttributes = ["name", "value", "sheets", "library", "deviceset", "device", "MANUFACTURER", "MPN", "OC_FARNELL", "OC_MOUSER", "OC_DIGIKEY"]

    def rowCount(self, parent):
        return len(self.bom)

    def columnCount(self, parent):
        return len(self.columnAttributes)

    def data(self, index, role):
        if not index.isValid():
            return ""
        elif role != Qt.DisplayRole:
            return None
        else:
            try:
                part = self.bom[index.row()]
                attr_name = self.columnAttributes[index.column()]
                if (attr_name=="sheets"):
                    return part.getSheetsString()
                else:
                    return part.getAttributes()[attr_name]
            except KeyError:
                return ""

    def headerData(self, col, orientation, role):
        if (orientation==Qt.Horizontal) and (role==Qt.DisplayRole):
            return self.headers[col]
        else:
            return None

class EditAttributesDialog(QDialog):

    def __init__(self, *args):
        QDialog.__init__(self, *args)

        self.attribute_names = ["value", "MANUFACTURER", "MPN", "OC_FARNELL", "OC_MOUSER", "OC_DIGIKEY"]
        self.attributes = {
            "value": {"caption": "Value:"},
            "MANUFACTURER": {"caption": "Manufacturer:"},
            "MPN": {"caption": "Part Number:"},
            "OC_FARNELL": {"caption": "Farnell OC:"},
            "OC_MOUSER": {"caption": "Mouser OC:"},
            "OC_DIGIKEY": {"caption": "DigiKey OC:"},
        }

        def createOnTextChanged(cb):
            return lambda: cb.setChecked(True)

        for a in self.attribute_names:
            checkbox = QCheckBox()
            self.attributes[a]["checkbox"] = checkbox
            edit = QLineEdit()
            edit.textChanged.connect(createOnTextChanged(checkbox))
            self.attributes[a]["edit"] = edit


        self.setLayout(self.createGUI())

    def createGUI(self):
        self.setMinimumSize(400, 200)
        grid = QGridLayout()
        i = 0
        for attr_name in self.attribute_names:
            attr = self.attributes[attr_name]
            grid.addWidget(attr["checkbox"], i, 0)
            grid.addWidget(QLabel(attr["caption"]), i, 1)
            grid.addWidget(attr["edit"], i, 2)
            i += 1

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        vbox = QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addWidget(self.buttons)

        QObject.connect(self.buttons, SIGNAL("accepted()"), self.accept)
        QObject.connect(self.buttons, SIGNAL("rejected()"), self.reject)

        return vbox

    def execute(self, parts):
        if len(parts)<1:
            return None

        self.setWindowTitle("Change attributes: " + ",".join(x.name for x in parts))

        for an in self.attribute_names:
            allTheSame = True
            x = parts[0].getAttribute(an)
            for part in parts:
                if part.getAttribute(an) != x:
                    allTheSame = False
                    break
            if allTheSame:
                self.attributes[an]["edit"].setText(x)
            else:
                self.attributes[an]["edit"].setText("")
            self.attributes[an]["checkbox"].setChecked(False)

        if self.exec_():
            result = dict()
            for attr_name in self.attributes:
                attr = self.attributes[attr_name]
                result[attr_name] = {"change": attr["checkbox"].isChecked(), "value": attr["edit"].text()}
            return result
        else:
            return None


class MainWindow(QMainWindow):

    def __init__(self, *args):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Eagle BOM Editor")
        self.schema = EagleSchema()
        self.board = EagleBoard()

        self.setCentralWidget(self.createGUI())
        self.editAttributesDialog = EditAttributesDialog()
        self.fileName = None
        self.hasUnsavedChanges = False

    def setHasUnsavedChanges(self, changes):
        self.hasUnsavedChanges = changes
        title = "Eagle BOM Editor"
        if (self.fileName != None):
            title = title + " - " + self.fileName
        if (self.hasUnsavedChanges):
            title = title + "*"
        self.setWindowTitle(title)

    def getBoardName(self, fileName):
        baseName, fileExtension = os.path.splitext(fileName)
        return baseName + ".brd"

    def openFile(self):
        path = os.path.expanduser("~") if (self.fileName==None) else os.path.dirname(self.fileName)
        fn = QFileDialog.getOpenFileName(self, "Open File", path, "Eagle Schematics (*.sch)")
        if fn != "":
            self.fileName = fn
            self.schema.loadFile(self.fileName)
            tm = TableModel(self.schema.bom, self)
            self.table.setModel(tm)
            self.table.resizeColumnsToContents()

            boardName = self.getBoardName(fn)
            if (os.path.isfile(boardName)):
                self.board.loadFile(boardName)
            else:
                self.board.clear()
                QMessageBox.question(
                    self,
                    "Board File Not Found",
                    "No corresponding board file was found.\nModified attributes will not be synced to the board.\n" + self.fileName,
                    QMessageBox.Ok, QMessageBox.Ok
                )

            self.saveFileAction.setEnabled(True)
            self.saveFileAsAction.setEnabled(True)
            self.setHasUnsavedChanges(False)

    def overwriteFile(self, fn):
        self.schema.saveToFile(fn)

        if not self.board.isEmpty():
            boardName = self.getBoardName(fn)
            self.board.saveToFile(boardName)

        self.setHasUnsavedChanges(False)
        self.fileName = fn

    def saveFile(self):
        if os.path.isfile(self.fileName):
            reply = QMessageBox.question(
                self,
                 "Overwrite File",
                 "Are you brave enough to overwrite your eagle schematic?\n" + self.fileName,
                 QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok
            )
            if reply == QMessageBox.Ok:
                self.overwriteFile(self.fileName)

    def saveFileAs(self):
        path = os.path.expanduser("~") if (self.fileName==None) else os.path.dirname(self.fileName)
        fn = QFileDialog.getSaveFileName(self, "Save File As", path, "Eagle Files (*.sch)")
        if fn != "":
            fileName, fileExtension = os.path.splitext(fn)
            if fileExtension != ".sch":
                fn = fn + ".sch"

            if os.path.isfile(fn):
                reply = QMessageBox.question(
                    self,
                    "Overwrite File",
                    "Are you brave enough to overwrite your eagle schematic?\n" + self.fileName,
                    QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok
                )
                if reply != QMessageBox.Ok:
                    return

            self.overwriteFile(fn)

    def quit(self):
        if self.hasUnsavedChanges:
            if QMessageBox.question(
                self,
                "Quit",
                "Your BOM was modified, but not saved.\nAre you sure you want to quit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            ) != QMessageBox.Yes:
                return
        qApp.quit()

    def createGUI(self):
        exitAction = QAction(QIcon('exit.png'), 'E&xit', self)
        exitAction.setShortcut('Alt+F4')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.quit)

        openFileAction = QAction("&Open", self)
        openFileAction.setShortcut("Ctrl+O")
        openFileAction.triggered.connect(self.openFile)

        self.saveFileAction = QAction('&Save', self)
        self.saveFileAction.setShortcut('Ctrl+S')
        self.saveFileAction.triggered.connect(self.saveFile)
        self.saveFileAction.setEnabled(False)

        self.saveFileAsAction = QAction('Save &As', self)
        self.saveFileAsAction.setShortcut('Shift+Ctrl+S')
        self.saveFileAsAction.triggered.connect(self.saveFileAs)
        self.saveFileAsAction.setEnabled(False)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openFileAction)
        fileMenu.addAction(self.saveFileAction)
        fileMenu.addAction(self.saveFileAsAction)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAction)

        editMenu = menubar.addMenu("&Edit")

        self.statusBar()

        self.table = self.createTable()

        btAttributeEdit = QPushButton("Properties...")
        btAttributeEdit.clicked.connect(self.onAttributeEditClick)
        hbox = QHBoxLayout()
        hbox.addWidget(btAttributeEdit)
        hbox.addStretch(1)
        hbox.setMargin(0)
        vbox = QVBoxLayout()
        vbox.addWidget(self.table)
        vbox.addLayout(hbox)

        vbox.setMargin(0)
        widget = QWidget()
        widget.setLayout(vbox)
        return widget

    def createTable(self):
        # create the view
        tableView = QTableView()

        tm = TableModel(self.schema.bom, self)
        tableView.setModel(tm)

        tableView.setMinimumSize(1000, 600)
        tableView.setSelectionBehavior(QAbstractItemView.SelectRows)

        vh = tableView.verticalHeader()
        vh.setDefaultSectionSize(18)
        vh.setVisible(False)

        hh = tableView.horizontalHeader()
        hh.setStretchLastSection(True)

        tableView.resizeColumnsToContents()

        return tableView

    def onAttributeEditClick(self):
        select = self.table.selectionModel()
        selectedParts = [self.schema.bom[x.row()] for x in select.selectedRows(0)]
        result = self.editAttributesDialog.execute(selectedParts)
        if result!=None:
            for part in selectedParts:
                for attr in result:
                    if result[attr]["change"]:
                        part.setAttribute(attr, result[attr]["value"])
                        self.board.setAttribute(part.name, attr, result[attr]["value"])
                        self.setHasUnsavedChanges(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())