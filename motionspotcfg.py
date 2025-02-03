# list ips or hostnames of cameras if controlling the led or settings on them
cameras = {
    'first_camera_name' : {
        # hostname or ip address of camera
        'host' : '192.168.1.58',
        # site information to be attached to the alerts
        'camera_site_name' : 'At Home',
        # classes of objects to be detected for presence
        'detect_presence_classes' : ['cat', 'person'],
        # classes of objects to be detected using count change
        'detect_count_classes' : ['bicycle'],
        # classes of objects to be detected for motion
        'detect_motion_classes' : ['car', 'bus'],
        # turn led spotlight on for this camera when detecting an object
        'control_led' : True,
        # destinations to use when sending detection alerts for this camera
        'active_alerts' : ['user1_telegram'],
    },
}

alerts = {
    'user1_telegram' : {
        # alert type: email, telegream, ntfy
        'alert_type' : 'telegram',
        # resize images before sending - optional
        'alert_image_resize' : 0.2,
        # telegram bot token - have to create this first using BotFather if it doesn't exist
        'alert_telegram_bot_token' : 'telegram_bot_token',
        # get telegram user_id by searching and starting a conversation with the @userinfobot bot
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

# path where Motion saves snapshots - for sending to object detector
img_path = '/var/lib/motion/cctv/images'
# log path - required - path to file or 'stdout'
log_path = '/var/log/motion/motionspot.log'
# log level: e, w, i, d (error, warning, info, debug) - defaults to 'e'
log_level = 'd'
# store pid of detection loop process here
lock_path = '/var/lib/motion/locks'
# load yolo model from here - best to download it and save it before running the script
yolo_model = '/etc/motion/yolov8s.pt' 
