# IP camera: HTTP admin panel, RTSP stream port and Telnet (common on cheap cameras)
FROM alpine:3.22
RUN apk add --no-cache python3 busybox-extras
COPY camera.py /camera.py
CMD telnetd -p 23 -l /bin/sh && exec python3 /camera.py
