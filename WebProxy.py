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
#replace urls to target proxy
#gzip before sending
#implement function: parseurl(function to parse url and obtain target_url)
#try to support headers(e.g.gzip, content-length, keep-alive)

class WebProxyHandler(BaseHTTPRequestHandler):
    sessions = dict()
    domain_pat = re.compile('(?<=://)[^/]*')
    schema_pat = re.compile('[a-z]*://')

    @classmethod 
    def remove_schema(cls, url):#removes schema from url and return it.
        schema_match = WebProxyHandler.schema_pat.match(url)
        schema = str()
        if not schema_match is None:
            schema = schema_match.group()
            url = url.replace(schema, '')
        else:
            schema = 'http://'

        return (url, schema)


    @classmethod
    def replace_url(cls, content, server_host, server_port, domain):
        urls = re.findall(r'href=[\'"]?([^\'" >]+)', content)

        temp = re.findall(r'src=[\'"]?([^\'" >]+)', content)

        if not urls is None and not temp is None:
            urls.extend(temp)
        elif urls is None:
            urls = temp

        if urls is None:
            raise URLReplacementException()
        else:
            for change_from_url in urls:
                original_url = change_from_url
                print 'change: ' +change_from_url
                if not 'http' in server_host:
                    server_host = 'http://' + server_host
                change_to_url = server_host + ':' + str(server_port) + '?targeturl='

                change_from_url = str(change_from_url)

                change_from_url, schema = WebProxyHandler.remove_schema(change_from_url)

                if change_from_url[0] != '/':
                    change_from_url = '/' + change_from_url

                if not domain in change_from_url:
                    change_from_url = domain + change_from_url

                change_from_url = schema + change_from_url

                change_from_url = WebProxyHandler.percent_encode(change_from_url)
                change_to_url += change_from_url
                print 'change_to: ' + change_to_url
                content = content.replace(original_url, change_to_url)

            print 'return '
            print content

            return content

    @classmethod
    def parse_path(cls, path):
        index = path.find('?')

        param_str = path[(index + 1):]

        param = param_str.split('=')

        return param


    
    @classmethod
    def percent_encode(cls, url):
        url = urllib.quote(url, safe = '')

        return url.replace('.', '%2E')

    @classmethod
    def percent_decode(cls, url):
        url = url.replace('%2E', '.')

        return urllib.unquote(url)

    def sendHttpHeader(self, res):
        for key, value in res.headers.iteritems():
            if not 'gzip' in value and not 'content-length' in key.lower() and not 'keep-alive' in value.lower():
                print '%s: %s' % (key, value)
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

            targeturl = str()
            domain = str()

            param = WebProxyHandler.parse_path(self.path)

            if param[0] == "targeturl":
                targeturl = param[1]
                targeturl = WebProxyHandler.percent_decode(targeturl)

                print 'targeturl: ' + targeturl

                if not "http" in targeturl:
                    targeturl = 'http://' + targeturl

                print 'here'

                domain = WebProxyHandler.domain_pat.search(targeturl).group()

                print 'domain: ' + domain

            else:#instead of raising exception return form
                print "header format wrong"
                raise HTTPHeaderFormatException('sorry not implemented ')

            print 'targeturl: ' + targeturl

            res = session.get(targeturl)

            logging.info('session.get: ' + targeturl)

            self.send_response(res.status_code)

            self.sendHttpHeader(res)

            self.end_headers()

            if 'text/html' in res.headers['content-type']:
                ret = WebProxyHandler.replace_url(res.content, 'localhost', 8080, domain)
                self.wfile.write(ret)
            else:
                self.wfile.write(res.content)
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
