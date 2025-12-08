# import os
# import logging
# import datetime
# from logging import FileHandler

# class MonthlyFileHandler(FileHandler):
#     """
#     Ein einfacher FileHandler, der die Logdatei pro Monat benennt:
#     <prefix>-YYYY-MM.log. Beim Monatswechsel wird die Datei automatisch
#     geschlossen und eine neue Datei mit neuem Monat geöffnet.
#     """
#     def __init__(self, dirname, filename_prefix='django', mode='a', encoding=None, delay=False):
#         self.dirname = os.path.abspath(dirname)
#         os.makedirs(self.dirname, exist_ok=True)
#         self.filename_prefix = filename_prefix
#         self.encoding = encoding
#         self.mode = mode
#         # aktuelle Monatskennung
#         self.current_month = datetime.datetime.now().strftime('%Y-%m')
#         fname = os.path.join(self.dirname, f"{self.filename_prefix}-{self.current_month}.log")
#         super().__init__(fname, mode=mode, encoding=encoding, delay=delay)

#     def _rollover_if_needed(self):
#         now_month = datetime.datetime.now().strftime('%Y-%m')
#         if now_month != self.current_month:
#             # Monatswechsel -> neue Datei
#             self.current_month = now_month
#             new_fname = os.path.join(self.dirname, f"{self.filename_prefix}-{self.current_month}.log")
#             # safely close old stream and open new
#             try:
#                 if hasattr(self, 'stream') and self.stream:
#                     try:
#                         self.stream.close()
#                     except Exception:
#                         pass
#                 self.baseFilename = new_fname
#                 self.stream = self._open()
#             except Exception:
#                 # Falls das Öffnen fehlschlägt, geben wir die Exception später an logging weiter
#                 pass

#     def emit(self, record):
#         try:
#             self._rollover_if_needed()
#         except Exception:
#             # Falls Rollover fehlschlägt, trotzdem versuchen zu loggen
#             pass
#         super().emit(record)