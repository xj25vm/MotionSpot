# v0.031 - 29-01-2025 - with single detection loop for all cameras
# copyright(c) Sebastian Arcus (s . arcus @ open-t . co . uk)
# dependencies: ultralytics, numpy


import sys
import time
import os
import glob
from datetime import datetime

# configuration file
from motionspotcfg import *


def log_write(msg_log_level, msg):
    # define log_path as global as we attempt to modify it further down
    global log_path
    global log_level
    # check if log_path has been initialised
    try:
        log_path
    except:
        # initialise log_path to empty variable if not defined
        log_path = ''

    try:
        log_level
    except:
        # default log_level to error
        log_level = 'e'

    if log_path == '':
        # logging is not enabled - just return
        return True

    if not (log_level == 'e' or log_level == 'w' or log_level == 'i' or log_level == 'd'):
        # change message to output wrong log_level error
        msg = 'unknown log_level setting: ' +  log_level
        # set log_level to 'error' so the above gets output to log
        log_level = 'e'

    # generate verbose level for output
    if msg_log_level == 'e':
        msg_log_level_full = 'error'
    elif msg_log_level == 'w':
        msg_log_level_full = 'warning'
    elif msg_log_level == 'i':
        msg_log_level_full = 'info'
    elif msg_log_level == 'd':
        msg_log_level_full = 'debug'
    else:
        msg_log_level = 'e'
        msg_log_level_full = 'error'
        msg = 'unkown msg_log_level passed to function: ' + msg_log_level



    if log_path == 'stdout':
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg_log_level_full}: [{event_type}] {msg}\n")

    else:
        try:
            with open(log_path, 'a') as log_file:
                log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg_log_level_full}: [{event_type}] {msg}\n")
        except IOError:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - error: unable to open log file")
            return False

    return True



def check_detection_loop():
    import subprocess
    import signal

    # use just one lock file for all cameras for a single detection loop process
    pid_file = os.path.join(lock_path, f'motionspot.pid')

    # Check if PID file exists
    if os.path.exists(pid_file):
        # Read the PID from the file
        with open(pid_file, 'r') as f:
            content = f.read().strip()

            if content:  # Check if the content is not empty
                detection_script_pid = int(content)

                # Log the contents of the PID lock file
                log_write('d', f'detection loop pid file contains: {detection_script_pid}')

            else:
                # If the process does not exist (OSError), we need to restart it
                log_write('i', 'detection loop pid file is empty - start detection loop')

                # Save the new PID to the PID file
                with open(pid_file, 'w') as f:
                    f.write(str(os.getpid()))

                # there is no pid in the file
                return(False)


        # Check if the detection script is still running
        try:
            os.kill(detection_script_pid, 0)  # Signal 0 checks if the process exists

        except OSError:
            # If the process does not exist (OSError), we need to restart it
            log_write('i', 'no detection loop process found - start detection loop')

            try:
                # Save the new PID to the PID file
                with open(pid_file, 'w') as f:
                    f.write(str(os.getpid()))
            except Exception as e:
                log_write('e', f'failed to write to detection loop pid file - {str(e)}')

            # detection loop is no running
            return(False)

        else:
            # exit script as another detection loop is already running
            log_write('d', f'another detection loop is running - exit')
            return(True)

    else:
        # If PID file does not exist, start the Python detection script
        print(f'no detection loop pid file found - start detection loop')

        try:
            # Save the PID to the PID file
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            log_write('e', f'error writing to detection loop pid file - {str(e)}')

        return(False)


