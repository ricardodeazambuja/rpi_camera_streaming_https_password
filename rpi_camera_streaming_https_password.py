"""Based on / using ideas from: 
- https://picamera.readthedocs.io/en/release-1.13/recipes2.html#web-streaming 
- https://github.com/tianhuil/SimpleHTTPAuthServer/blob/master/SimpleHTTPAuthServer/__main__.py
- https://stackoverflow.com/questions/19705785/python-3-simple-https-server
"""
import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
import ssl
import base64
import argparse

# from PIL import Image, ImageDraw

PAGE = """\
<html>
<head>
<title>picamera MJPEG streaming demo using https and password</title>
</head>
<body>
<h1>PiCamera MJPEG Streaming Demo Using Https, User and Password</h1>
<div style="position: relative;">
 <img src="stream.mjpg" style="width:100%; position: absolute; left: 0; top: 0; z-index: 0; border:1px solid #c3c3c3;"/>
</div>

</script>
</body>
</html>
"""

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    KEY = ''
    def do_authhead(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        if self.headers.get('Authorization') is None:
            print("Not authorized!")
            self.do_authhead()
            self.wfile.write('No authorization header received!'.encode("utf-8"))
        elif self.headers.get('Authorization') == 'Basic '+ str(self.KEY):
            print("Authorized!")
            if self.path == '/':
                self.send_response(301)
                self.send_header('Location', '/index.html')
                self.end_headers()
            elif self.path == '/index.html':
                content = PAGE.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
            elif self.path == '/stream.mjpg':
                self.send_response(200)
                self.send_header('Age', 0)
                self.send_header('Cache-Control', 'no-cache, private')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
                self.end_headers()
                try:
                    while True:
                        with self.output.condition:
                            self.output.condition.wait()
                            frame = self.output.frame
                        # How to modify the image on-the-fly using PIL (it will reduce the fps...)
                        # Maybe this could speed up: https://picamera.readthedocs.io/en/release-1.13/api_mmalobj.html#file-input-jpeg-encoding
                        # stream = io.BytesIO(frame)
                        # image = Image.open(stream)
                        # dimage = ImageDraw.Draw(image)
                        # dimage.text((100, 100 + 10), "Test!!!", fill='red')
                        # dimage.rectangle([(50, 50), (100, 100)], outline='green')
                        # stream.seek(0)
                        # image.save(stream, format='JPEG')
                        # frame = stream.getbuffer()
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                except Exception as e:
                    logging.warning(
                        'Removed streaming client %s: %s',
                        self.client_address, str(e))
            else:
                self.send_error(404)
                self.end_headers()
        else:
            self.do_authhead()
            self.wfile.write(self.headers.get('Authorization').encode("utf-8"))
            self.wfile.write('Authentication Failed!'.encode("utf-8"))

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True



def start_streaming():
    print("Starting...")
    with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
        output = StreamingOutput()
        camera.start_recording(output, format='mjpeg')
        try:
            address = ('0.0.0.0', 443) # You need to run this script with sudo because of 0.0.0.0 and 443!
            StreamingHandler.output = output
            rpiserver = StreamingServer(address, StreamingHandler)
            rpiserver.socket = ssl.wrap_socket(rpiserver.socket,
                                   server_side=True,
                                   certfile='./localhost.pem',
                                   ssl_version=ssl.PROTOCOL_TLS)
            print("Web server is going up!")
            rpiserver.serve_forever()
        except KeyboardInterrupt:
            print('\rWeb server closing')
            rpiserver.server_close()
        finally:
            camera.stop_recording()



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('key', help='username:password')
    args = parser.parse_args()

    StreamingHandler.KEY = base64.b64encode(args.key.encode("utf-8")).decode('ascii')

    start_streaming()

if __name__ == '__main__':
    main()
