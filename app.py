from flask import Flask, render_template, Response, url_for
from threading import Thread
import os
import re
import glob
import picamera  

app = Flask(__name__)

video_dir = '/home/pi/dashcam/videos/'

RESOLUTION = (1920, 1080)
FRAMERATE = 25
RECORD_TIME = 60 * 5
MAX_FILES = 9

save = False
stop = False

camera = picamera.PiCamera()
stream = picamera.PiCameraCircularIO(camera, seconds=RECORD_TIME)

@app.route('/test') 
def test(): 
   return 'server running'


@app.route('/dashcam')
def dashcam():
   return render_template('dashcam.html')


@app.route('/save')
def save():
    global save
    save = True
    return 'saved video'


def stream_generator():
   global camera
   while True: 
       camera.capture('frame.jpg')
       yield (b'--frame\r\n' 
              b'Content-Type: image/jpeg\r\n\r\n' + open('frame.jpg', 'rb').read() + b'\r\n')
 

@app.route('/video_feed') 
def video_feed(): 
   return Response(stream_generator(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame') 


def start_camera():
    global save
    global camera
    global stream

    vids = glob.glob(video_dir + '*')
    video_num = 0

    if len(vids) > 0:
        newest = max(vids, key=os.path.getctime)
        video_num = int(re.search(r'\d+', newest).group()) + 1
    
    camera.start_recording(stream, format='h264')
    try:
        while True:
            camera.wait_recording(1)
            if save == True:
                file_name = f'{video_dir}video{video_num % MAX_FILES}.h264'
                stream.copy_to(file_name)
                video_num += 1
                save = False
    finally:
        camera.stop_recording()


thread = Thread(target=start_camera)
thread.daemon = True
if __name__ == '__main__':
    thread.start()
    app.run(host='0.0.0.0', threaded=True)