def movie_save():

    if (cameras[camera_name]['control_led'] == True):
        # turn down the led at the end of the movie
        control_led(camera_name, 0)

    # check if there are any *.jpg.detection files in the image dir belonging to this event
    detection_files = glob.glob(f'{img_path}/{camera_name}/{event_id}_*.detection')
    # check if there are any unprocessed files for this event
    unprocessed_files = glob.glob(f'{img_path}/{camera_name}/{event_id}_*.jpg')

    if (len(detection_files) == 0 and len(unprocessed_files) == 0):
        log_write('d', f'no detection or pending unprocessed files found for event_id {event_id} - remove {saved_file}')

        if (os.path.isfile(saved_file)):
            os.remove(saved_file)

    elif (len(detection_files) > 0):
        log_write('i', f'detection files found for event_id: {event_id} - keep {saved_file}')

    elif (len(unprocessed_files) > 0):
        log_write('i', f'pending unprocessed jpg file(s) found - wait to finish processing')
        # sleep and check again for detectionf files in case the cpu is busy
        time.sleep(10);
        detection_files = glob.glob(f'{img_path}/{camera_name}/{event_id}_*.detection')

        if (len(detection_files) == 0):
            log_write('i', f'still no detection files found for event_id: {event_id} - delete {saved_file}')

            if(os.path.isfile(saved_file)):
                os.remove(saved_file)

        else:
            log_write('i', f'detection files found for event_id: {event_id} - keep {saved_file}');

    # can't remove remaining snapthot files belonging to this event, as it crashes the detection loop
    # if it is in the middle of processing some of them
    # remove all snapshot files belonging to this event - regardless of detections
    #for (file in glob.glob(f'{img_path}/{camera_name}/{event_id}_*.jp*g')
    #    if(os.path.isfile(file)):
    #        os.remove(file)



def detection_loop():
    from pathlib import Path
    import psutil

    # declare as global variable so that we can change the global value
    global event_type

    # dictionary to keep track of tracked object centers through the frames in current event
    global centre_sets
    # dictionary to keep track of object counters for each class of counter change objects in the frames of current event
    global counter_sets
    centre_sets = {}
    counter_sets = {}

    # initialise centre_sets dictionaries for all cameras
    for camera_name in cameras:
        centre_sets[camera_name] = {}
        counter_sets[camera_name] = {}

    # change event_type when we enter the detection loop
    event_type = 'detection_loop'

    # initialise centre sets dictionary

    # check if there are leftover snapshots from previous runs and remove
    # as event numbers are reset on motioneye restarts, and can overlap with future events
    stale_snapshots = glob.glob(f'{img_path}/*.jpg*')

    if ( len(stale_snapshots) > 0 ):
        log_write('i', f'removing stale snapshots from previous Motioneye runs')

        for stale_snapshot in stale_snapshots:
            if(os.path.isfile(stale_snapshot)):
                log_write('i', f'removing stale snapshot: {stale_snapshot}')
                os.remove(stale_snapshot)


    log_write('i', f'starting Python detection loop for all cameras')

    # loop continuously waiting for pictures to be saved
    while True:
        # reset snapshots_found flag
        snapshots_found = False

        # check if there are any unprocessed files
        if (len(glob.glob(f'{img_path}/*.jpg')) != 0): 
            # set flag as we found some snapshots to process
            snapshots_found = True

            # store start time for statistics later
            start_time = time.time()

            # pick the first file in the list
            file = sorted(glob.glob(img_path + '/*.jpg'))[0]

            # extract event id - all characters up to the first '.' character
            # have to use '.' for splitting fields as camera names contain underscore
            event_id = os.path.basename(file).split('.')[0]
            # extract camera_name - second set of characters betweeen '.' characters
            camera_name = os.path.basename(file).split('.')[1]

            # check for presence detection files belonging to this event and camera
            detection_files_count = len(glob.glob(img_path + '/' + event_id + '.' + camera_name + '*.detection'))

            # stop after 4 detections if camera has alerts enabled, and after 1 detection if no alerts are enabled for this camera
            if (detection_files_count >= 4 or (detection_files_count >=1  and not 'active_alerts' in cameras[camera_name])):

                # remove current file as we already have enough detections for this event
                log_write('d', f'person already detected for event:  {event_id} - remove {file}')
                os.remove(file)

            else:

                log_write('d', f'processing file: {file}')

                # event_id is needed for motion detection
                detection_type, detection_object_class  = yolo_detect(file, camera_name, event_id)

                if (detection_type == 'presence_low'):
                    # only turn on the led, don't send alerts as we have a low confidence detection
                    if (cameras[camera_name]['control_led'] == True):
                        # turn on led
                        control_led(camera_name, 100)

                    #log_write(f'no detection of sufficient confidence in {file} - remove')
                    os.remove(file)

                elif (detection_type != ''):

                    if (cameras[camera_name]['control_led'] == True):
                        # turn on led
                        control_led(camera_name, 100)

                    # rename jpg file
                    #log_write('i', f'detection: {object_class} {detection_type} in {file} with score {str(score)}')

                    # send alert for 1st, 2nd and 4th detections
                    # 'detection_files_count' holds the number of detections before current run
                    if (detection_files_count == 0 or detection_files_count == 1 or detection_files_count == 3):
                        # check if there are any active alerts settings on this camera
                        if ('active_alerts' in cameras[camera_name]): 
                            send_alert(file, camera_name, detection_object_class)

                    # rename file from .jpg to .jpg.detection
                    os.rename(file, file + '.detection')


                else:
                    #log_write(f'no detection in {file} - remove')
                    os.remove(file)

                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000

                log_write('d', f'finished processing file: {file} in {duration_ms:.2f}ms')

                # check if there are other files saved in this second and remove to avoid further processing
                name_minus_frame_number = Path(file).stem[0:-2]

                other_frames_in_this_second = sorted(glob.glob(f'{img_path}/{name_minus_frame_number}??.jpg'))

                # remove the other frames in this second to avoid too much processing
                if (other_frames_in_this_second != False):
                    for frame in other_frames_in_this_second:
                        if(os.path.isfile(frame)):
                            log_write('d', f'remove other frames in same second: {frame}')
                            os.remove(frame)

        # if no new snapshots were found, sleep 0.2 seconds and check if motion process still exists
        if (snapshots_found == False):
            time.sleep(0.2)

            # check if there is still a motion process about - otherwise terminate
            motion_found = False

            # go through all processes looking for 'motion'
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == 'motion':
                    # we found motion, so exit the for loop
                    motion_found = True
                    break

            if (motion_found == False):
                log_write('w', f'motion process has gone away - exiting')
                sys.exit()




