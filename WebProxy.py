import requests
import threading
import socket
import sys
import logging
import re
import urllib
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn

#TODO: 
#implement exception code.
#implement logging
#replace urls to target proxy

class WebProxyHandler(BaseHTTPRequestHandler):
    sessions = dict()

    def sendHttpHeader(self, res):
        for key, value in res.headers.iteritems():
            self.send_header(key, value)


    def do_GET(self):
        try:
            client_host, client_port = self.client_address

            session = None

            key = "%s:%d" % (client_host, client_port)

            logging.info('Connection from ' + key)

            if WebProxyHandler.sessions.has_key(key):
                session = WebProxyHandler.sessions[key]
            else:
                session = requests.Session()
                WebProxyHandler.sessions[key] = session

            req_path = self.path

            index = req_path.find('?')

            param_str = req_path[(index + 1):]

            param = param_str.split('=')

            if param[0] == "targeturl":
                req_url = "http://" + param[1]
            else:#instead of raising exception return form
                raise HTTPHeaderFormatException

            res = session.get(req_url, stream = True)

            logging.info('session.get: ' + req_url)

            self.send_response(res.status_code)

            self.sendHttpHeader(res)

            self.end_headers()

            self.wfile.write(res.raw.read())
        except Exception as e:
            logging.exception(e)

        return 


class ThreadedWebProxy(ThreadingMixIn, HTTPServer):
    """Threaded WebProxy"""


class URLReplacementException(Exception):

    def __str__(self):
        return 'Cannot replace URL'


class HTTPHeaderFormatException(Exception):
    def __init__(self, header):
        self.header = header

    def __str__(self):
        ret = "Cannot parse following HTTP header: \n"
        ret += self.header

        return ret
