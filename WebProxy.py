import requests
import hashlib
import threading
import socket
import sys
import logging
import re
import gzip
import urllib
import os.path

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
from HttpLogger import HttpLogger

class WebProxyHandler(BaseHTTPRequestHandler):
    sessions = dict()
    domain_pat = re.compile('(?<=://)[^/]*')
    schema_pat = re.compile('[a-z]*:?//')

    @classmethod 
    def remove_schema(cls, url):#removes schema from url and return the schema and the url.
        schema_match = WebProxyHandler.schema_pat.match(url)
        schema = str()
        if not schema_match is None:
            schema = schema_match.group()
            url = url.replace(schema, '')
            if schema == r'//':
                schema = 'http://'
        else:
            schema = 'http://'

        return (url, schema)

    def get_replace_urls(self, pat_str):
        temp = re.findall(pat_str, string = self.res.content, flags = re.IGNORECASE)

        if temp is None:
            return []
        else:
            return temp

    def replace_url(self):#replace the urls to target the proxy
        server_host = self.server_host
        server_port = self.server_port
        domain = self.domain
        ret_content = self.res.content

        urls = []

        urls.extend(self.get_replace_urls(r'href=[\'"]?([^\'" >]+)'))
        urls.extend(self.get_replace_urls(r'src=[\'"]?([^\'" >]+)'))
        urls.extend(self.get_replace_urls(r'action=[\'"]?([^\'" >]+)'))
        urls.extend(self.get_replace_urls(r'(?<=url\([\'\"])[^\'\"]*'))
        urls.extend(self.get_replace_urls(r'(?<=url\([^\'\"])[^\'\")]*'))



        if urls is None:#there is a possibility that the page has no links
            raise URLReplacementException()
        else:
            for change_from_url in urls:
                original_url = change_from_url


                if not 'http' in server_host:
                    server_host = 'http://' + server_host

                change_to_url = server_host + ':' + str(server_port) + '?targeturl='

                change_from_url = str(change_from_url)

                has_domain = None

                if '//' in change_from_url:
                    has_domain = True
                else:
                    has_domain = False

                change_from_url, schema = WebProxyHandler.remove_schema(change_from_url)

                if not has_domain:
                    change_from_url = domain + change_from_url

                change_from_url = schema + change_from_url

                change_from_url = WebProxyHandler.percent_encode(change_from_url)
                change_to_url += change_from_url
                url_pat_str = '(?<=[\(\'\"])' + re.escape(original_url) + '(?=[\)\'\"])'
                ret_content = re.sub(url_pat_str, change_to_url, ret_content)

            return ret_content

    def parse_path(self):
        index = self.path.find('?')

        param_str = self.path[(index + 1):]

        param = param_str.split('=')

        if param[0] == "targeturl":
            targeturl = param[1]
            targeturl = WebProxyHandler.percent_decode(targeturl)

            if not "http" in targeturl:
                targeturl = 'http://' + targeturl

            domain = WebProxyHandler.domain_pat.search(targeturl).group()

        else:#instead of raising exception return form
            raise PathParsingException(self.path)

        return (targeturl, domain)


    @classmethod
    def percent_encode(cls, url):
        url = urllib.quote(url, safe = '')

        return url.replace('.', '%2E')

    @classmethod
    def percent_decode(cls, url):
        url = url.replace('%2E', '.')

        return urllib.unquote(url)

    def getHttpReqHeader(self):
        header = str()
        for name in self.headers:
            header += name 
            header += self.headers.getheader(name)
            header += '\n'

        return header


    def sendHttpHeader(self):#transfer the headers of result from the target to the client
        self.gzip_allowed = False
        for key, value in self.res.headers.iteritems():
            if 'gzip' in value.lower():
                self.gzip_allowed = True

            if not 'content-length' in key.lower() and not 'transfer-encoding' in key.lower():
                self.send_header(key, value)


    def prepare(self):
        self.proxy_logger = HttpLogger(server_handler = self,level = logging.DEBUG)

        self.proxy_logger.log_access()

        client_host, client_port = self.client_address

        session = None

        self.protocol_version = 'HTTP/1.1'

        key = "%s:%d" % (client_host, client_port)

        if WebProxyHandler.sessions.has_key(key):
            session = WebProxyHandler.sessions[key]
        else:
            session = requests.Session()
            WebProxyHandler.sessions[key] = session

        return session

    def do_GET(self):
        try:

            session = self.prepare()

            if 'favicon' in self.path:
                self.send_response(404)
                self.end_headers()

                return 

            targeturl, domain = self.parse_path()

            self.domain = domain

            self.res = session.get(targeturl)

            self.proxy_logger.log_proxy_action(url = targeturl)

            self.send_response(self.res.status_code)

            self.sendHttpHeader()


            filepath = '/tmp/webproxy/'


            if 'text' in self.res.headers['Content-Type'] or 'css' in self.res.headers['Content-Type'] or 'javascript' in self.res.headers['Content-Type']:
                self.server_host = 'localhost'
                self.server_port = 8080
                url_replaced = self.replace_url()

                if not os.path.exists(filepath):
                    os.mkdir(filepath)

                #filepath += targeturl.replace('/', '_')
                filepath += str(hashlib.md5(targeturl))

                if self.gzip_allowed:
                    gzipfilepath = filepath + '.gz'
                    with gzip.open(gzipfilepath, 'w') as f_out:
                        f_out.write(url_replaced)
                    with open(gzipfilepath, 'r') as f_in:
                        url_replaced = f_in.read()

                    self.send_header('Content-Length', os.path.getsize(gzipfilepath))

                else:#send raw content size
                    with open(filepath, 'w') as f_out:
                        f_out.write(url_replaced)

                    self.send_header('Content-Length', os.path.getsize(filepath))

                self.end_headers()

                self.wfile.write(url_replaced)
            else:#send raw content size
                #filepath += targeturl.replace('/', '_')
                filepath += str(hashlib.md5(targeturl))
                with open(filepath, 'w') as f_out:
                    f_out.write(self.res.content)

                self.send_header('Content-Length', os.path.getsize(filepath))

                self.end_headers()
                self.wfile.write(self.res.content)
        except Exception as e:
            self.proxy_logger.log_exception(e)

        return 


class ThreadedWebProxy(ThreadingMixIn, HTTPServer):
    """Threaded WebProxy"""


class URLReplacementException(Exception):

    def __str__(self):
        return 'Cannot replace URL'


class PathParsingException(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return "\nCannot parse path:" + self.path


class HTTPHeaderFormatException(Exception):
    def __init__(self, header):
        self.header = header

    def __str__(self):
        ret = "\nCannot parse following HTTP header: \n"
        ret += self.header

        return ret