def yolo_detect(file, camera_name, event_id):
    # use global centreset variable
    global centre_sets
    global counter_sets

    try:
        # mode.predict can take multiple images as input, so returns an array of results
        results = models[camera_name].predict(file, conf=0.3, save=False)
    except Exception as e:
        log_write('e', f'error: failed to run model.predict - {str(e)}')
        return ('', '')

    # we passed only one image in, so expect only one result out
    result = results[0]

    # check how many detection boxes have been returned
    #detections = len(result.boxes)

    # run presence detection on high threshold, if there are any object classes configured for it
    if 'detect_presence_classes' in cameras[camera_name]:
        # loop through object classes configured for static detection
        for class_name in cameras[camera_name]['detect_presence_classes']:
            # check if the name of the object class is valid
            if class_name not in models[camera_name].names.values():
                log_write('e', f'object class {class_name} not a valid option for presence detection')
                return ('', '')

            else:
                # detections are represented by boxes
                for box in result.boxes:
                    # print class, coordinates and confidence
                    #cords = box.xyxy[0].tolist()
                    #cords = [round(x) for x in cords]
                    box_class_name = result.names[box.cls[0].item()]
                    confidence = int(round(box.conf[0].item(), 2) * 100)

                    if confidence > 60 and box_class_name == class_name:
                        #print("Object type:", box_class_name)
                        #print("Coordinates:", cords)
                        #print("Probability:", conf)
                        #print("----")
                        # return as soon as we found one of the static classes
                        log_write('d', f'detection: presence_high; object class: {box_class_name}; confidence: {confidence}; file: {file}')
                        return ('presence_high', class_name)


    # section for detecting motion based on the movement of object centres
    if 'detect_motion_classes' in cameras[camera_name]:
        # loop through object classes configured for motion detection
        for class_name in cameras[camera_name]['detect_motion_classes']:
            # check if the name of the object class is valid
            if class_name not in models[camera_name].names.values():
                log_write('e', f'object class {class_name} not a valid option for motion detection')
                return ('', '')

        # perform motion detection on all requested classes for motion at the same time

        # detect and track objects in the current frame - preserve object id's between frames
        results = models[camera_name].track(file, persist=True)

        # if centreset for this camera doesn't have an event_id, or the event_id is not for this event
        if ('event_id' not in centre_sets[camera_name] or centre_sets[camera_name]['event_id'] != event_id):
            # reset the centreset data
            centre_sets[camera_name].clear()
            # set event_id to current event_id
            centre_sets[camera_name]['event_id'] = event_id
            centre_sets[camera_name]['centreset'] = {}

            # reset all trackers (one tracker per frame in previous event) on this model, 
            # to reset all object ids and tracking information from previous event
            for tracker in models[camera_name].predictor.trackers:
                 tracker.reset()

            # initialise prev_centreset to empty dictionary
            prev_centreset = {}

        else:
            # load previous centre set into variable
            prev_centreset = centre_sets[camera_name]['centreset']
        

        # Dictionary to store current frame centres (bounding box center)
        curr_centreset = {}

        # detections are represented by boxes
        for box in result.boxes:
            # print class, coordinates and confidence
            #cords = box.xyxy[0].tolist()
            #cords = [round(x) for x in cords]
            box_class_name = result.names[box.cls[0].item()]
            confidence = int(round(box.conf[0].item(), 2) * 100)

            if confidence > 60 and box_class_name in cameras[camera_name]['detect_motion_classes']:
                # extract bounding box coordinates and convert them from tensor to scalar values with .tolist()
                x1, y1, x2, y2 = box.xyxy[0].tolist()  # Bounding box coordinates

                # object id for tracking - extract scalar from tensor object so it can be used for dictionary key lookup below
                if box.id is not None:
                    obj_id = box.id.item()
                else:
                    obj_id = ''

                # Calculate the center of the bounding box
                centre = (((x1 + x2) / 2), ((y1 + y2) / 2))

                # if this is not the first frame with detections and this object exists in previous centre set
                if obj_id != '' and obj_id in prev_centreset:
                    prev_centre = prev_centreset[obj_id]
                    distance = numpy.sqrt((prev_centre[0] - centre[0])**2 + (prev_centre[1] - centre[1])**2)

                    # add centre to centreset for this camera - doing this above the if statement overwrites the current centre for some reason
                    centre_sets[camera_name]['centreset'][obj_id] = centre

                    # If the distance is greater than the threshold, object has moved
                    if distance > 55 and distance < 400:

                        # return as soon as we detect the first object movement
                        log_write('d', f'detection: motion; object class {box_class_name}; distance: {distance}; file: {file}')
                        return ('motion', box_class_name)

                else:
                    # add centre to centreset for this camera
                    centre_sets[camera_name]['centreset'][obj_id] = centre

    # section for detecting motion based on changes in counters of objects
    if 'detect_count_classes' in cameras[camera_name]:
        cur_counter_set = {}

        # loop through object classes configured for count change detection
        for class_name in cameras[camera_name]['detect_count_classes']:
            # check if the name of the object class is valid
            if class_name not in models[camera_name].names.values():
                log_write('e', f'object class {class_name} not a valid option for count change detection')
                return ('', '')

        # loop through object classes configured for count change detection
        # and setup an empty count for each in the current counter
        for class_name in cameras[camera_name]['detect_count_classes']:
            cur_counter_set[class_name] = 0

        # if counter_set for this camera doesn't have an event_id, or the event_id is not for this event
        if ('event_id' not in counter_sets[camera_name] or counter_sets[camera_name]['event_id'] != event_id):
            # reset the centreset data
            counter_sets[camera_name].clear()
            # set event_id to current event_id
            counter_sets[camera_name]['event_id'] = event_id
            # initialise an empty dictionary
            counter_sets[camera_name]['counter_set'] = {}

            # initialise prev_counter_set to empty dictionary
            prev_counter_set = {}

        else:
            # load previous counter set into variable
            prev_counter_set = counter_sets[camera_name]['counter_set']

        # count how many objects/boxes of each count change class have been detected
        for box in result.boxes:
            box_class_name = result.names[box.cls[0].item()]

            # increment counters for those classes requested for count change detection
            if box_class_name in cameras[camera_name]['detect_count_classes']:
                # add trucks to car counter - as the library keeps on changing its mind
                # if a vehicle is a truck or a car
                if box_class_name == 'truck':
                    cur_counter_set['car'] += 1
                else:
                    cur_counter_set[box_class_name] += 1

        # check if prev_counter_set is not empty
        if prev_counter_set != {}:
            # check if any of the counters have increased - as decreases means the object has disappeared
            for class_name in cameras[camera_name]['detect_count_classes']:
                if cur_counter_set[class_name] > prev_counter_set[class_name]:
                    # save current counter to counter sets
                    counter_sets[camera_name]['counter_set'] = cur_counter_set
                    log_write('d', f'detection: counter_change; object class: {class_name}; counters: {prev_counter_set[class_name]} vs. {cur_counter_set[class_name]}; file: {file}')
                    return('counter_change', class_name)

        # no changed counter found - save current counter to counter sets
        counter_sets[camera_name]['counter_set'] = cur_counter_set


    # run presence detection again, on low threshold, to be used for turning on the led, if no other detection succeeded
    if 'detect_presence_classes' in cameras[camera_name]:
        # loop through object classes configured for static detection
        for class_name in cameras[camera_name]['detect_presence_classes']:
            # check if the name of the object class is valid
            if class_name not in models[camera_name].names.values():
                log_write('e', f'object class {class_name} not a valid option for presence detection')
                return ('', '')

            else:
                # detections are represented by boxes
                for box in result.boxes:
                    # print class, coordinates and confidence
                    #cords = box.xyxy[0].tolist()
                    #cords = [round(x) for x in cords]
                    box_class_name = result.names[box.cls[0].item()]
                    confidence = int(round(box.conf[0].item(), 2) * 100)

                    if confidence > 30 and box_class_name == class_name:
                        #print("Object type:", box_class_name)
                        #print("Coordinates:", cords)
                        #print("Probability:", conf)
                        #print("----")
                        # return as soon as we found one of the static classes
                        log_write('d', f'detection: presence_low; object class: {box_class_name}; confidence: {confidence}; file: {file}')
                        return ('presence_low', class_name)


    # if we reached this point, there hasn't been a successful detection
    return ('', '')



