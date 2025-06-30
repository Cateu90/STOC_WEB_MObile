import os
import platform
import traceback
import logging

# Configuração básica do logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] - %(message)s')

class PrintService:
    @staticmethod
    def imprimir_texto(texto, printer_name=None):
        logging.info("Serviço de impressão iniciado.")
        logging.info(f"Impressora recebida: {printer_name}")
        texto_preview = texto[:100].replace('\n', ' ')
        logging.info(f"Texto a ser impresso (primeiros 100 chars): {texto_preview}")

        if platform.system() != "Windows":
            logging.error("Impressão só é suportada no Windows.")
            return {"status": "error", "message": "Impressão não é suportada neste sistema operacional."}

        try:
            import win32print
            import win32ui
        except ImportError:
            logging.error("A biblioteca 'pywin32' não está instalada. Execute 'pip install pywin32'.")
            return {"status": "error", "message": "Dependência de impressão (pywin32) não encontrada."}

        try:
            if not printer_name:
                printer_name = win32print.GetDefaultPrinter()
                logging.info(f"Nenhuma impressora especificada, usando a padrão: {printer_name}")
            
            hprinter = win32print.OpenPrinter(printer_name)
            logging.info(f"Conexão com a impressora '{printer_name}' aberta.")

            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            logging.info("DC da impressora criado.")

            hdc.StartDoc("Comprovante de Venda")
            hdc.StartPage()
            logging.info("Página de impressão iniciada.")

            y = 100
            font = win32ui.CreateFont({"name": "Consolas", "height": 20})
            hdc.SelectObject(font)

            for line in texto.splitlines():
                hdc.TextOut(100, y, line)
                y += 30
            
            logging.info("Conteúdo do comprovante desenhado na página.")

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
            win32print.ClosePrinter(hprinter)
            
            logging.info(f"Impressão concluída com sucesso na impressora '{printer_name}'.")
            return {"status": "success", "message": "Impresso com sucesso."}

        except Exception as e:
            error_msg = f"Erro inesperado durante a impressão: {e}"
            logging.error(error_msg)
            logging.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}

    @staticmethod
    def listar_status_impressoras(impressoras):
        status = []
        try:
            import win32print
            for imp in impressoras:
                try:
                    hprinter = win32print.OpenPrinter(imp['printer_name'])
                    status.append({"nome": imp['nome'], "printer_name": imp['printer_name'], "status": "OK"})
                    win32print.ClosePrinter(hprinter)
                except Exception as e:
                    status.append({"nome": imp['nome'], "printer_name": imp['printer_name'], "status": f"Erro: {e}"})
        except ImportError:
            for imp in impressoras:
                status.append({"nome": imp['nome'], "printer_name": imp['printer_name'], "status": "Desconhecido"})
        return status
