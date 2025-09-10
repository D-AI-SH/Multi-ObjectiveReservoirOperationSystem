STYLE = """
/* 全局字体与字号 */
* {
    font-family: "Microsoft YaHei";
    font-size: 12px;
}

/* -------------------- 主窗口 -------------------- */
QMainWindow {
    background-color: #222222;   /* 深色背景 */
    color: #EEEEEE;              /* 亮色文字，可读性佳 */
}

/* -------------------- TabWidget -------------------- */
QTabWidget::pane {
    border: 1px solid #444444;   /* 外边框 */
}
QTabBar::tab {
    background: #333333;
    color: #CCCCCC;
    padding: 6px 12px;
    border: 1px solid #444444;
    border-bottom: none;         /* 与面板无缝衔接 */
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
    QTabBar::tab:selected, QTabBar::tab:hover {
        background: #3A6FE2;
        color: #FFFFFF;
    }

/* -------------------- 按钮 -------------------- */
QPushButton {
    background-color: #444444;
    color: #DDDDDD;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 8px;
}
QPushButton:hover {
    background-color: #3A6FE2;
}
QPushButton:pressed {
    background-color: #2B57C1;
}

/* -------------------- 分割条 -------------------- */
QSplitter::handle {
    background-color: #444444;
}

/* -------------------- Tree / List -------------------- */
QTreeView, QTreeWidget {
    background-color: #2B2B2B;
    border: 1px solid #444444;
}
    QTreeView::item:selected, QTreeWidget::item:selected {
    background-color: #3A6FE2;
    color: #FFFFFF;
}

/* -------------------- 表格 -------------------- */
QTableView {
    background-color: #2B2B2B;
    border: 1px solid #444444;
    gridline-color: #444444;
    selection-background-color: #3A6FE2;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background-color: #2B2B2B;
    color: #CCCCCC;
    padding: 4px;
    border: 1px solid #444444;
}

/* -------------------- 输入框 -------------------- */
QLineEdit, QComboBox, QSpinBox {
    background-color: #333333;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px 4px;
    color: #EEEEEE;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {
    border: 1px solid #888888;
}

"""