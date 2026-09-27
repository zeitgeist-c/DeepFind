"""Kaynak okumasını zaman sınırı olan, anahtarsız alt süreçte çalıştır."""
import multiprocessing as mp
import time


def _perform(kind, args):
    if kind == "extract":
        from .extract import extract
        return extract(*args)
    if kind == "ocr":
        from .ocr import ocr_document
        return ocr_document(*args)
    if kind == "pdf":
        path, number, zoom = args
        import pypdfium2 as pdfium
        with pdfium.PdfDocument(path) as doc:
            number = max(1, min(number, len(doc)))
            page = doc[number - 1]
            width, height = page.get_size()
            scale = min(2.0 * zoom, (8_000_000 / max(1, width * height)) ** 0.5)
            image = page.render(scale=scale).to_pil().convert("RGB")
            return {"number": number, "total": len(doc), "width": image.width,
                    "height": image.height, "data": image.tobytes()}
    if kind == "excel":
        path, sheet = args
        from .extract import _zip_guard
        if path.lower().endswith(".xlsx"):
            if _zip_guard(path):
                raise ValueError("ZIP_LIMIT")
            import openpyxl
            from itertools import islice
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True, keep_links=False)
            try:
                ws = wb[sheet] if sheet in wb.sheetnames else wb.worksheets[0]
                rows = list(islice(ws.iter_rows(max_col=50, values_only=True), 200))
                return {"rows": rows, "sheet": ws.title}
            finally:
                wb.close()
        import xlrd
        wb = xlrd.open_workbook(path, on_demand=True)
        try:
            ws = wb.sheet_by_name(sheet) if sheet in wb.sheet_names() else wb.sheet_by_index(0)
            return {"rows": [ws.row_values(i, 0, min(50, ws.ncols))
                              for i in range(min(200, ws.nrows))], "sheet": ws.name}
        finally:
            wb.release_resources()
    raise ValueError("bilinmeyen iş")


def _child(sender, kind, args):
    try:
        import pickle
        payload = pickle.dumps((True, _perform(kind, args)))
        if len(payload) > 40 * 1024 * 1024:
            payload = pickle.dumps((False, "SIZE_LIMIT"))
        sender.send_bytes(payload)
    except Exception as error:
        import pickle
        sender.send_bytes(pickle.dumps((False, type(error).__name__)))
    finally:
        sender.close()


def run_work(kind, args, timeout=60, stop=None):
    import pickle
    context = mp.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(sender, kind, args), daemon=True)
    process.start()
    sender.close()
    deadline = time.monotonic() + timeout
    try:
        while not receiver.poll(0.05):
            if stop and stop():
                raise InterruptedError("iş iptal edildi")
            if time.monotonic() >= deadline:
                raise TimeoutError("PROCESS_TIMEOUT")
            if not process.is_alive():
                raise RuntimeError("çalışan beklenmedik biçimde kapandı")
        ok, result = pickle.loads(receiver.recv_bytes(40 * 1024 * 1024))
        if not ok:
            raise RuntimeError(result)
        return result
    finally:
        receiver.close()
        if process.is_alive():
            import os
            if os.name == "nt":
                import subprocess
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
            process.terminate()
        process.join(3)
        if process.is_alive():
            process.kill()
            process.join()
        process.close()
