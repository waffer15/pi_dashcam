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

RESOLUTION = (1920, 1080)
FRAMERATE = 25
RECORD_TIME = 60 * 2
MAX_FILES = 9

save = False
stop = False

camera = picamera.PiCamera()
stream = picamera.PiCameraCircularIO(camera, seconds=RECORD_TIME)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(directory='/home/pi/dashcam/', filename='favicon.ico')


@app.route('/test') 
def test(): 
   return render_template('test.html')


@app.route('/save')
def save():
    global save
    save = True
    return redirect(url_for('dashcam'))


@app.route('/dashcam')
def dashcam():
    return render_template('dashcam.html', videos=os.listdir(video_dir))


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


@app.route('/download/<path:filename>')
def download(filename):
    new_filename = convert_to_mp4(filename[:(len(filename)-5)])
    return send_from_directory(directory=video_dir, filename=new_filename)


@app.route('/delete/<path:filename>')
def delete(filename):     
    rm_cmd = f'rm {video_dir}{filename}'
    run([rm_cmd], shell=True)
    return redirect(url_for('dashcam'))


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
    camera.annotate_background = picamera.Color('black')
    try:
        while True:
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.wait_recording(1)
            if save == True:
                # create base video name and the filename for h264 format
                video_base = f'{video_dir}video{video_num % MAX_FILES}'
                file_name = video_base + '.h264'

                # save the video as h264
                stream.copy_to(file_name)

                video_num += 1
                save = False
    finally:
        camera.stop_recording()


def convert_to_mp4(file_name):
    new_filename = f'{file_name}.mp4'
    convert_cmd = f'MP4Box -add {video_dir}{file_name}.h264 {video_dir}{new_filename}'
    run([convert_cmd], shell=True)
    return new_filename


thread = Thread(target=start_camera)
thread.daemon = True
if __name__ == '__main__':
    thread.start()
    app.run(host='0.0.0.0', threaded=True)

