from functools import partial
import re

from PySide6.QtCore import Qt, QTimer
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

from reports import RelatorioWindow
from operators import OPERADORES
from logger import Logger
from serial_worker import SerialWorker
from database import salvar_teste, criar_tabela


PORTA = "COM3"
BAUDRATE = 9600


class HipotWindow(QWidget):
    def __init__(self):
        super().__init__()

        criar_tabela()

        self.setWindowTitle("HIPOT - Sistema de Ensaios Elétricos (Rastreabilidade)")
        self.setMinimumSize(800, 700)

        self.worker = None
        self.worker_seq = 0
        self.reconexao_em_andamento = False
        self._aguardando_parada_tentativas = 0
        self.linhas_acumuladas = []

        self._montar_interface()

        self.logger = Logger(self.adicionar_log)
        self.logger.log("[GUI] Aplicação iniciada")

        self.iniciar_worker()

    def _montar_interface(self):
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        status_box = QVBoxLayout()

        self.conn_label = QLabel("🟡 Comunicação: aguardando inicialização...")
        self.conn_label.setAlignment(Qt.AlignLeft)
        self.conn_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #B58105;"
        )

        self.status_label = QLabel("🟡 Aguardando início do teste...")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #333;"
        )

        status_box.addWidget(self.conn_label)
        status_box.addWidget(self.status_label)

        self.btn_reconectar = QPushButton("🔄 Reconectar Hi-Pot")
        self.btn_reconectar.setMinimumHeight(40)
        self.btn_reconectar.clicked.connect(self.reconectar_comunicacao)

        self.btn_relatorios = QPushButton("📊 Consultar Relatórios")
        self.btn_relatorios.setMinimumHeight(40)
        self.btn_relatorios.clicked.connect(self.abrir_tela_relatorios)

        header_layout.addLayout(status_box)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_reconectar)
        header_layout.addWidget(self.btn_relatorios)
        layout.addLayout(header_layout)

        ident_layout = QHBoxLayout()

        sn_vbox = QVBoxLayout()
        sn_vbox.addWidget(QLabel("🆔 <b>NÚMERO DE SÉRIE (Obrigatório):</b>"))

        self.sn_input = QLineEdit()
        self.sn_input.setPlaceholderText("Digite ou bip o S/N aqui...")
        self.sn_input.setStyleSheet(
            "font-size: 16px; padding: 5px; border: 2px solid #0d6efd;"
        )
        sn_vbox.addWidget(self.sn_input)

        op_vbox = QVBoxLayout()
        op_vbox.addWidget(QLabel("👤 <b>Operador:</b>"))

        self.operador_combo = QComboBox()
        self.operador_combo.addItems(OPERADORES)
        self.operador_combo.setStyleSheet("font-size: 14px; padding: 5px;")
        op_vbox.addWidget(self.operador_combo)

        ident_layout.addLayout(sn_vbox, 2)
        ident_layout.addLayout(op_vbox, 1)
        layout.addLayout(ident_layout)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(
            "background-color: #0d1117; color: #58a6ff; font-family: Consolas; font-size: 11px;"
        )
        layout.addWidget(self.log_area)

        self.setLayout(layout)

    def adicionar_log(self, texto):
        self.log_area.append(texto)

    def iniciar_worker(self):
        self.worker_seq += 1
        seq = self.worker_seq

        worker = SerialWorker(PORTA, BAUDRATE)
        worker.log.connect(partial(self._on_worker_log, seq))
        worker.status.connect(partial(self._on_worker_status, seq))
        worker.erro.connect(partial(self._on_worker_error, seq))
        worker.dados_recebidos.connect(partial(self._on_worker_data, seq))
        worker.finished.connect(partial(self._on_worker_finished, seq))

        self.worker = worker
        self.logger.log(
            f"[GUI][WORKER] iniciando worker #{seq} em {PORTA} @ {BAUDRATE}."
        )
        worker.start()

    def _worker_ativo(self, seq):
        return seq == self.worker_seq

    def _on_worker_log(self, seq, mensagem):
        self.logger.log(f"[SERIAL#{seq}] {mensagem}")

    def _on_worker_status(self, seq, texto):
        if not self._worker_ativo(seq):
            self.logger.log(f"[GUI][STALE] status ignorado do worker #{seq}: {texto}")
            return
        self.atualizar_status_serial(texto)

    def _on_worker_error(self, seq, mensagem):
        if not self._worker_ativo(seq):
            self.logger.log(f"[GUI][STALE] erro ignorado do worker #{seq}: {mensagem}")
            return
        self.erro_serial(mensagem)

    def _on_worker_data(self, seq, linha):
        if not self._worker_ativo(seq):
            self.logger.log(f"[GUI][STALE] dado ignorado do worker #{seq}.")
            return
        self.processar_dado(linha)

    def _on_worker_finished(self, seq):
        self.logger.log(f"[GUI][WORKER] worker #{seq} finalizado.")

    def atualizar_status_serial(self, texto):
        if "Teste em execução" in texto:
            self.atualizar_status_teste(texto, "#0d6efd")
            return

        if texto.startswith("✅"):
            self.atualizar_status_teste(texto, "#198754")
            return

        if texto.startswith("🟢"):
            self.conn_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #198754;"
            )
            self.conn_label.setText(texto)
            return

        if texto.startswith("🟡"):
            self.conn_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #B58105;"
            )
            self.conn_label.setText(texto)
            return

        if texto.startswith("🔴") or texto.startswith("⚠"):
            self.conn_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #D35400; "
                "background-color: #FDEBD0; padding: 6px; border-radius: 5px;"
            )
            self.conn_label.setText(texto)
            return

        self.conn_label.setText(texto)

    def atualizar_status_teste(self, texto, cor="#333"):
        self.status_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {cor};"
        )
        self.status_label.setText(texto)

    def processar_dado(self, linha):
        numero_serie = self.sn_input.text().strip()
        if not numero_serie:
            self.atualizar_status_teste(
                "🛑 ERRO: Digite o S/N antes de iniciar!", "#c0392b"
            )
            return

        match = re.search(r'"(.*?)"', linha)
        if not match:
            return

        texto_limpo = match.group(1)

        if texto_limpo == "ENTRAN" and not self.linhas_acumuladas:
            separador = (
                f"\n\n\n\n{'=' * 60}\n"
                f"     :: NOVO ENSAIO INICIADO - S/N: {numero_serie} ::\n"
                f"{'=' * 60}\n"
            )
            self.adicionar_log(separador)

        self.linhas_acumuladas.append(texto_limpo)

        if texto_limpo in {"APR", "REP"}:
            self.finalizar_e_salvar(texto_limpo)

    def finalizar_e_salvar(self, resultado_raw):
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

        resumo = (
            f"\n{'=' * 40}\n"
            f"🆔 S/N: {numero_serie}\n"
            f"✅ RESULTADO: {resultado}\n"
            f"👤 OPERADOR: {operador}\n"
            f"📦 PRODUTO: {produto}\n"
            f"⚡ ISOLAÇÃO (HP): {valor_hp}\n"
            f"🛡️ ATERRAMENTO (GB): {valor_gb}\n"
            f"{'=' * 40}"
        )
        self.adicionar_log(resumo)

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

        self.sn_input.clear()
        self.sn_input.setFocus()
        self.linhas_acumuladas = []

    def abrir_tela_relatorios(self):
        self.janela_relatorios = RelatorioWindow()
        self.janela_relatorios.show()

    def reconectar_comunicacao(self):
        if self.reconexao_em_andamento:
            self.logger.log("[GUI][RECONNECT] solicitação ignorada; já em andamento.")
            return

        self.reconexao_em_andamento = True
        self._aguardando_parada_tentativas = 0
        self.btn_reconectar.setEnabled(False)

        self.logger.log("=" * 50)
        self.logger.log("[GUI][RECONNECT] solicitação iniciada")
        self.logger.log(f"[GUI][RECONNECT] nova tentativa em {PORTA} @ {BAUDRATE}")
        self.logger.log("=" * 50)

        self.conn_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #B58105;"
        )
        self.conn_label.setText("🟡 Reiniciando comunicação serial...")

        if self.worker and self.worker.isRunning():
            self.worker.solicitar_parada()
            QTimer.singleShot(100, self._aguardar_worker_encerrar)
        else:
            QTimer.singleShot(0, self._iniciar_worker_pos_reconexao)

    def _aguardar_worker_encerrar(self):
        if self.worker and self.worker.isRunning():
            self._aguardando_parada_tentativas += 1

            if self._aguardando_parada_tentativas >= 50:  # 5 segundos max
                self.logger.log(
                    "[GUI][RECONNECT] timeout aguardando término do worker anterior (5s)."
                )
                self.logger.log("[GUI][RECONNECT] forçando encerramento...")
                
                if self.worker:
                    self.worker.wait(1000)
                
                self.logger.log("[GUI][RECONNECT] worker forçadamente encerrado.")
                self._iniciar_worker_pos_reconexao()
                return

            QTimer.singleShot(100, self._aguardar_worker_encerrar)
            return

        self._iniciar_worker_pos_reconexao()

    def _iniciar_worker_pos_reconexao(self):
        self.logger.log("[GUI][RECONNECT] aguardando 1 segundo antes de reabrir porta...")
        QTimer.singleShot(1000, self._reabrir_porta)

    def _reabrir_porta(self):
        self.iniciar_worker()
        self.logger.log(
            "[GUI][RECONNECT] nova tentativa iniciada; aguardando status do worker."
        )
        self.reconexao_em_andamento = False
        self.btn_reconectar.setEnabled(True)

    def erro_serial(self, mensagem):
        self.logger.log(f"[SERIAL][ERROR] {mensagem}")

        if not self.conn_label.text().startswith(("🔴", "⚠")):
            self.conn_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #D35400; "
                "background-color: #FDEBD0; padding: 6px; border-radius: 5px;"
            )
            self.conn_label.setText("⚠️ PROBLEMA DE CONEXÃO DETECTADO")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.logger.log("[GUI] Encerrando aplicação e comunicação serial...")
            self.worker.parar(timeout_ms=2000)
        event.accept()