def send_alert(alert_snapshot, camera_name, detection_object_class):
    import smtplib
    import requests
    from email.mime.multipart import MIMEMultipart
    from email.mime.image import MIMEImage
    from email.mime.text import MIMEText
    from PIL import Image
    from io import BytesIO

    log_write('i', f'start alerts function')
    for alert_name in cameras[camera_name]['active_alerts']:
        # check if alert is defined
        if not alert_name in alerts:
            log_write('e', f'alert {alert_name} is not defined')
            continue

        else:
            # only resize image if an appropriate setting exists
            if 'alert_image_resize' in alerts[alert_name]:
                alert_image_resize = alerts[alert_name]['alert_image_resize']

                # resize the image down for emailing
                with Image.open(alert_snapshot) as img:
                    width, height = img.size
                    new_width = int(width * alert_image_resize)
                    new_height = int(height * alert_image_resize)
                    img_resized = img.resize((new_width, new_height))

                    # Save the resized image to a bytes buffer
                    img_byte_arr = BytesIO()
                    img_resized.save(img_byte_arr, format='JPEG', quality=70)
                    img_byte_arr.seek(0)
                    attachment_jpg = img_byte_arr.read()

            if alerts[alert_name]['alert_type'] == 'email':
                log_write('i', f'send email alert for {alert_snapshot}')

                try:
                    # Set up the email server
                    server = smtplib.SMTP_SSL(alert_smtp_host, alert_smtp_port)
                    server.login(alert_smtp_username, alert_smtp_password)

                    # Create the email message
                    msg = MIMEMultipart()
                    msg['From'] = email_sender
                    msg['To'] = email_recipient
                    msg['Subject'] = f"[{camera_name}] {detection_object_class}"
                    msg.attach(MIMEText("<img src='cid:alert_image'>", 'html', 'utf-8'))


                    # Attach the image
                    image = MIMEImage(attachment_jpg, name=os.path.basename(alert_snapshot))
                    image.add_header('Content-ID', '<alert_image>')
                    msg.attach(image)

                    # Send the email
                    server.sendmail(email_sender, email_recipient, msg.as_string())
                    server.quit()

                except Exception as e:
                    log_write('e', f"error: email alert failed to send to {email_recipient} - {str(e)}")

            elif alerts[alert_name]['alert_type'] == 'telegram':
                # check if telegram userid and bot variables exist
                if (not 'alert_telegram_user_id' in alerts[alert_name]):
                    log_write('e', 'error: missing telegram user_id')
                    continue

                if (not 'alert_telegram_bot_token' in alerts[alert_name]):
                    log_write('e', 'error: missing telegram bot token')
                    continue

                log_write('i', f'sending Telegram alert for {alert_snapshot}')

                # Send the text message
                #params = {
                #    'chat_id': alert_telegram_user_id,
                #    'text': f"[{camera_name}]"
                #}
                #response = requests.post(f"https://api.telegram.org/bot{alerts[alert_name]['alert_telegram_bot_token']}/sendMessage", data=params)

                # Send the snapshot image with caption
                files = {
                    'photo': (os.path.basename(alert_snapshot), open(alert_snapshot, 'rb'), 'image/jpeg')
                }

                params = {'chat_id': alerts[alert_name]['alert_telegram_user_id'],
                          'caption': f'[{camera_name}] {detection_object_class}'}

                response = requests.post(f"https://api.telegram.org/bot{alerts[alert_name]['alert_telegram_bot_token']}/sendPhoto", data=params, files=files)
                # don't use return here, as we have to loop through the rest of the alerts
                if (response.status_code != 200):
                    log_write('e', f'telegram alert failed to send to telegram user_id: {alert_telegram_user_id}')



