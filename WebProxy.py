import requests
import threading
import socket
import sys

class Client:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr

    def sendto(self, data):
        self.sock.send(data)

    def recv(self):
        return self.sock.recv(4096)

    def recvfrom(self):
        ret = ""
        while True:
            data = self.sock.recv(4096)

            if not data:
                break

            ret += data

        return ret


class WebProxy:
    def __init__(self, host = '127.0.0.1', port = 80):
        self.host = host
        self.port = port
        #self.sessions = []


    def start(self):
        print "Start WebProxy"

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
            session = requests.Session()
            client = Client(sock, addr)

            print "Connection from %s:%d" % (client.addr[0], client.addr[1])

            thread = threading.Thread(target = self.handler, args = (client, session))
            thread.start()

    @classmethod
    def makeHttpResponse(cls, res):
        response = ''
        header = ''
        for key, value in res.headers.iteritems():
            header += key + ': ' + value + '\r\n'

        header = '\r\n'

        response = header + res.content

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

            #req_url = str()
            req_url = "http://"

            for param in params:
                key, value = param.split('=')

                if key == 'targeturl':
                    req_url += value

            return (method, req_url)

    def handler(self, client, session):
        #client_data = client.recvfrom()

        try:
            client_data = client.sock.recv(4096)
            if len(client_data) == 0:
                raise Exception('data not received')

            method, req_url = WebProxy.parseHttpHeader(client_data)

            if method == 'get':
                print "[*]get: " + req_url
                res = session.get(req_url)
                print "done get"
            else:
                print "no method"
                raise HTTPMethodException(method)

            client.sendto(WebProxy.makeHttpResponse(res))

        except HTTPHeaderFormatException as e:
            print e
        except HTTPMethodException as e :
            print e
        except Exception as e:
            print e
        finally:
            client.sock.close()


class HTTPMethodException(Exception):
    def __init__(self, method):
        self.method = method

    def __str__(self):
        return 'Method "%s" is not known' % self.method


class HTTPHeaderFormatException(Exception):
    def __init__(self, header):
        self.header = header

    def __str__(self):
        ret = "Cannot parse following HTTP header: \n"
        ret += self.header

        return ret
