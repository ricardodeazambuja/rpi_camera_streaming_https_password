#!/bin/bash

echo "Access through https://maplesyruppicam.local/"
echo
echo "To create the certificate (valid for 365 days):"
echo "openssl req -new -x509 -keyout localhost.pem -out localhost.pem -days 365 -nodes"
echo


CMD="sudo python rpi_camera_streaming_https_password.py user:pass"

echo "The browser will ask for the username and password that were passed as arguments:"
echo $CMD
echo
$CMD
