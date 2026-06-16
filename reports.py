import csv
from pathlib import Path
from datetime import datetime

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
    QMessageBox,
)
from PySide6.QtCore import QDate, Qt
from database import conectar


class RelatorioWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Histórico e Gestão de Ensaios")
        self.setMinimumSize(1100, 700)

        # Lista usada para exportar exatamente os dados filtrados/exibidos
        self.dados_filtrados = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "background-color: #f8f9fa; border-radius: 10px; border: 1px solid #dee2e6;"
        )
        filter_layout = QVBoxLayout(filter_frame)

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

        search_row = QHBoxLayout()
        self.search_sn = QLineEdit()
        self.search_sn.setPlaceholderText("🔍 Digite o Número de Série para buscar...")
        self.search_sn.setStyleSheet(
            "padding: 8px; font-size: 14px; border: 1px solid #ced4da;"
        )
        self.search_sn.textChanged.connect(self.carregar_dados)

        self.btn_filtrar = QPushButton("⚡ Atualizar Lista")
        self.btn_filtrar.setStyleSheet(
            """
            QPushButton {
                background-color: #0d6efd;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            """
        )
        self.btn_filtrar.clicked.connect(self.carregar_dados)

        search_row.addWidget(QLabel("<b>Busca S/N:</b>"))
        search_row.addWidget(self.search_sn)
        search_row.addWidget(self.btn_filtrar)
        filter_layout.addLayout(search_row)

        self.main_layout.addWidget(filter_frame)

        self.label_resumo = QLabel("Mostrando: 0 testes encontrados")
        self.label_resumo.setStyleSheet(
            "font-size: 13px; color: #666; font-style: italic;"
        )
        self.main_layout.addWidget(self.label_resumo)

        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Data/Hora", "Nº SÉRIE", "Operador", "Resultado", "Relatório Bruto"]
        )

        header = self.tabela.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.main_layout.addWidget(self.tabela)

        # Botão reaproveitado: antes era PDF, agora exporta CSV
        self.btn_imprimir = QPushButton("📄 Exportar relatório CSV")
        self.btn_imprimir.setMinimumHeight(45)
        self.btn_imprimir.setEnabled(True)
        self.btn_imprimir.setStyleSheet(
            "background-color: #198754; color: white; font-weight: bold; border-radius: 8px;"
        )
        self.btn_imprimir.clicked.connect(self.exportar_relatorio_csv)
        self.main_layout.addWidget(self.btn_imprimir)

        self.carregar_dados()

    def carregar_dados(self):
        """Busca dados filtrando por data, status e número de série."""
        self.tabela.setRowCount(0)
        self.dados_filtrados = []

        conn = conectar()
        cursor = conn.cursor()

        status_sel = self.combo_status.currentText()
        busca_sn = self.search_sn.text().strip()

        query = """
            SELECT
                id,
                data_hora,
                numero_serie,
                operador,
                resultado,
                relatorio,
                porta_com,
                baudrate
            FROM testes_hipot
            WHERE 1=1
        """
        params = []

        if "APROVADO" in status_sel:
            query += " AND resultado = 'APROVADO'"
        elif "REPROVADO" in status_sel:
            query += " AND resultado = 'REPROVADO'"

        if busca_sn:
            query += " AND numero_serie LIKE ?"
            params.append(f"%{busca_sn}%")

        query += " ORDER BY id DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        d_inicio = self.data_inicio.date()
        d_fim = self.data_fim.date()
        testes_filtrados = 0

        for row_data in rows:
            data_str = row_data[1].split(" ")[0]
            data_objeto = QDate.fromString(data_str, "dd/MM/yyyy")

            if data_objeto >= d_inicio and data_objeto <= d_fim:
                testes_filtrados += 1

                registro = {
                    "id": row_data[0],
                    "data_hora": row_data[1],
                    "numero_serie": row_data[2],
                    "operador": row_data[3],
                    "resultado": row_data[4],
                    "relatorio": row_data[5],
                    "porta_com": row_data[6],
                    "baudrate": row_data[7],
                }

                self.dados_filtrados.append(registro)

                row_idx = self.tabela.rowCount()
                self.tabela.insertRow(row_idx)

                dados_tabela = row_data[:6]

                for col_idx, data in enumerate(dados_tabela):
                    item = QTableWidgetItem(str(data))

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

    def exportar_relatorio_csv(self):
        """Exporta os dados atualmente filtrados para CSV."""

        if not self.dados_filtrados:
            QMessageBox.information(
                self,
                "Exportação CSV",
                "Nenhum dado disponível para exportação.",
            )
            return

        pasta_exportacao = Path("data") / "hipot" / "exports"
        pasta_exportacao.mkdir(parents=True, exist_ok=True)

        nome_arquivo = f"relatorio_hipot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        caminho_arquivo = pasta_exportacao / nome_arquivo

        colunas = [
            "id",
            "data_hora",
            "numero_serie",
            "operador",
            "resultado",
            "relatorio",
            "porta_com",
            "baudrate",
        ]

        # utf-8-sig facilita abertura correta no Excel
        with open(caminho_arquivo, mode="w", encoding="utf-8-sig", newline="") as arquivo:
            writer = csv.DictWriter(arquivo, fieldnames=colunas, delimiter=";")
            writer.writeheader()
            writer.writerows(self.dados_filtrados)

        QMessageBox.information(
            self,
            "Exportação concluída",
            f"Relatório CSV gerado com sucesso:\n\n{caminho_arquivo.resolve()}",
        )  