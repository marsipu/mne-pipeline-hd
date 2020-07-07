from PyQt5.QtCore import QAbstractListModel, QAbstractTableModel, Qt
from PyQt5.QtGui import QColor, QFont


class CheckListModel(QAbstractListModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self.checked = []

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return self._data[index.row()]

        if role == Qt.CheckStateRole:
            if index in self.checked:
                return Qt.Checked
            else:
                return Qt.Unchecked

    def setData(self, index, value, role=None):
        if role == Qt.CheckStateRole:
            if value == Qt.Checked:
                self.checked.append(index)
            else:
                self.checked.remove(index)

    def rowCount(self, index=None):
        return len(self._data)

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable

    def getchecked(self):
        """
        Get checked list-items
        :return: list with checked items
        """
        return [self._data[index.row()] for index in self.checked]


class DataTableModel(QAbstractTableModel):
    def __init__(self, main_win):
        super().__init__()
        self.mw = main_win

    def data(self, index, role=None):
        value = self.mw.main_data.iloc[index.row(), index.column()]
        column = self.mw.main_data.columns[index.column()]
        if role == Qt.DisplayRole:
            if column == 'Datum':
                return value.strftime('%d.%m.%Y')

            if column == 'Betrag':
                return f'{value} €'

            if column == 'Kategorie':
                return f'{int(value)}'

            return value

        if role == Qt.FontRole:
            if column in ['Datum', 'Betrag']:
                return QFont('Helvetica', self.mw.font_size, QFont.Bold)
            elif column in ['Wer', 'Was']:
                return QFont('Helvetica', self.mw.font_size, italic=True)
            else:
                return QFont('Helvetica', self.mw.font_size)

        if role == Qt.ForegroundRole:
            if column == 'Betrag':
                if value < 0:
                    return QColor('red')
                else:
                    return QColor('green')

        if role == Qt.TextAlignmentRole:
            if column in ['Betrag', 'Kategorie']:
                return Qt.AlignRight

    def rowCount(self, index=None):
        return len(self.mw.main_data.index)

    def columnCount(self, index=None):
        return len(self.mw.main_data.columns)

    def headerData(self, idx, orientation, role=None):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self.mw.main_data.columns[idx])
            if orientation == Qt.Vertical:
                return str(self.mw.main_data.index[idx])
