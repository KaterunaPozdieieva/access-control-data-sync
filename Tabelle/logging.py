import os
import logging
from logging import FileHandler
from datetime import datetime
class MonthlyFileHandler(FileHandler):
    def __init__(self, dirname, filename_prefix="django-log", mode='a', encoding='utf-8'):
        os.makedirs(dirname, exist_ok=True)
        self.dirname = dirname
        self.filename_prefix = filename_prefix
        self.mode = mode
        self.encoding = encoding
        self.current_period = datetime.now().strftime("%Y-%m")
        filename = os.path.join(self.dirname, f"{self.filename_prefix}-{self.current_period}.log")
        super().__init__(filename, mode=mode, encoding=encoding)
    def _update_file_if_needed(self):
        period = datetime.now().strftime("%Y-%m-")
        if period != self.current_period:
            try:
                self.current_period = period
                self.close()
                new_filename = os.path.join(self.dirname, f"{self.filename_prefix}-{self.current_period}.log")
                self.baseFilename = os.path.abspath(new_filename)
                self.stream = self._open()
            except Exception:
                pass
    def emit(self, record):
        try:
            self._update_file_if_needed()
        except Exception:
            pass
        super().emit(record)