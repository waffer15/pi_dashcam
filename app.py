from flask import Flask, render_template, Response, url_for, jsonify, send_from_directory, redirect
from threading import Thread
import datetime as dt
import os
from subprocess import run
import re
import glob
import picamera  

app = Flask(__name__)

video_dir = '/home/pi/dashcam/videos/'

# constants
RESOLUTION = (1280, 720)
FRAMERATE = 25
RECORD_TIME = 120
MAX_FILES = 9

# global variables
save = False
vids = glob.glob(video_dir + '*')
video_num = 0

# calulate the number of the next video
if len(vids) > 0:
    newest = max(vids, key=os.path.getctime)
    video_num = int(re.search(r'\d+', newest).group()) + 1

# setting up the camera
camera = picamera.PiCamera()
camera.resolution = RESOLUTION
camera.framerate = FRAMERATE
   
# circular stream that will save specified chunk of video in memory
# 'seconds' is not perfect and will rarely save the exact time
stream = picamera.PiCameraCircularIO(camera, seconds=RECORD_TIME)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(directory='/home/pi/dashcam/', filename='favicon.ico')


@app.route('/test') 
def test(): 
   return render_template('test.html')


@app.route('/save/<int:time>')
def save(time):
    global stream
    global video_num

    # create base video name and the filename for h264 format
    video_base = f'{video_dir}video{video_num % MAX_FILES}'
    file_name = video_base + '.h264'

    # save the video as h264
    stream.copy_to(file_name, seconds=time)

    video_num += 1
    return redirect(url_for('dashcam'))


@app.route('/dashcam')
def dashcam():
    sorted_dir = sorted(os.listdir(video_dir))
    return render_template('dashcam.html', videos=sorted_dir)


@app.route('/shutdown')
def shutdown():
    os.system('sudo poweroff')
    return 'shutting down'


def stream_generator():
   global camera
   while True:
       camera.capture('frame.jpg', use_video_port=True)
       yield (b'--frame\r\n' 
              b'Content-Type: image/jpeg\r\n\r\n' + open('frame.jpg', 'rb').read() + b'\r\n')
 

@app.route('/video_feed') 
def video_feed(): 
   return Response(stream_generator(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame') 


@app.route('/download/<path:file_name>')
def download(file_name):
    if 'mp4' not in file_name:
        file_name = convert_to_mp4(file_name)
    return send_from_directory(directory=video_dir, filename=file_name, as_attachment=True)


@app.route('/delete/<path:file_name>')
def delete(file_name):     
    rm_cmd = f'rm {video_dir}{file_name}'
    run([rm_cmd], shell=True)
    return redirect(url_for('dashcam'))


def start_camera():
    global camera
    global stream
     
    camera.start_recording(stream, format='h264')
    camera.annotate_background = picamera.Color('black')
    try:
        while True:
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.wait_recording(1)
    finally:
        camera.stop_recording()


def convert_to_mp4(file_name):
    mp4_file = file_name.replace('h264', 'mp4')
    convert_cmd = f'MP4Box -add {video_dir}{file_name} {video_dir}{mp4_file}'
    run([convert_cmd], shell=True)
    return mp4_file 


thread = Thread(target=start_camera)
thread.daemon = True
if __name__ == '__main__':
    thread.start()
    app.run(host='0.0.0.0', threaded=True)

