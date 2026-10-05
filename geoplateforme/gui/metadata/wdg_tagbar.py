from functools import partial

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class TagBarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.h_layout = QHBoxLayout()
        self.h_layout.setSpacing(4)
        self.setLayout(self.h_layout)
        self.combobox = QComboBox()
        self.combobox.setEditable(True)
        self.combobox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combobox.completer().setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.combobox.setCurrentIndex(-1)
        self.combobox.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum
        )
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.setContentsMargins(2, 2, 2, 2)
        self.h_layout.setContentsMargins(2, 2, 2, 2)

    def setup_ui(self):
        self.combobox.currentIndexChanged.connect(self.create_tag_from_value)

    def create_tag_from_value(self, index): ...

    def create_tags(self, tags):
        if len(tags) > 0:
            new_tags = [tag for tag in tags if self.is_valid_tag(tag)]
            self.combobox.setCurrentIndex(-1)
            self.tags.extend(new_tags)
            self.tags = list(set(self.tags))
            self.tags.sort(key=lambda x: x.lower())
            self.refresh()

    def refresh(self): ...

    def add_tag_to_bar(self, text):
        tag = QFrame()
        tag.setStyleSheet("border:1px solid rgb(192, 192, 192); border-radius: 4px;")
        tag.setContentsMargins(2, 2, 2, 2)
        tag.setFixedHeight(28)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(4, 4, 4, 4)
        hbox.setSpacing(10)
        tag.setLayout(hbox)
        label = QLabel(text)
        label.setStyleSheet("border:0px")
        label.setFixedHeight(16)
        hbox.addWidget(label)
        x_button = QPushButton("x")
        x_button.setFixedSize(20, 20)
        x_button.setStyleSheet("border:0px; font-weight:bold")
        x_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        x_button.clicked.connect(partial(self.delete_tag, text))
        hbox.addWidget(x_button)
        tag.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.h_layout.addWidget(tag)

    def clear(self):
        self.tags = []
        self.refresh()

    def delete_tag(self, tag_name): ...

    def is_valid_tag(self, tag_name) -> bool:
        return True


class DictTagBarWidget(TagBarWidget):
    def __init__(self, items: dict):
        super().__init__()

        # Sort items by value
        self.items = dict(sorted(items.items(), key=lambda item: item[1]))

        self.combobox.addItems([v for v in self.items.values()])
        self.combobox.setCurrentIndex(-1)
        self.refresh()
        self.setup_ui()
        self.show()

    def create_tag_from_value(self, index):
        if index >= 0:
            tag_key = list(self.items.keys())[index]
            self.create_tags([tag_key])

    def refresh(self):
        for i in reversed(range(self.h_layout.count())):
            self.h_layout.itemAt(i).widget().setParent(None)
        for tag in self.tags:
            self.add_tag_to_bar(self.items[tag])
        self.h_layout.addWidget(self.combobox)
        self.combobox.setFocus()

    def delete_tag(self, tag_name):
        tag_key = list(self.items.keys())[list(self.items.values()).index(tag_name)]
        self.tags.remove(tag_key)
        self.refresh()

    def is_valid_tag(self, tag_name) -> bool:
        if tag_name in self.items:
            return True
        else:
            return False


class ListTagBarWidget(TagBarWidget):
    def __init__(self, items: list):
        super().__init__()
        self.items = items
        self.combobox.addItems(self.items)
        self.combobox.setCurrentIndex(-1)
        self.refresh()
        self.setup_ui()
        self.show()

    def create_tag_from_value(self, index):
        if index >= 0:
            tag_key = self.items[index]
            self.create_tags([tag_key])

    def refresh(self):
        for i in reversed(range(self.h_layout.count())):
            self.h_layout.itemAt(i).widget().setParent(None)
        for tag in self.tags:
            self.add_tag_to_bar(tag)
        self.h_layout.addWidget(self.combobox)
        self.combobox.setFocus()

    def delete_tag(self, tag_name):
        self.tags.remove(tag_name)
        self.refresh()

    def is_valid_tag(self, tag_name) -> bool:
        if tag_name in self.items:
            return True
        else:
            return False