def control_led(camera_name, brightness):
    import requests
    from requests.auth import HTTPDigestAuth

    # turn on the ir light if turning off the white light
    if (int(brightness) == 0):
        supplementLightMode = 'irLight'
        log_write('i', f'turn off led for camera {camera_name}')
    else:
        supplementLightMode = 'colorVuWhiteLight'
        log_write('i', f'turn on led for camera {camera_name}')


    url = f'http://{cameras[camera_name]["host"]}/ISAPI/Image/channels/1'
    xml_data = f'''<ImageChannel version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
                       <id>1</id>
                       <enabled>true</enabled>
                       <videoInputID>1</videoInputID>
                       <IrcutFilter>
                           <IrcutFilterType>auto</IrcutFilterType>
                           <nightToDayFilterLevel>1</nightToDayFilterLevel>
                           <nightToDayFilterTime>5</nightToDayFilterTime>
                       </IrcutFilter>
                       <Shutter>
                           <ShutterLevel>1/75</ShutterLevel>
                       </Shutter>
                       <SupplementLight>
                          <supplementLightMode>{supplementLightMode}</supplementLightMode>
                          <EventIntelligenceModeCfg>
                              <brightnessRegulatMode>manual</brightnessRegulatMode>
                              <whiteLightBrightness>{brightness}</whiteLightBrightness>
                              <irLightBrightness>100</irLightBrightness>
                          </EventIntelligenceModeCfg>
                       </SupplementLight>
                  </ImageChannel>'''

    # several different ways to pass commands to the camera - by varying the url and xml payload

    #url = 'http://192.168.106.85/ISAPI/Image/channels/1/IrcutFilter'
    '''xml_data = f<IrcutFilter>
                       <IrcutFilterType>night</IrcutFilterType>
                   </IrcutFilter>'''

    #url = 'http://192.168.106.85/ISAPI/Image/channels/1/SupplementLight'
    '''xml_data = f<SupplementLight>
                          <supplementLightMode>colorVuWhiteLight</supplementLightMode>
                          <EventIntelligenceModeCfg>
                              <brightnessRegulatMode>manual</brightnessRegulatMode>
                              <whiteLightBrightness>{brightness}</whiteLightBrightness>
                              <irLightBrightness>100</irLightBrightness>
                          </EventIntelligenceModeCfg>
                   </SupplementLight>'''

    # and the urls for Dahua 5442 camera
    #curl_setopt($cs, CURLOPT_URL,"http://cam-01-ot/cgi-bin/configManager.cgi?action=setConfig&Lighting[0][3].MiddleLight[0].Light=100" );
    #curl_setopt($cs, CURLOPT_URL,"http://cam-01-ot/cgi-bin/configManager.cgi?action=setConfig&Lighting[0][3].Mode=Off" );

    # Send the PUT request
    response = requests.put(
        url,
        data=xml_data,
        headers={'Content-Type': 'application/xml'},
        auth=HTTPDigestAuth(camera_username, camera_password),
        verify=False  # Ignore SSL certificate verification (use with caution)
    )

    # Check the response status and print the result
    if response.status_code == 200:
        return True
    else:
        log_write('e', f"Failed with status code: {response.status_code}")
        log_write('e', f'{response.text}')
        return False



