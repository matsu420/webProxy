import logging

class WebProxyLog:
    @classmethod
    def config(cls, filename, level):
        logging.basicConfig(filename = filename, level = level)
