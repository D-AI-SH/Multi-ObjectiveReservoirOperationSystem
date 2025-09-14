STYLE = """
/* 全局字体与字号 */
* {
    font-family: "Microsoft YaHei";
    font-size: 12px;
    color: #333333;              /* 全局黑色文字 */
}

/* -------------------- 主窗口 -------------------- */
QMainWindow {
    background-color: #FFFFFF;   /* 白色背景 */
    color: #333333;              /* 黑色文字 */
}

QWidget {
    background-color: #FFFFFF;   /* 所有控件默认白色背景 */
    color: #333333;              /* 所有控件默认黑色文字 */
}

/* -------------------- 对话框 -------------------- */
QDialog {
    background-color: #FFFFFF;
    color: #333333;
    border: 1px solid #CCCCCC;
}

QDialogButtonBox QPushButton {
    background-color: #F5F5F5;
    color: #333333;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 60px;
}

QDialogButtonBox QPushButton:hover {
    background-color: #3A6FE2;
    color: #FFFFFF;
}

/* -------------------- 消息框 -------------------- */
QMessageBox {
    background-color: #FFFFFF;
    color: #333333;
}

QMessageBox QLabel {
    color: #333333;
    background-color: transparent;
}

QMessageBox QPushButton {
    background-color: #F5F5F5;
    color: #333333;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 60px;
}

QMessageBox QPushButton:hover {
    background-color: #3A6FE2;
    color: #FFFFFF;
}

/* -------------------- 标签 -------------------- */
QLabel {
    color: #333333;
    background-color: transparent;
}

/* -------------------- TabWidget -------------------- */
QTabWidget::pane {
    border: 1px solid #CCCCCC;   /* 浅色边框 */
    background-color: #FFFFFF;
}

QTabBar::tab {
    background: #F5F5F5;
    color: #333333;
    padding: 6px 12px;
    border: 1px solid #CCCCCC;
    border-bottom: none;         /* 与面板无缝衔接 */
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected, QTabBar::tab:hover {
    background: #3A6FE2;        /* 保持蓝色强调色 */
    color: #FFFFFF;
}

/* -------------------- 按钮 -------------------- */
QPushButton {
    background-color: #F5F5F5;
    color: #333333;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 4px 8px;
}

QPushButton:hover {
    background-color: #3A6FE2;    /* 保持蓝色强调色 */
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #2B57C1;    /* 保持蓝色强调色深色版本 */
    color: #FFFFFF;
}

QPushButton:disabled {
    background-color: #E9ECEF;
    color: #6C757D;
    border: 1px solid #DEE2E6;
}

/* -------------------- 橙色强调按钮 -------------------- */
QPushButton[class="accent-orange"] {
    background-color: #FF6B35;    /* 橙色强调色 */
    color: #FFFFFF;
}

QPushButton[class="accent-orange"]:hover {
    background-color: #E55A2B;
}

QPushButton[class="accent-orange"]:pressed {
    background-color: #CC4A21;
}

/* -------------------- 下拉框 -------------------- */
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 2px 4px;
    color: #333333;
    min-width: 60px;
}

QComboBox:hover {
    border: 1px solid #3A6FE2;   /* 悬停时显示蓝色强调色 */
}

QComboBox:focus {
    border: 2px solid #3A6FE2;   /* 聚焦时显示蓝色强调色 */
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-left-width: 1px;
    border-left-color: #CCCCCC;
    border-left-style: solid;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
    background-color: #F5F5F5;
}

QComboBox::down-arrow {
    image: none;
    border: 2px solid #666666;
    width: 6px;
    height: 6px;
    border-top: none;
    border-right: none;
    transform: rotate(45deg);
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    color: #333333;
    selection-background-color: #3A6FE2;
    selection-color: #FFFFFF;
    outline: none;
}

/* -------------------- 菜单 -------------------- */
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    color: #333333;
    padding: 2px;
}

QMenu::item {
    background-color: transparent;
    padding: 4px 16px;
    color: #333333;
}

QMenu::item:selected {
    background-color: #3A6FE2;
    color: #FFFFFF;
}

QMenu::separator {
    height: 1px;
    background-color: #DDDDDD;
    margin: 2px 0px;
}

/* -------------------- 分割条 -------------------- */
QSplitter::handle {
    background-color: #DDDDDD;
}

/* -------------------- Tree / List -------------------- */
QTreeView, QTreeWidget, QListView, QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    color: #333333;
    alternate-background-color: #F8F9FA;
}

QTreeView::item:selected, QTreeWidget::item:selected,
QListView::item:selected, QListWidget::item:selected {
    background-color: #3A6FE2;    /* 保持蓝色强调色 */
    color: #FFFFFF;
}

QTreeView::item:hover, QTreeWidget::item:hover,
QListView::item:hover, QListWidget::item:hover {
    background-color: #E3F2FD;
    color: #333333;
}

/* -------------------- 表格 -------------------- */
QTableView, QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    gridline-color: #DDDDDD;
    selection-background-color: #3A6FE2;    /* 保持蓝色强调色 */
    selection-color: #FFFFFF;
    color: #333333;
    alternate-background-color: #F8F9FA;
}

QHeaderView::section {
    background-color: #F5F5F5;
    color: #333333;
    padding: 4px;
    border: 1px solid #CCCCCC;
    font-weight: bold;
}

/* -------------------- 输入框 -------------------- */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 2px 4px;
    color: #333333;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border: 1px solid #3A6FE2;   /* 悬停时显示蓝色强调色 */
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #3A6FE2;   /* 聚焦时显示蓝色强调色 */
}

/* -------------------- 文本框 -------------------- */
QTextEdit, QPlainTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    color: #333333;
    padding: 4px;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #3A6FE2;
}

/* -------------------- 复选框和单选框 -------------------- */
QCheckBox, QRadioButton {
    color: #333333;
    background-color: transparent;
    spacing: 8px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    background-color: #FFFFFF;
    border: 2px solid #CCCCCC;
}

QCheckBox::indicator {
    border-radius: 3px;
}

QRadioButton::indicator {
    border-radius: 8px;
}

QCheckBox::indicator:checked {
    background-color: #3A6FE2;
    border-color: #3A6FE2;
}

QRadioButton::indicator:checked {
    background-color: #3A6FE2;
    border-color: #3A6FE2;
}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {
    border-color: #3A6FE2;
}

/* -------------------- 滚动条 -------------------- */
QScrollBar:vertical {
    background-color: #F5F5F5;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #CCCCCC;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #999999;
}

QScrollBar:horizontal {
    background-color: #F5F5F5;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #CCCCCC;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #999999;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}

/* -------------------- 进度条 -------------------- */
QProgressBar {
    border: 2px solid #CCCCCC;
    border-radius: 5px;
    text-align: center;
    background-color: #F5F5F5;
    color: #333333;
}

QProgressBar::chunk {
    background-color: #3A6FE2;
    border-radius: 3px;
}

/* -------------------- 滑块 -------------------- */
QSlider::groove:horizontal {
    border: 1px solid #CCCCCC;
    height: 6px;
    background-color: #F5F5F5;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #3A6FE2;
    border: 1px solid #3A6FE2;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}

QSlider::handle:horizontal:hover {
    background-color: #2B57C1;
}

/* -------------------- 分组框 -------------------- */
QGroupBox {
    color: #333333;
    border: 2px solid #CCCCCC;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    background-color: #FFFFFF;
    color: #333333;
}

/* -------------------- 状态栏 -------------------- */
QStatusBar {
    background-color: #F5F5F5;
    color: #333333;
    border-top: 1px solid #CCCCCC;
}

/* -------------------- 工具提示 -------------------- */
QToolTip {
    background-color: #FFFEF7;
    color: #333333;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 4px;
}

/* -------------------- 日期时间选择器 -------------------- */
QDateEdit, QTimeEdit, QDateTimeEdit {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 2px 4px;
    color: #333333;
}

QDateEdit:hover, QTimeEdit:hover, QDateTimeEdit:hover {
    border: 1px solid #3A6FE2;
}

QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {
    border: 2px solid #3A6FE2;
}

QCalendarWidget {
    background-color: #FFFFFF;
    color: #333333;
}

QCalendarWidget QAbstractItemView {
    background-color: #FFFFFF;
    color: #333333;
    selection-background-color: #3A6FE2;
    selection-color: #FFFFFF;
}

"""