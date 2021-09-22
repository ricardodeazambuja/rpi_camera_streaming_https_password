#!/bin/bash

echo "For more details, check https://github.com/ricardodeazambuja/rpi_camera_streaming_https_password"
echo

echo "Access through https://maplesyruppicam.local/"
echo
echo "To create the certificate (valid for 365 days):"
echo "openssl req -new -x509 -keyout localhost.pem -out localhost.pem -days 365 -nodes"
echo


echo "Choose a user:pass and hash it:"
echo "echo user:pass | sha256sum | cut -d " " -f1"
echo "As an example, the output for 'user:pass' is 6f5fde15fa7df3fb7eb78d58425165120d5b0a95f8af68e73a638937bf76e52e"
echo "===> Save in this script ONLY the final hash, not the user:pass, or the use of a hash is useless :D <=== "
echo 

CMD="sudo python rpi_camera_streaming_https_password.py 6f5fde15fa7df3fb7eb78d58425165120d5b0a95f8af68e73a638937bf76e52e"

echo "The browser will ask for the username and password that were used to generate the hash:"
echo $CMD
echo
$CMD
