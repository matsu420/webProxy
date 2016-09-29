import logging

class HttpLogger:
    def __init__(self, server_handler, filename = 'http.log', level = logging.INFO, fmt = '%(asctime)s %(message)s'):
        self.server_handler = server_handler
        logging.basicConfig(filename = filename, level = level, format = fmt)

    def log_access(self):
        client_host, client_port = self.server_handler.client_address

        agent = self.server_handler.headers.getheader('user-agent', '')

        log_str = client_host

        temp = ' "%s %s %s"' % (self.server_handler.command, self.server_handler.path, self.server_handler.request_version)

        temp += ' "%s"' % agent

        log_str += temp

        logging.info(log_str)

    def log_proxy_action(self, url, data = None):
        log_str = 'Proxy "%s %s"' % (self.server_handler.command, url)
        log_str += ' %d ' % self.server_handler.res.status_code

        logging.info(log_str)

        if not data is None:
            for key, value in data.iteritems():
                logging.info('"%s=%s"' % (key, value))

    def log_exception(self, exception):
        logging.exception(exception)
