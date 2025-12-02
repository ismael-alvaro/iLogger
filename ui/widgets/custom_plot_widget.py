# iLogger/ui/widgets/custom_plot_widget.py

import pyqtgraph as pg
from pyqtgraph import exporters
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel, QGridLayout, QLineEdit
from PyQt6.QtCore import Qt
from config import CUSTOM_PLOT_AXES_OPTIONS
import numpy as np

class CustomPlotWidget(QWidget):
    """
    Widget para a aba de Gráfico Personalizado, usando pyqtgraph
    e suportando um segundo eixo Y.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_state = None
        # Mapeamentos customizados: nome exibido -> nome da coluna CSV
        self.custom_mappings = {}
        
        main_layout = QVBoxLayout(self)
        controls_layout = QGridLayout()

        # --- Controles ---
        axes_options_with_none = [""] + CUSTOM_PLOT_AXES_OPTIONS
        self.combo_x = QComboBox()
        self.combo_y1 = QComboBox()
        self.combo_y2 = QComboBox()
        self.combo_x.addItems(CUSTOM_PLOT_AXES_OPTIONS)
        self.combo_y1.addItems(CUSTOM_PLOT_AXES_OPTIONS)
        self.combo_y2.addItems(axes_options_with_none)
        self.btn_update = QPushButton("Atualizar Gráfico")
        # Controles para adicionar mapeamentos customizados
        self.line_name = QLineEdit()
        self.line_name.setPlaceholderText("Nome a exibir (ex: MeuSensor)")
        self.combo_columns = QComboBox()
        self.btn_add_mapping = QPushButton("Adicionar Mapeamento")
        self.lbl_mappings = QLabel("Mapeamentos: Nenhum")

        # --- Layout dos Controles ---
        controls_layout.addWidget(QLabel("Eixo X:"), 0, 0)
        controls_layout.addWidget(self.combo_x, 0, 1)
        controls_layout.addWidget(QLabel("Eixo Y (Primário):"), 1, 0)
        controls_layout.addWidget(self.combo_y1, 1, 1)
        controls_layout.addWidget(QLabel("Eixo Y (Secundário - Opcional):"), 2, 0)
        controls_layout.addWidget(self.combo_y2, 2, 1)
        controls_layout.addWidget(self.btn_update, 3, 0, 1, 2)
        # Linha para criar mapeamentos entre nome exibido e coluna do CSV
        controls_layout.addWidget(QLabel("Nome do Dado:"), 4, 0)
        controls_layout.addWidget(self.line_name, 4, 1)
        controls_layout.addWidget(QLabel("Coluna CSV (cabeçalho):"), 5, 0)
        controls_layout.addWidget(self.combo_columns, 5, 1)
        controls_layout.addWidget(self.btn_add_mapping, 6, 0, 1, 2)
        controls_layout.addWidget(self.lbl_mappings, 7, 0, 1, 2)
        
        # --- Widget de Gráfico (pyqtgraph) ---
        self.plot_widget = pg.PlotWidget()
        
        # --- OTIMIZAÇÃO DE RENDERIZAÇÃO ---
        self.plot_widget.getPlotItem().setDownsampling(mode='peak')
        self.plot_widget.getPlotItem().setClipToView(True)
        # ---------------------------------
        
        self.p1 = self.plot_widget.getPlotItem()
        self.legend = self.p1.addLegend()
        
        # Configuração do segundo eixo Y
        self.p2 = pg.ViewBox()
        self.p1.showAxis('right')
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis('right').linkToView(self.p2)
        self.p2.setXLink(self.p1)
        
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.plot_widget)
        
        self.btn_update.clicked.connect(self.update_plot)
        self.btn_add_mapping.clicked.connect(self.add_mapping)
        self.p1.vb.sigResized.connect(self._update_views)

    def link_state(self, app_state):
        """
        Linka o estado da aplicação e atualiza a lista de colunas disponíveis quando
        novos dados são carregados.
        """
        self.app_state = app_state
        # conecta sinal para atualizar colunas
        try:
            self.app_state.data_loaded.connect(self._refresh_available_columns)
        except Exception:
            pass
        # Inicializa lista de colunas caso já haja dados
        self._refresh_available_columns()

    def _refresh_available_columns(self):
        """Preenche `self.combo_columns` com os nomes de colunas do primeiro run (se houver)."""
        self.combo_columns.clear()
        if not self.app_state or not self.app_state.raw_runs:
            return
        # Usa as colunas do primeiro Run carregado
        first_run = self.app_state.raw_runs[0]
        cols = list(first_run.df_raw.columns)
        self.combo_columns.addItems(cols)

    def add_mapping(self):
        """Adiciona um mapeamento (nome exibido -> coluna CSV) e atualiza os combos."""
        name = self.line_name.text().strip()
        col = self.combo_columns.currentText().strip()
        if not name or not col:
            return
        # armazena mapeamento
        self.custom_mappings[name] = col
        # adiciona o nome personalizado aos combos de seleção do gráfico, se ainda não existir
        for combo in (self.combo_x, self.combo_y1, self.combo_y2):
            if name and combo.findText(name) == -1:
                combo.addItem(name)
        # atualiza label com os mapeamentos atuais
        mappings_text = ", ".join([f"{k} -> {v}" for k, v in self.custom_mappings.items()])
        self.lbl_mappings.setText(f"Mapeamentos: {mappings_text}")
        # limpa o campo de texto
        self.line_name.clear()

    def _update_views(self):
        """Sincroniza a geometria da ViewBox secundária com a primária."""
        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
        self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)

        
    def update_plot(self):
        if not self.app_state: return

        self._clear_plots()
        x_key, y1_key, y2_key = self.combo_x.currentText(), self.combo_y1.currentText(), self.combo_y2.currentText()

        # Resolve chaves customizadas para nomes de colunas do CSV quando aplicável
        def resolve_key(k):
            return self.custom_mappings.get(k, k)

        x_key_resolved = resolve_key(x_key)
        y1_key_resolved = resolve_key(y1_key)
        y2_key_resolved = resolve_key(y2_key) if y2_key else ''
        
        # Usa os rótulos de exibição (nome escolhido pelo usuário) para os eixos
        self.p1.setLabel('bottom', x_key)
        self.p1.setLabel('left', y1_key)
        self.p1.setTitle(f"Gráfico Personalizado", size='14pt')
        self.p1.showGrid(x=True, y=True, alpha=0.3)
        
        if not self.app_state.raw_runs:
            self.p1.addItem(pg.TextItem("Sem dados para exibir", anchor=(0.5, 0.5), color='k'))
            return
        
        pens = [pg.mkPen(color=c, width=2) for c in ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']]
        
        for i, run in enumerate(self.app_state.raw_runs):
            x_data, y_data = run.get_data_for_custom_plot(x_key_resolved), run.get_data_for_custom_plot(y1_key_resolved)
            min_len = min(len(x_data), len(y_data))
            if min_len > 0:
                self.p1.plot(x_data[:min_len], y_data[:min_len], pen=pens[i % len(pens)], name=f"{y1_key} ({run.file_name})")
        
        if y2_key:
            self.p1.getAxis('right').show()
            self.p1.setLabel('right', y2_key)
            self.p2.setVisible(True)

            for i, run in enumerate(self.app_state.raw_runs):
                x_data, y_data = run.get_data_for_custom_plot(x_key_resolved), run.get_data_for_custom_plot(y2_key_resolved)
                min_len = min(len(x_data), len(y_data))
                if min_len > 0:
                    item = pg.PlotDataItem(x_data[:min_len], y_data[:min_len], pen=pg.mkPen(pens[i % len(pens)], style=Qt.PenStyle.DashLine), name=f"{y2_key} ({run.file_name})")
                    self.p2.addItem(item)
        else:
            self.p1.getAxis('right').hide()
            self.p2.setVisible(False)
        
        self._update_views()

    def _clear_plots(self):
        self.p1.clear()
        self.p2.clear()
        if self.legend:
            self.legend.clear()

    def get_figure_for_report(self):
        """Exporta o layout gráfico atual como uma imagem."""
        exporter = exporters.ImageExporter(self.plot_widget.scene())
        return exporter.export(toBytes=True)