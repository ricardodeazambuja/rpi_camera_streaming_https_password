"""https://github.com/ricardodeazambuja/rpi_camera_streaming_https_password

Experiment using a canvas to overlay information...


Information on HTML Canvas:
- https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Drawing_shapes

Based on / using ideas from: 
- https://picamera.readthedocs.io/en/release-1.13/recipes2.html#web-streaming 
- https://github.com/tianhuil/SimpleHTTPAuthServer/blob/master/SimpleHTTPAuthServer/__main__.py
- https://stackoverflow.com/questions/19705785/python-3-simple-https-server
"""
import rpi_camera_streaming_https_password

# from PIL import Image, ImageDraw

# Uses canvas to programmatically overlay something on top of the image.
PAGE = """\
<html>
<head>
<title>picamera MJPEG streaming demo using https and password</title>
</head>
<body>
<h1>PiCamera MJPEG Streaming Demo Using Https, User and Password</h1>
<div style="position: relative;">
 <img src="stream.mjpg" width=640 height=480 style="position: absolute; left: 0; top: 0; z-index: 0; border:1px solid #c3c3c3;"/>
 <canvas id="canvas" width=640 height=480 style="position: absolute; left: 0; top: 0; z-index: 1;"/>
</div>

<script>
function draw_rect(xmin, ymin, xmax, ymax, width, color) {{
    ctx.lineWidth = width;
    ctx.strokeStyle = color;
    ctx.strokeRect(xmin+width,ymin+width,xmax-2*width,ymax-2*width);
}}

var canvas = document.getElementById('canvas');
var ctx = canvas.getContext("2d");

{rectangles}

ctx.font = "30px Arial";
ctx.fillText("Hello World", 10, 50);

</script>
</body>
</html>
"""

draw_rectangle = "draw_rect({xmin}, {ymin}, {xmax}, {ymax}, {width}, '{color}');\n"

rectangles = ''.join([draw_rectangle.format(xmin=0, ymin=0, xmax=100+i, ymax=100+i, width=3, color="#00ff00") for i in range(0,100,20)])

PAGE = PAGE.format(rectangles=rectangles)

rpi_camera_streaming_https_password.PAGE = PAGE

if __name__ == '__main__':
    rpi_camera_streaming_https_password.main()