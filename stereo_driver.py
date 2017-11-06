from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image

logging = False


def logger(*data):
    if (logging):
        print(data)


class splitter_node:
    def onMsg(self, data):
        logger("frame")
        bridge = CvBridge()
        try:
            cv_image = bridge.imgmsg_to_cv2(data, 'bgr8')
        except CvBridgeError as e:
            logger(e)

        height, width, channels = cv_image.shape
        crop_l = cv_image[0:height, 0:(width / 2)]
        crop_r = cv_image[0:height, (width / 2):width]
        logger("crop_l: " + str(crop_l.shape))

        logger(height, width, channels)

        image_messagel = bridge.cv2_to_imgmsg(crop_l, "bgr8")
        image_messager = bridge.cv2_to_imgmsg(crop_r, "bgr8")
        logger(image_messagel.width)
        logger(image_messager.width)
        self.lpub.publish(image_messagel)
        self.rpub.publish(image_messager)

    def listener(self):
        rospy.Subscriber("/cv_camera/image_raw", Image, self.onMsg)
        self.lpub = rospy.Publisher("/camera/left/image_raw", Image, queue_size=1)
        self.rpub = rospy.Publisher("/camera/right/image_raw", Image, queue_size=1)
        print rospy.get_published_topics()
        try:
            rospy.spin()
        except KeyboardInterrupt:
            logger("goodbye")


import sys
import yaml

from sensor_msgs.msg import CameraInfo
from sensor_msgs.srv import SetCameraInfo, SetCameraInfoRequest, SetCameraInfoResponse
import rospy
import rospy.service


class CameraInfoServiceImpl:
    def handle_info_req(self, req):
        print("got req " + str(req.camera_info))
        self.data = req.camera_info
        self.infopub = CameraInfoPublisher('camera/' + self.name, self.data)
        return {"success":True}

    def __init__(self, name):
        self.infopub = None
        self.name = name
        self.data = CameraInfo()
        self.s = rospy.Service("/camera/" + name + "/set_camera_info", SetCameraInfo, self.handle_info_req)


class CameraInfoPublisher:
    # Callback of the ROS subscriber.

    def callback(self, data):
        cam_info_org = data
        self.cam_info.header = cam_info_org.header
        self.publish()

    def __init__(self, camera_name, camera_data=None):
        if camera_data is None:
            file_name = '/mnt/core/scratch/datasets/calib/vitr-stereo/' + camera_name + '/ost.yaml'
            self.cam_info = parse_yaml(file_name)
        else:
            self.cam_info = camera_data

        self.left_cam_info_org = 0
        self.right_cam_info_org = 0

        topic = "/" + camera_name + "/camera_info"
        rospy.Subscriber(camera_name + "/camera_info", CameraInfo, self.callback)

        self.pub = rospy.Publisher(topic, CameraInfo)

    def publish(self):
        '''
        now = rospy.Time.now()
        self.left_cam_info.header.stamp = now
        self.right_cam_info.header.stamp = now
        '''
        self.pub.publish(self.cam_info)


def parse_yaml(filename):
    stream = file(filename, 'r')
    calib_data = yaml.load(stream)
    cam_info = CameraInfo()
    cam_info.width = calib_data['image_width']
    cam_info.height = calib_data['image_height']
    cam_info.K = calib_data['camera_matrix']['data']
    cam_info.D = calib_data['distortion_coefficients']['data']
    cam_info.R = calib_data['rectification_matrix']['data']
    cam_info.P = calib_data['projection_matrix']['data']
    cam_info.distortion_model = calib_data['distortion_model']

    return cam_info


if __name__ == '__main__':
    rospy.init_node('stereo_driver')
    # lpublisher = CameraInfoPublisher('camera/left')
    # rpublisher = CameraInfoPublisher('camera/right')
    lsvc = CameraInfoServiceImpl("left")
    rsvc = CameraInfoServiceImpl("right")
    s = splitter_node()
    s.listener()
    while not rospy.is_shutdown():
        rospy.sleep(rospy.Duration(.1))
