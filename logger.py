from datetime import datetime


class Logger:
    def __init__(self, callback):
        """
        callback: função que recebe string e mostra na tela
        """
        self.callback = callback

    def log(self, mensagem):
        timestamp = datetime.now().strftime("%H:%M:%S")
        texto = f"[{timestamp}] {mensagem}"
        self.callback(texto)
