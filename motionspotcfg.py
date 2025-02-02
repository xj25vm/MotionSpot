# list ips or hostnames of cameras if controlling the led or settings on them
cameras = {
    'front_door' : {
        'host' : 'first_camera_host_name_or_ip',
        # site information to be attached to the alerts
        'camera_site_name' : 'At Home',
        # classes of objects to be detected for presence
        'detect_presence_classes' : ['cat', 'person'],
        # classes of objects to be detected using count change
        'detect_count_classes' : ['bicycle'],
        # classes of objects to be detected for motion
        'detect_motion_classes' : ['car', 'bus'],
        # per camera settings
        'control_led' : True,
        'active_alerts' : ['user1_telegram'],
    },
}

alerts = {
    'user1_telegram' : {
        # alert type: email, telegream, ntfy
        'alert_type' : 'telegram',

        # resize images before sending - optional
        'alert_image_resize' : 0.2,
        # details for sending telegram alerts
        'alert_telegram_bot_token' : 'long_telegram_bot_token',
        # get telegram user_id by starting by searching and starting a conversation with the @userinfobot bot
        'alert_telegram_user_id' : 'telegram_id_of_recipient',
    },

    # an example of an email alert
    'user1_email' : {
        'alert_type' : 'email',
        'alert_image_resize' : 0.2,
        'alert_smtp_host' : '127.0.0.1',
        'alert_smtp_username' : 'server@mydomain.tld',
        'alert_smtp_password' : 'very_secure_password',
        'alert_smtp_port' : '465',
        'alert_email_recipient' : 'admin@mydomain.tld',
        'alert_email_sender' : 'server@mydomain.tld',
    },
}

# credentials to send led and config commands to cameras
camera_username = 'admin'
camera_password = 'very_secure_password'

# path where Motioneye saves snapshots - for sending to object detector
img_path = '/var/lib/motioneye/cctv/images'
# log path - required - path to file or 'stdout'
log_path = '/var/log/motioneye/motionspot.log'
# log level: e, w, i, d (error, warning, info, debug) - defaults to 'e'
log_level = 'd'
# store pid of detection loop process here
lock_path = '/var/lib/motioneye/locks'
yolo_model = '/etc/motioneye/yolov8s.pt' 
