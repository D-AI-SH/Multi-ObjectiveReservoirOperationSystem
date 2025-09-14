from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QFileDialog, QMessageBox
from PyQt6.QtGui import QFont, QMouseEvent
from PyQt6.QtCore import Qt, QEvent
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas


class IntegratedChartWidget(QWidget):
    """集成在标签页内的图表组件。"""

    def __init__(self, title: str, data: Any, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.title = title
        self.data = data
        self.is_dragging = False
        self.drag_start_y = 0
        self.original_height = 400
        self.min_height = 240
        self.max_height = 1200

        # 图像尺寸
        self.base_width_inch = 8.0
        self.base_height_inch = 4.5

        self._init_ui()
        self.plot_data()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标题栏
        title_bar = QHBoxLayout()
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        # 尺寸控制与保存
        save_btn = QPushButton("保存图片")
        save_btn.clicked.connect(self.save_figure)
        title_bar.addWidget(save_btn)

        height_btn = QPushButton("拖拽调高")
        height_btn.setToolTip("按住图表区域底部上下拖拽可调高度")
        height_btn.clicked.connect(self.toggle_height_adjustment)
        title_bar.addWidget(height_btn)
        layout.addLayout(title_bar)

        # 图表区域
        self.chart_frame = QFrame()
        self.chart_frame.setFrameStyle(QFrame.Shape.Box)
        self.chart_frame.setMinimumHeight(self.min_height)
        self.chart_frame.setMaximumHeight(self.max_height)

        # 创建 matplotlib 图表
        self.figure = Figure(figsize=(self.base_width_inch, self.base_height_inch), dpi=100)
        self.canvas = FigureCanvas(self.figure)

        chart_layout = QVBoxLayout(self.chart_frame)
        chart_layout.addWidget(self.canvas)
        layout.addWidget(self.chart_frame)

        # 事件过滤器处理拖拽
        self.chart_frame.setMouseTracking(True)
        self.chart_frame.installEventFilter(self)

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------
    def _handle_mouse_press(self, event: QMouseEvent | None) -> None:
        if event and event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_y = event.globalPosition().y()
            self.original_height = self.chart_frame.height()

    def _handle_mouse_move(self, event: QMouseEvent | None) -> None:
        if self.is_dragging and event:
            current_y = event.globalPosition().y()
            delta_y = current_y - self.drag_start_y
            new_height = max(self.min_height, min(self.max_height, self.original_height + int(delta_y)))
            self.chart_frame.setFixedHeight(new_height)
            # 以当前画布宽度与DPI换算宽度英寸，保持宽度不变，仅按高度像素设置高度英寸
            dpi = self.figure.get_dpi()
            width_inch = max(1.0, self.canvas.width() / dpi)
            height_inch = max(1.5, new_height / dpi)
            self.figure.set_size_inches(width_inch, height_inch)
            self.canvas.draw()

    def _handle_mouse_release(self, event: QMouseEvent | None) -> None:
        if event and event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

    def eventFilter(self, obj, event):  # type: ignore[override]
        if obj is self.chart_frame:
            et = event.type()
            if et == QEvent.Type.MouseButtonPress:
                self._handle_mouse_press(event)
                return True
            if et == QEvent.Type.MouseMove:
                self._handle_mouse_move(event)
                return True
            if et == QEvent.Type.MouseButtonRelease:
                self._handle_mouse_release(event)
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # 绘图
    # ------------------------------------------------------------------
    def plot_data(self) -> None:
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)

            if isinstance(self.data, pd.Series):
                series = pd.to_numeric(self.data, errors='coerce').dropna()
                y_vals = series.astype(float).tolist()
                x_vals = list(range(len(y_vals)))
                ax.plot(x_vals, y_vals, color='b', linewidth=2, alpha=0.7)
                ax.set_xlabel('时间步')
                ax.set_ylabel('数值')
                ax.set_title(self.title, fontsize=12, fontweight='bold')
                ax.grid(True, alpha=0.3)

            elif isinstance(self.data, pd.DataFrame):
                for col in self.data.columns:
                    col_series = pd.to_numeric(self.data[col], errors='coerce').dropna()
                    if len(col_series) == 0:
                        continue
                    y_vals = col_series.astype(float).tolist()
                    x_vals = list(range(len(y_vals)))
                    ax.plot(x_vals, y_vals, label=col, linewidth=2, alpha=0.7)
                ax.set_xlabel('时间步')
                ax.set_ylabel('数值')
                ax.set_title(self.title, fontsize=12, fontweight='bold')
                ax.legend()
                ax.grid(True, alpha=0.3)

            # 应用当前缩放的尺寸
            self._apply_figure_size()
            self.canvas.draw()

        except Exception as e:
            print(f"绘制图表时出错: {str(e)}")

    # ------------------------------------------------------------------
    # 其他
    # ------------------------------------------------------------------
    def toggle_height_adjustment(self) -> None:
        # 提示性质按钮，不改变布局，仅确保最大高度范围
        self.chart_frame.setMinimumHeight(self.min_height)
        self.chart_frame.setMaximumHeight(self.max_height)

    def resizeEvent(self, event):  # type: ignore[override]
        # 窗口变化时保持当前缩放比例下的合适高度，不强制16:9
        super().resizeEvent(event)
        dpi = self.figure.get_dpi()
        _, height_inch = self.figure.get_size_inches()
        target_height_px = int(height_inch * dpi)
        self.chart_frame.setFixedHeight(max(self.min_height, min(self.max_height, target_height_px)))

    # ------------------------------------------------------------------
    # 尺寸与保存
    # ------------------------------------------------------------------
    def _apply_figure_size(self) -> None:
        # 使用固定尺寸，不再支持缩放
        self.figure.set_size_inches(self.base_width_inch, self.base_height_inch)
        dpi = self.figure.get_dpi()
        self.chart_frame.setFixedHeight(max(self.min_height, min(self.max_height, int(self.base_height_inch * dpi))))

    def save_figure(self) -> None:
        try:
            default_name = f"{self.title}.png".replace("/", "-")
            file_path, _ = QFileDialog.getSaveFileName(self, "保存图像", default_name, "PNG 图片 (*.png);;JPEG 图片 (*.jpg *.jpeg);;PDF 文件 (*.pdf)")
            if not file_path:
                return
            # 高质量保存
            self.figure.savefig(file_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
            QMessageBox.information(self, "保存成功", f"已保存到:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存图像时发生错误:\n{str(e)}")


