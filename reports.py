from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QDateEdit,
    QComboBox,
    QPushButton,
    QLabel,
    QHeaderView,
    QFrame,
    QLineEdit,
)
from PySide6.QtCore import QDate, Qt
from database import conectar


class RelatorioWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Histórico e Gestão de Ensaios")
        self.setMinimumSize(1100, 700)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # ======================================================
        # PAINEL DE FILTROS E BUSCA (CAPRICHADO)
        # ======================================================
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "background-color: #f8f9fa; border-radius: 10px; border: 1px solid #dee2e6;"
        )
        filter_layout = QVBoxLayout(filter_frame)

        # Linha 1: Datas e Status
        top_row = QHBoxLayout()
        self.data_inicio = QDateEdit(QDate.currentDate().addDays(-30))
        self.data_inicio.setCalendarPopup(True)
        self.data_fim = QDateEdit(QDate.currentDate())
        self.data_fim.setCalendarPopup(True)
        self.combo_status = QComboBox()
        self.combo_status.addItems(
            ["🔍 Todos os Resultados", "✅ APROVADO", "❌ REPROVADO"]
        )

        top_row.addWidget(QLabel("<b>De:</b>"))
        top_row.addWidget(self.data_inicio)
        top_row.addWidget(QLabel("<b>Até:</b>"))
        top_row.addWidget(self.data_fim)
        top_row.addWidget(QLabel("  <b>Status:</b>"))
        top_row.addWidget(self.combo_status)
        top_row.addStretch()
        filter_layout.addLayout(top_row)

        # Linha 2: Busca por Número de Série
        search_row = QHBoxLayout()
        self.search_sn = QLineEdit()
        self.search_sn.setPlaceholderText("🔍 Digite o Número de Série para buscar...")
        self.search_sn.setStyleSheet(
            "padding: 8px; font-size: 14px; border: 1px solid #ced4da;"
        )
        self.search_sn.textChanged.connect(self.carregar_dados)  # Busca enquanto digita

        self.btn_filtrar = QPushButton("⚡ Atualizar Lista")
        self.btn_filtrar.setStyleSheet(
            """
            QPushButton { background-color: #0d6efd; color: white; font-weight: bold; border-radius: 5px; padding: 8px 20px; }
            QPushButton:hover { background-color: #0b5ed7; }
        """
        )
        self.btn_filtrar.clicked.connect(self.carregar_dados)

        search_row.addWidget(QLabel("<b>Busca S/N:</b>"))
        search_row.addWidget(self.search_sn)
        search_row.addWidget(self.btn_filtrar)
        filter_layout.addLayout(search_row)

        self.main_layout.addWidget(filter_frame)

        # KPI de Resumo
        self.label_resumo = QLabel("Mostrando: 0 testes encontrados")
        self.label_resumo.setStyleSheet(
            "font-size: 13px; color: #666; font-style: italic;"
        )
        self.main_layout.addWidget(self.label_resumo)

        # ======================================================
        # TABELA DE DADOS (AGORA COM 6 COLUNAS)
        # ======================================================
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Data/Hora", "Nº SÉRIE", "Operador", "Resultado", "Relatório Bruto"]
        )

        header = self.tabela.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # S/N em destaque
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Relatório expandido

        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.main_layout.addWidget(self.tabela)

        # Botão Imprimir
        self.btn_imprimir = QPushButton("🖨️ Gerar Relatório de Impressão (PDF)")
        self.btn_imprimir.setMinimumHeight(45)
        self.btn_imprimir.setStyleSheet(
            "background-color: #198754; color: white; font-weight: bold; border-radius: 8px;"
        )
        self.btn_imprimir.clicked.connect(self.imprimir_relatorio)
        self.main_layout.addWidget(self.btn_imprimir)

        self.carregar_dados()

    def carregar_dados(self):
        """Busca dados filtrando por Data, Status e Número de Série."""
        self.tabela.setRowCount(0)
        conn = conectar()
        cursor = conn.cursor()

        status_sel = self.combo_status.currentText()
        busca_sn = self.search_sn.text().strip()

        # Query base buscando a nova coluna numero_serie
        query = "SELECT id, data_hora, numero_serie, operador, resultado, relatorio FROM testes_hipot WHERE 1=1"
        params = []

        if "APROVADO" in status_sel:
            query += " AND resultado = 'APROVADO'"
        elif "REPROVADO" in status_sel:
            query += " AND resultado = 'REPROVADO'"

        if busca_sn:
            query += " AND numero_serie LIKE ?"
            params.append(f"%{busca_sn}%")

        cursor.execute(query, params)
        rows = cursor.fetchall()

        d_inicio = self.data_inicio.date()
        d_fim = self.data_fim.date()
        testes_filtrados = 0

        for row_data in rows:
            data_str = row_data[1].split(" ")[0]
            data_objeto = QDate.fromString(data_str, "dd/MM/yyyy")

            if data_objeto >= d_inicio and data_objeto <= d_fim:
                row_idx = self.tabela.rowCount()
                self.tabela.insertRow(row_idx)
                testes_filtrados += 1

                for col_idx, data in enumerate(row_data):
                    item = QTableWidgetItem(str(data))

                    # Estilização do Resultado (Coluna 4 agora)
                    if col_idx == 4:
                        if data == "APROVADO":
                            item.setForeground(Qt.darkGreen)
                            item.setText("✅ APROVADO")
                        else:
                            item.setForeground(Qt.red)
                            item.setText("❌ REPROVADO")
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)

                    item.setTextAlignment(Qt.AlignCenter)
                    self.tabela.setItem(row_idx, col_idx, item)

        self.label_resumo.setText(
            f"📋 Filtro aplicado: {testes_filtrados} testes encontrados."
        )
        conn.close()

    def imprimir_relatorio(self):
        # Lógica de impressão (PDF)
        pass
