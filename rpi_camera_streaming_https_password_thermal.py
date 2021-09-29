"""https://github.com/ricardodeazambuja/rpi_camera_streaming_https_password

Based on / using ideas from: 
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
from hashlib import sha256
import argparse

from matplotlib import cm
import numpy as np

from PIL import Image

#
# MLX90640 library from Adafruit. It will install the library and dependencies: 
# sudo pip install adafruit-circuitpython-mlx90640
# It's necessary to enable i2c:
# $ sudo raspi-config=>interface options=>i2c
# Or editing /boot/config.txt by adding:
# dtparam=i2c_arm=on
# dtparam=i2c1_baudrate=1000000
#
import board
import busio
import adafruit_mlx90640



MAX_TEMP = 40

PAGE = f"""\
<html>
<head>
<title>picamera MJPEG (+ thermal camera overlaid) streaming demo using https and password</title>
</head>
<body>
<div style="position: relative;">
 <img src="stream.mjpg" style="width: 90vw; height: 90vh; position: absolute; left: 0; top: 0; z-index: 0; border:1px solid #c3c3c3;"/>
 <p style="position: absolute; left: 0; top: 0; z-index: 1;"> MAX_TEMP (strong red) = {MAX_TEMP}&degC
</div>

</script>
</body>
</html>
"""



i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)

mlx = adafruit_mlx90640.MLX90640(i2c)
print("MLX addr detected on I2C", [hex(i) for i in mlx.serial_number])
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_16_HZ
frame_thermal = np.asarray([0] * 768)

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
    HASH = ''
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
            return
        
        received_user_pass = base64.b64decode(self.headers.get('Authorization')[6:]).decode("utf-8") +'\n'
        if sha256(received_user_pass.encode('utf-8')).hexdigest() == str(self.HASH):
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
                        stream = io.BytesIO(frame)
                        image = Image.open(stream)
                        cropped = image.crop((200,10,550,455))

                        valid = False
                        while not valid:
                            try:
                                mlx.getFrame(frame_thermal)
                                valid = True
                            except ValueError:
                                # these happen, no biggie - retry
                                print("Thermal camera failed...")
                            
                        background = cropped
                        cmapped = (cm.jet(np.rot90(frame_thermal.reshape(24, 32)/MAX_TEMP))*255).astype('uint8')
                        overlay = Image.fromarray(cmapped).resize(cropped.size)

                        background = background.convert("RGBA")
                        overlay = overlay.convert("RGBA")

                        new_img = Image.blend(background, overlay, 0.7).convert("RGB")
                        #new_img = overlay.convert("RGB")
                        
                        stream.seek(0)
                        new_img.save(stream, format='JPEG')
                        frame = stream.getbuffer()
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
        camera.rotation = 180
        camera.hflip = True
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
    parser.add_argument('hash', help='echo username:password | sha256sum | cut -d " " -f1')
    args = parser.parse_args()

    StreamingHandler.HASH = args.hash
    

    start_streaming()

if __name__ == '__main__':
    main()
