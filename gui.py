from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QComboBox,
    QPushButton,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt
import re
from reports import RelatorioWindow
from operators import OPERADORES
from logger import Logger
from serial_worker import SerialWorker
from database import salvar_teste, criar_tabela

# Configurações globais de conexão física com o equipamento
PORTA = "COM3"
BAUDRATE = 9600


class HipotWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Inicializa a estrutura de dados local (SQLite) se não existir
        criar_tabela()

        self.setWindowTitle("HIPOT - Sistema de Ensaios Elétricos (Rastreabilidade)")
        self.setMinimumSize(800, 700)

        # =========================
        # LAYOUT PRINCIPAL
        # =========================
        layout = QVBoxLayout()

        # =========================
        # CABEÇALHO (STATUS + BOTÃO)
        # =========================
        header_layout = QHBoxLayout()

        self.status_label = QLabel("🟡 Aguardando início do teste...")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #333;"
        )

        self.btn_relatorios = QPushButton("📊 Consultar Relatórios")
        self.btn_relatorios.setMinimumHeight(40)
        self.btn_relatorios.clicked.connect(self.abrir_tela_relatorios)

        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_relatorios)
        layout.addLayout(header_layout)

        # =========================
        # IDENTIFICAÇÃO (S/N E OPERADOR)
        # =========================
        ident_layout = QHBoxLayout()

        # Campo de Número de Série (Obrigatório)
        sn_vbox = QVBoxLayout()
        sn_vbox.addWidget(QLabel("🆔 <b>NÚMERO DE SÉRIE (Obrigatório):</b>"))
        self.sn_input = QLineEdit()
        self.sn_input.setPlaceholderText("Digite ou bip o S/N aqui...")
        self.sn_input.setStyleSheet(
            "font-size: 16px; padding: 5px; border: 2px solid #0d6efd;"
        )
        sn_vbox.addWidget(self.sn_input)

        # Campo de Operador
        op_vbox = QVBoxLayout()
        op_vbox.addWidget(QLabel("👤 <b>Operador:</b>"))
        self.operador_combo = QComboBox()
        self.operador_combo.addItems(OPERADORES)
        self.operador_combo.setStyleSheet("font-size: 14px; padding: 5px;")
        op_vbox.addWidget(self.operador_combo)

        ident_layout.addLayout(sn_vbox, 2)  # S/N ganha mais espaço
        ident_layout.addLayout(op_vbox, 1)
        layout.addLayout(ident_layout)

        # =========================
        # ÁREA DE LOG
        # =========================
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(
            "background-color: #0d1117; color: #58a6ff; font-family: Consolas; font-size: 11px;"
        )
        layout.addWidget(self.log_area)

        self.setLayout(layout)

        # =========================
        # LOGGER E ESTADOS
        # =========================
        self.logger = Logger(self.adicionar_log)
        self.logger.log("Aplicação iniciada")
        self.linhas_acumuladas = []

        # =========================
        # WORKER SERIAL
        # =========================
        self.worker = SerialWorker(PORTA, BAUDRATE)
        self.worker.log.connect(self.logger.log)
        self.worker.status.connect(self.atualizar_status)
        self.worker.erro.connect(self.erro_serial)
        self.worker.dados_recebidos.connect(self.processar_dado)
        self.worker.start()

    def adicionar_log(self, texto):
        self.log_area.append(texto)

    def atualizar_status(self, texto):
        self.status_label.setText(texto)

    def processar_dado(self, linha):
        # Validação de Segurança: Se não digitou S/N, o sistema ignora dados e avisa
        if not self.sn_input.text().strip():
            self.status_label.setText("🛑 ERRO: Digite o S/N antes de iniciar!")
            return

        match = re.search(r'"(.*?)"', linha)
        if match:
            texto_limpo = match.group(1)

            if texto_limpo == "ENTRAN" and not self.linhas_acumuladas:
                separador = (
                    f"\n\n\n\n{'='*60}\n"
                    f"     :: NOVO ENSAIO INICIADO - S/N: {self.sn_input.text()} ::\n"
                    f"{'='*60}\n"
                )
                self.adicionar_log(separador)

            self.linhas_acumuladas.append(texto_limpo)

            if texto_limpo in ["APR", "REP"]:
                self.finalizar_e_salvar(texto_limpo)

    def finalizar_e_salvar(self, resultado_raw):
        # Bloqueio final de segurança
        numero_serie = self.sn_input.text().strip()
        if not numero_serie:
            QMessageBox.critical(
                self,
                "Erro de Rastreabilidade",
                "O teste terminou, mas o Número de Série não foi preenchido!",
            )
            return

        resultado = "APROVADO" if resultado_raw == "APR" else "REPROVADO"
        cor = "#27ae60" if resultado == "APROVADO" else "#c0392b"
        operador = self.operador_combo.currentText()

        valor_hp = next((l for l in self.linhas_acumuladas if "mA" in l), "N/A")
        valor_gb = next((l for l in self.linhas_acumuladas if "mR" in l), "N/A")
        produto = next((l for l in self.linhas_acumuladas if "HGF" in l), "Padrão")

        # =========================
        # RESUMO VISUAL (COM S/N)
        # =========================
        resumo = (
            f"\n{'=' * 40}\n"
            f"🆔 S/N: {numero_serie}\n"  # NOVO: S/N como destaque
            f"✅ RESULTADO: {resultado}\n"
            f"👤 OPERADOR: {operador}\n"
            f"📦 PRODUTO: {produto}\n"
            f"⚡ ISOLAÇÃO (HP): {valor_hp}\n"
            f"🛡️ ATERRAMENTO (GB): {valor_gb}\n"
            f"{'=' * 40}"
        )
        self.adicionar_log(resumo)

        # Salva no Banco com o novo campo S/N
        relatorio_db = " | ".join(self.linhas_acumuladas)
        salvar_teste(
            numero_serie=numero_serie,
            operador=operador,
            resultado=resultado,
            relatorio=relatorio_db,
            porta=PORTA,
            baud=BAUDRATE,
        )

        self.status_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {cor};"
        )
        self.status_label.setText(f"✅ PEÇA {numero_serie}: {resultado}!")

        # LIMPEZA OBRIGATÓRIA: Força o operador a digitar o próximo S/N
        self.sn_input.clear()
        self.sn_input.setFocus()
        self.linhas_acumuladas = []

    def abrir_tela_relatorios(self):
        self.janela_relatorios = RelatorioWindow()
        self.janela_relatorios.show()

    def erro_serial(self, mensagem):
        self.status_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #D35400; background-color: #FDEBD0; padding: 10px; border-radius: 5px;"
        )
        self.status_label.setText("⚠️ PROBLEMA DE CONEXÃO DETECTADO")
        # (Log de orientação omitido aqui por brevidade, mas mantido no seu código original)

    def closeEvent(self, event):
        self.worker.parar()
        event.accept()