# if started with no argument, attempt to start the detection loop

if (len(sys.argv) == 1):
    # if we have no argument, event_type is detection_loop
    event_type = detection_loop

    # check if there are any cameras defined
    if (len(cameras) == 0):
        log_write('e', f'at least one camera should be configured')
        sys.exit()

    if (check_detection_loop() == True):
        # a detection loop process is already running - just exit
        sys.exit()
    else:
        # load ultralytics libraries here outside any function to be available globally
        # they need loading here only once, when the detection loop starts, as they are large and slow
        try:
            from ultralytics import YOLO
        except Exception as e:
            log_write('e', f'failed to load YOLO from ultralytics - {str(e)}')
            sys.exit()

        try:
            import numpy
        except Exception as e:
            log_write('e', f'failed to load numpy - {str(e)}')
            sys.exit()

        # load the models only once to save cpu cycles
        # one for each camera to keep object ids separate during tracking
        models = {}

        for camera_name in cameras:
            models[camera_name] = YOLO(f'{yolo_model}')

        # start detection loop
        detection_loop()

# only movie_save event uses arguments, no need to process them at the top
else:
    event_type = sys.argv[1]
    camera_name = sys.argv[2]
    event_id = sys.argv[3]
    saved_file = sys.argv[4]

    # there is a bug in motioneye - movie_end and picture_save event names get merged together
    if (event_type == 'file_save' and (saved_file[-3:] == 'mp4' or saved_file[-3:] == 'avi')):
        event_type = 'movie_save';
    elif (event_type == 'file_save'):
        # if it is a file/jpg file_save event, just exit
        sys.exit()

    if (event_type == 'movie_save'):
        movie_save()
