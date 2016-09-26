import requests
import threading
import socket
import sys
import logging
import re
import urllib

class Client:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr

    def send(self, data):
        self.sock.send(data)

    def recv(self):
        ret = ""
        while True:
            data = self.sock.recv(4096)

            if not data:
                break

            ret += data

        return ret


class WebProxy:
    LOGLEVEL = logging.DEBUG

    def __init__(self, host = '127.0.0.1', port = 80, global_address = '127.0.0.1'):
        self.host = host
        self.port = port
        self.global_addres = global_address
        self.sessions = dict()

        logging.basicConfig(filename = 'webproxy.log', level = WebProxy.LOGLEVEL)


    def start(self):
        logging.info('Start WebProxy')

        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            server_sock.bind((self.host, self.port))

            server_sock.listen(5)

        except Exception as e:
            raise e

        while True:
            client = None
            session = None
            sock, addr = server_sock.accept()
            client = Client(sock, addr)

            if self.sessions.has_key('%s:%d' % (client.addr[0], client.addr[1])):
                session = self.sessions['%s:%d' % (client.addr[0], client.addr[1])]
            else:
                session = requests.Session()
                self.sessions['%s:%d' % (client.addr[0], client.addr[1])] = session

            logging.info("Connection from %s:%d" % (client.addr[0], client.addr[1]))

            thread = threading.Thread(target = self.handler, args = (client, session))
            thread.start()

    @classmethod
    def makeHttpResponse(cls, res_headers, res_content):
        response = ''
        header = ''
        for key, value in res_headers.iteritems():
            header += key + ': ' + value + '\r\n'

        header = '\r\n'

        response = header + res_content

        return response

    @classmethod
    def parseHttpHeader(cls, client_data):
            client_data.replace('\r\n', '\n')

            print "[*]client data:"
            print client_data

            client_lines = client_data.split('\n')

            request = client_lines[0]

            request_tokens = request.split()

            method = str()

            if request_tokens[0].lower() == 'get':
                method = 'get'
            else:
                raise Exception('method not supported')

            index = request_tokens[1].find('?')

            params = None

            if not index == -1:
                param_str = request_tokens[1][(index + 1):]
                params = param_str.split('&')

            if params is None or len(params) == 0:
                #instead of raising exception, return a form to enter the target url
                raise HTTPHeaderFormatException(client_data)

            req_url = "http://"

            for param in params:
                key, value = param.split('=')

                if key == 'targeturl':
                    req_url += value

            return (method, req_url)

    @classmethod
    def replace_url(cls, content, host, port):
        urls = re.findall(r'href=[\'"]?([^\'" >]+)', content)
        #urls = p.findall(content)

        temp = re.findall(r'src=[\'"]?([^\'" >]+)', content)
        #temp = p.findall(content)

        if not urls is None and not temp is None:
            urls.extend(temp)
        elif urls is None:
            urls = temp

        if urls is None:
            raise URLReplacementException()
        else:
            for url in urls:
                target_url = 'http://' + host + ':' + str(port) + '?targeturl='
                temp = str(url)
                temp = temp.replace('http://', '')
                temp = temp.replace('/', '_')
                temp = urllib.quote(temp)
                target_url += temp
                content = content.replace(url, target_url)

            return content


    def handler(self, client, session):
        try:
            client_data = client.sock.recv(4096)
            if len(client_data) == 0:
                raise Exception('data not received')

            method, req_url = WebProxy.parseHttpHeader(client_data)

            if method == 'get':
                logging.info("get: " + req_url)
                res = session.get(req_url)
            else:
                raise HTTPMethodException(method)

            res_content_replaced = WebProxy.replace_url(res.content, self.host, self.port)

            if res_content_replaced is None:
                sys.exit(1)

            client.send(WebProxy.makeHttpResponse(res.headers, res_content_replaced))

        except HTTPHeaderFormatException as e:
            logging.exception(e)
        except HTTPMethodException as e :
            logging.exception(e)
        except URLReplacementException as e:
            logging.exception(e)
        except Exception as e:
            logging.exception(e)
        finally:
            client.sock.close()


class HTTPMethodException(Exception):
    def __init__(self, method):
        self.method = method

    def __str__(self):
        return 'Method "%s" is not known' % self.method


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