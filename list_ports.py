import serial.tools.list_ports


def listar_portas():
    # ======================================================
    # CABEÇALHO DE INTERFACE
    # ======================================================
    # Exibe um título claro no terminal para facilitar a leitura do log de diagnóstico.
    print("\n" + "=" * 50)
    print("🔍 BUSCANDO PORTAS SERIAIS ATIVAS...")
    print("=" * 50)

    # ======================================================
    # MAPEAMENTO DE HARDWARE
    # ======================================================
    # Consulta o sistema operacional (Windows) para listar todos os dispositivos
    # de comunicação serial (COM) atualmente conectados e reconhecidos.
    portas = serial.tools.list_ports.comports()

    # ======================================================
    # LÓGICA DE EXIBIÇÃO E ORIENTAÇÃO
    # ======================================================
    if not portas:
        # Caso o hardware não seja detectado, fornece uma dica operacional imediata.
        print("❌ NENHUMA PORTA ENCONTRADA!")
        print("DICA: Verifique se o cabo USB da Hi-Pot está conectado.")
    else:
        # Itera sobre cada porta encontrada, detalhando o identificador e o fabricante.
        for porta in portas:
            print(
                f"✅ Porta: {porta.device}"
            )  # Exemplo: COM3 (O que deve ser usado no código)
            print(
                f"   Descrição: {porta.description}"
            )  # Identifica o tipo de adaptador USB-Serial
            print(
                f"   Hardware ID: {porta.hwid}"
            )  # Identificação única do chip para suporte técnico
            print("-" * 30)

    print("=" * 50 + "\n")


if __name__ == "__main__":
    # Executa a listagem apenas se o arquivo for chamado diretamente no terminal.
    listar_portas()
