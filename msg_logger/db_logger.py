import logging


class DBLoggerHandler(logging.Handler):
    def __init__(self, model):
        self.model = model
        super().__init__()

    def emit(self, record):
        try:
            log_entry = self.model(
                logger_name=record.name,
                level=record.levelno,
                msg=record.msg,
                traceback=record.exc_text if record.exc_info else None,
                create_time=record.created,
            )
            log_entry.save()
        except Exception:
            self.handleError(record)
