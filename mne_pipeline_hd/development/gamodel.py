import sys

from PyQt5.QtWidgets import QApplication, QInputDialog, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class GrandAvgWidget(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.gad = {'GroupA': ['a', 'b', 'c'],
                    'GroupB': {'a': ['a', 'b', 'c'], 'b': ['a', 'b', 'c'], 'c': ['a', 'b', 'c']},
                    'GroupC': {'d': {'a': ['a', 'b', 'c'], 'b': ['a', 'b', 'c'], 'c': ['a', 'b', 'c']},
                               'e': ['a', 'b', 'c']}}
        self.layout = QVBoxLayout()
        self.treew = QTreeWidget()
        self.treew.setColumnCount(1)
        self.treew.setHeaderLabel('Subject:')

        self.update_treew()

        self.layout.addWidget(self.treew)
        self.setLayout(self.layout)

    # Just supports level 3 nested dictionaries, kind of bulky needs improvement (probably with model/view-architecture)
    def update_treew(self):
        top_items = []
        for key1 in self.gad:
            top_item = QTreeWidgetItem()
            top_item.setText(0, key1)
            if type(self.gad[key1]) is dict:
                for key2 in self.gad[key1]:
                    sub_item = QTreeWidgetItem(top_item)
                    sub_item.setText(0, key2)
                    if type(self.gad[key1][key2]) is dict:
                        for key3 in self.gad[key1][key2]:
                            subsub_item = QTreeWidgetItem(sub_item)
                            subsub_item.setText(0, key3)
                            if type(self.gad[key1][key2][key3]) is list:
                                for listitem in self.gad[key1][key2][key3]:
                                    subsubsub_item = QTreeWidgetItem(subsub_item)
                                    subsubsub_item.setText(0, listitem)
                            else:
                                subsubsub_item = QTreeWidgetItem(subsub_item)
                                subsubsub_item.setText(0, self.gad[key1][key2][key3])
                    elif type(self.gad[key1][key2]) is list:
                        for listitem in self.gad[key1][key2]:
                            subsub_item = QTreeWidgetItem(sub_item)
                            subsub_item.setText(0, listitem)
                    else:
                        subsub_item = QTreeWidgetItem(sub_item)
                        subsub_item.setText(0, self.gad[key1][key2])
            elif type(self.gad[key1]) is list:
                for listitem in self.gad[key1]:
                    sub_item = QTreeWidgetItem(top_item)
                    sub_item.setText(0, listitem)
            else:
                sub_item = QTreeWidgetItem(top_item)
                sub_item.setText(0, self.gad[key1])
            top_items.append(top_item)

        self.treew.addTopLevelItems(top_items)

    # List-items and dict in same list not allowed
    def get_treew(self):
        new_dict = {}
        for idx in range(self.treew.topLevelItemCount()):
            top_item = self.treew.topLevelItem(idx)
            ti_text = top_item.text(0)
            new_dict.update({ti_text:None})
            for child_idx1 in range(top_item.childCount()):
                child_item1 = top_item.child(child_idx1)
                ci1_text = child_item1.text(0)
                if child_item1.childCount() == 0:
                    if type(new_dict[ti_text]) is list:
                        new_dict[ti_text].append(ci1_text)
                    else:
                        new_dict.update({ti_text: [ci1_text]})
                else:
                    if type(new_dict[ti_text]) is dict:
                        new_dict[ti_text].update({ci1_text: None})
                    else:
                        new_dict[ti_text] = {ci1_text: None}
                    for child_idx2 in range(child_item1.childCount()):
                        child_item2 = child_item1.child(child_idx2)
                        ci2_text = child_item2.text(0)
                        if child_item2.childCount() == 0:
                            if type(new_dict[ti_text][ci1_text]) is list:
                                new_dict[ti_text][ci1_text].append(ci2_text)
                            else:
                                new_dict[ti_text].update({ci1_text: [ci2_text]})
                        else:
                            if type(new_dict[ti_text][ci1_text]) is dict:
                                new_dict[ti_text][ci1_text].update({ci2_text: None})
                            else:
                                new_dict[ti_text][ci1_text] = {ci2_text: None}
                            for child_idx3 in range(child_item2.childCount()):
                                child_item3 = child_item2.child(child_idx3)
                                ci3_text = child_item3.text(0)
                                if type(new_dict[ti_text][ci1_text][ci2_text]) is list:
                                    new_dict[ti_text][ci1_text][ci2_text].append(ci3_text)
                                else:
                                    new_dict[ti_text][ci1_text].update({ci2_text: [ci3_text]})

    def add_group(self):
        group_name = QInputDialog.getText(self, 'Enter Group', 'Enter the name for a group:', text='group-name')
        if group_name:
            self.treew.addTopLevelItem(0, group_name)
            self.mw.pr.grand_avg_dict.update({group_name: None})

    def add_sub_group(self):
        pass

app = QApplication(sys.argv)
a = None
win = GrandAvgWidget(a)
win.show()

sys.exit(app.exec_())
