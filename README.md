# MotionSpot
Object detection and tracking add-on for Motion

A basic Python script for Motion (https://motion-project.github.io/) to add object detection and tracking capabilities using the Ultralytics Yolo model (https://docs.ultralytics.com/)

## Dependencies
1. Python3
2. A number of Python modules, which might already be present on your system: numpy, signal, pathlib, psutil, smtplib, requests, email, PIL, io
3. Ultralytics Python module from Ultralytics (www.ultralytics.com)
4. One of the Yolo models - the current code has been tested with yolov8n and yolov8s

## Installation instructions

1. copy motionspot.py and motionspotcfg.py to /etc/motion (or /etc/motioneye, if using MotionEye)
2. Download one of the Yolo models to /etc/motion (or /etc/motioneye) from here: https://github.com/ultralytics/ultralytics/blob/main/docs/en/tasks/detect.md The current code has been tested with Yolov8 nano and small.
3. Install Python modules (instructions will vary based on your distribution):  
 a. `pip install ultalytics`  
 b. `pip install numpy`  
4. Change settings in motionspotcfg.py as needed - there are explanatory descriptions for each setting.
5. In Motion camera configs, for each camera you want object detection, set the following settings as per below:  
   a. for `on_event_start`, add the followint to existing code: `/usr/bin/python3 /etc/motion/motionspot.py`  
   b. for `on_movie_end`, add the following to existing code: `/usr/bin/python3 /etc/motioneye/motionspot.py file_save %$ %v %f`  
   c. set `picture_output on`  
   d. set `picture_filename` to: `images/%v.[camera_name].%H-%M-%S.%q` - replace [camera_name] with actual camera name. It is important not to use full stop (.) in the camera name - as it is used for delimiting fields in the name of saved snapshots  
   e. (optional) - configure `images` to mount off tmpfs in ram - to avoid excessive writes to permanent storage, and possibly speed processing up

## Functional overview

1. MotionSpot is designed to be started by the Motion process. On every event_start, Motion will attempt to start MotionSpot. MotionSpot itself will check if there is another instance running, and quit if it finds one
2. MotionSpot will keep looping over the images saved by Motion, and when it finds the requested object class or classes, it will rename the snapthot from `snapshot.jpg` to `snapthos.jpg.detection`
3. On `movie_save`, Motion will invoke MotionSpot again, with the name of the filename of the saved movie as one of the parameters. MotionSpot will check if there are any .detection files corresponding to the event of the saved movie file. If it finds any, it will leave the move file in place. If it doesn't, it deletes it
