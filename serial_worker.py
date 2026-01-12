from PySide6.QtCore import QThread, Signal
from serial_comm import open_serial, read_line
import time


class SerialWorker(QThread):
    # Canais de comunicação com a interface (GUI)
    log = Signal(str)  # Envia mensagens de texto para o console visual
    status = Signal(str)  # Atualiza a barra de status principal (em destaque)
    dados_recebidos = Signal(
        str
    )  # Envia a linha bruta para processamento matemático/banco
    erro = Signal(str)  # Reporta falhas físicas ou de conexão

    def __init__(self, porta, baudrate):
        super().__init__()
        self.porta = porta
        self.baudrate = baudrate
        self._rodando = True
        self.em_teste = False
        self.ultima_linha_processada = None

    def run(self):
        ser = None
        try:
            # ===== ABERTURA DA PORTA =====
            # Tenta estabelecer o link físico com o hardware.
            # O status é enviado à GUI para feedback imediato ao operador.
            self.status.emit(f"🟡 Tentando acessar a porta {self.porta}...")
            ser = open_serial(self.porta, self.baudrate)

            if ser is None or not ser.is_open:
                # Interrompe a execução se o Windows negar acesso à porta COM
                self.erro.emit("Falha ao abrir a porta serial.")
                return

            self.status.emit("🟢 Conectado! Aguardando o início do teste...")
            self.log.emit(f"Porta {self.porta} aberta com sucesso")

            # ===== LOOP PRINCIPAL =====
            # Escuta contínua da porta serial enquanto o programa estiver ativo.
            while self._rodando:
                linha = read_line(ser)

                # Timeout / silêncio da máquina
                # Se a máquina não enviar nada, limpamos a trava de segurança
                # para permitir que um novo teste (com dados iguais) possa começar.
                if not linha:
                    if not self.em_teste:
                        self.ultima_linha_processada = None
                    time.sleep(0.05)  # Pequeno descanso para não sobrecarregar a CPU
                    continue

                # Trava contra looping da mesma linha
                # Máquinas industriais costumam repetir o último pacote dezenas de vezes.
                # Se a linha for idêntica à anterior, o código ignora para evitar spam no banco.
                if linha == self.ultima_linha_processada:
                    continue

                # ===== DETECÇÃO DE INÍCIO =====
                # O protocolo da Hi-Pot inicia pacotes de dados com a letra "A".
                # Só iniciamos um novo ciclo se não houver um teste já em andamento.
                if not self.em_teste and linha.startswith("A"):
                    self.em_teste = True
                    self.status.emit("🟢 Teste em execução...")
                    self.log.emit(
                        "==============================\n"
                        "   :: NOVO TESTE INICIADO ::\n"
                        "=============================="
                    )

                # ===== PROCESSAMENTO =====
                # Enquanto 'em_teste' for True, toda linha recebida é repassada para a GUI.
                if self.em_teste:
                    self.log.emit(f"RX: {linha}")
                    self.dados_recebidos.emit(linha)

                    # ===== DETECÇÃO DE FIM =====
                    # "APR" (Aprovado) e "REP" (Reprovado) indicam que a máquina concluiu o ensaio.
                    if '"APR"' in linha or '"REP"' in linha:
                        self.log.emit("Fim do ciclo detectado.")
                        self.status.emit("✅ Finalizado. Remova a peça.")

                        # Bloqueamos novas detecções desta mesma linha e resetamos o estado do ciclo.
                        self.ultima_linha_processada = linha
                        self.em_teste = False

        except Exception as e:
            # Captura erros inesperados (ex: cabo desconectado durante o uso)
            self.erro.emit(f"Erro crítico: {str(e)}")

        finally:
            # Garante que a porta COM seja liberada para outros apps ao fechar o programa.
            if ser and ser.is_open:
                ser.close()
                self.log.emit("Porta serial encerrada.")

    def parar(self):
        """Método externo para encerrar a thread de forma segura."""
        self._rodando = False
        self.wait()
