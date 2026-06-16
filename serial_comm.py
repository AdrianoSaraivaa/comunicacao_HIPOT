import time
import serial


def open_serial(
    port,
    baudrate=9600,
    timeout=1,
    settle_time=2.0,
    set_rts=None,
    set_dtr=None,
    max_retries=3
):
    """
    Abre a porta serial com tentativas múltiplas e tratamento de permissão.
    O erro PermissionError(13, 'Acesso negado') é comum quando a porta está presa
    pelo Windows ou por outra instância do programa.
    """
    last_exc = None
    
    for tentativa in range(1, max_retries + 1):
        try:
            # Tenta forçar fechamento se a porta já estiver aberta em outra instância
            # (isso é feito criando uma instância temporária e fechando)
            try:
                temp_ser = serial.Serial()
                temp_ser.port = port
                temp_ser.close()
            except:
                pass
                
            time.sleep(0.5)  # Pequeno delay antes de tentar abrir
            
            ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )

            if set_rts is not None:
                ser.rts = bool(set_rts)

            if set_dtr is not None:
                ser.dtr = bool(set_dtr)

            # Aguarda a porta estabilizar (importante para Hi-Pot)
            time.sleep(settle_time)
            
            # Limpa buffers para evitar lixo antigo e sincronizar
            try:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except Exception as e:
                # Ignora erros de buffer (ClearCommError), apenas segue em frente
                pass
                
            return ser

        except (serial.SerialException, OSError) as exc:
            last_exc = exc
            # Se for erro de permissão, aguarda mais tempo e tenta novamente
            if "PermissionError" in str(exc) or "Acesso negado" in str(exc):
                time.sleep(1.5)  # Espera o Windows liberar a porta
            else:
                time.sleep(0.5)
                
    # Se falhou todas as tentativas, lança o último erro
    raise RuntimeError(f"Falha ao abrir {port} após {max_retries} tentativas. Erro: {last_exc}") from last_exc


def read_line(ser):
    """
    Lê uma linha da porta serial com tratamento robusto de erros.
    Ignora erros intermitentes de ClearCommError que podem ocorrer
    durante oscilações elétricas.
    """
    if ser is None or not ser.is_open:
        return None

    try:
        # Envolve a checagem de in_waiting em try/except para capturar
        # o ClearCommError que ocorre quando o cabo USB sofre interferência
        try:
            if ser.in_waiting <= 0:
                return None
        except serial.SerialException as e:
            if "ClearCommError" in str(e):
                # Erro comum de driver USB/Serial, ignora e retorna None
                # para que o loop tente novamente
                time.sleep(0.1)
                return None
            raise

        raw = ser.readline()
        if not raw:
            return None

        texto = raw.decode("utf-8", errors="ignore").strip()
        return texto or None

    except (serial.SerialException, OSError) as exc:
        # Apenas lança erro se for algo grave (desconexão física)
        if "ClearCommError" in str(exc):
            time.sleep(0.1)
            return None
            
        raise RuntimeError(f"Falha na leitura serial: {exc}") from exc