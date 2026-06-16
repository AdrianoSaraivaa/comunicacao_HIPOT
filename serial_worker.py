import time
import traceback

from PySide6.QtCore import QThread, Signal

from serial_comm import open_serial, read_line


class SerialWorker(QThread):
    log = Signal(str)
    status = Signal(str)
    dados_recebidos = Signal(str)
    erro = Signal(str)

    def __init__(self, porta, baudrate):
        super().__init__()
        self.porta = porta
        self.baudrate = baudrate
        self._rodando = True
        self.em_teste = False
        self.ultima_linha_processada = None
        self.ser = None

    def run(self):
        try:
            self.status.emit(f"🟡 Tentando acessar a porta {self.porta}...")
            self.log.emit(f"Tentando abrir {self.porta} @ {self.baudrate}...")

            # open_serial agora tem retry interno e tratamento de permissão
            self.ser = open_serial(self.porta, self.baudrate)

            if self.ser is None or not self.ser.is_open:
                self.status.emit(f"🔴 Falha ao abrir a porta {self.porta}")
                self.erro.emit("Falha ao abrir a porta serial.")
                return

            self.status.emit("🟢 Conectado! Aguardando o início do teste...")
            self.log.emit(f"Porta {self.porta} aberta com sucesso")

            erros_leitura_consecutivos = 0

            while self._rodando:
                try:
                    linha = read_line(self.ser)
                    erros_leitura_consecutivos = 0  # Reseta contador se leu com sucesso (ou retornou None validamente)
                except Exception as exc:
                    erros_leitura_consecutivos += 1
                    
                    if "ClearCommError" in str(exc) and erros_leitura_consecutivos < 5:
                        # Erro intermitente, tenta recuperar
                        self.log.emit(f"Aviso de leitura (ClearCommError). Tentativa {erros_leitura_consecutivos}/5...")
                        time.sleep(0.5)
                        continue
                        
                    self.status.emit(f"🔴 Erro de leitura na porta {self.porta}")
                    self.erro.emit(f"Erro de leitura serial: {exc}")
                    self.log.emit("=" * 60)
                    self.log.emit("EXCEÇÃO DURANTE LEITURA SERIAL")
                    self.log.emit(traceback.format_exc())
                    self.log.emit("=" * 60)
                    break

                if not linha:
                    if not self.em_teste:
                        self.ultima_linha_processada = None
                    time.sleep(0.05)
                    continue

                if linha == self.ultima_linha_processada:
                    continue

                if not self.em_teste and linha.startswith("A"):
                    self.em_teste = True
                    self.status.emit("🟢 Teste em execução...")
                    self.log.emit(
                        "==============================\n"
                        "   :: NOVO TESTE INICIADO ::\n"
                        "=============================="
                    )

                if self.em_teste:
                    self.log.emit(f"RX: {linha}")
                    self.dados_recebidos.emit(linha)

                    if '"APR"' in linha or '"REP"' in linha:
                        self.log.emit("Fim do ciclo detectado.")
                        self.status.emit("✅ Finalizado. Remova a peça.")
                        self.ultima_linha_processada = linha
                        self.em_teste = False

        except Exception as exc:
            self.status.emit(f"🔴 Erro de comunicação na porta {self.porta}")
            self.erro.emit(f"Erro crítico: {exc}")
            self.log.emit("=" * 60)
            self.log.emit("EXCEÇÃO GERAL NO SERIAL WORKER")
            self.log.emit(traceback.format_exc())
            self.log.emit("=" * 60)

        finally:
            self.fechar_serial()

    def fechar_serial(self):
        try:
            if self.ser and self.ser.is_open:
                self.log.emit("Encerrando porta serial...")
                self.ser.close()
                self.log.emit("Porta serial encerrada.")
                time.sleep(0.2)  # Dá um tempo pro SO liberar a porta
        except Exception as exc:
            self.log.emit(f"Erro ao encerrar porta serial: {exc}")

    def solicitar_parada(self):
        """Solicita parada da thread de forma segura."""
        self._rodando = False

    def parar(self, timeout_ms=None):
        """Para a thread com timeout opcional."""
        self._rodando = False

        if timeout_ms is None:
            self.wait()
            return True

        resultado = self.wait(timeout_ms)
        
        if not resultado:
            self.log.emit("Aguardando thread encerrar...")
            self.wait(1000)
        
        return resultado