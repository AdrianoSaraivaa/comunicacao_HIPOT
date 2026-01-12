import sqlite3
from datetime import datetime

DB_NAME = "hipot.db"


def conectar():
    """Estabelece a conexão com o banco de dados SQLite."""
    return sqlite3.connect(DB_NAME)


def criar_tabela():
    """Cria a tabela de resultados com foco em rastreabilidade por número de série."""
    conn = conectar()
    cursor = conn.cursor()

    # Criamos a tabela incluindo a coluna numero_serie
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS testes_hipot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            numero_serie TEXT NOT NULL,
            operador TEXT NOT NULL,
            resultado TEXT NOT NULL,
            relatorio TEXT NOT NULL,
            porta_com TEXT,
            baudrate INTEGER
        )
        """
    )

    # TÉCNICO: Verifica se a coluna numero_serie existe (para quem já tinha o banco antigo)
    cursor.execute("PRAGMA table_info(testes_hipot)")
    colunas = [col[1] for col in cursor.fetchall()]
    if "numero_serie" not in colunas:
        cursor.execute(
            "ALTER TABLE testes_hipot ADD COLUMN numero_serie TEXT DEFAULT 'S/N ANTIGO'"
        )

    conn.commit()
    conn.close()


def salvar_teste(numero_serie, operador, resultado, relatorio, porta, baud):
    """
    Insere um novo registro de teste vinculado obrigatoriamente a um número de série.
    """
    conn = conectar()
    cursor = conn.cursor()

    # Captura a data e hora exata da gravação para o histórico
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO testes_hipot (data_hora, numero_serie, operador, resultado, relatorio, porta_com, baudrate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (data_hora, numero_serie, operador, resultado, relatorio, porta, baud),
    )

    conn.commit()
    conn.close()
