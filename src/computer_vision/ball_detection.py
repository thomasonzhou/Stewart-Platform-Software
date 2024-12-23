from computer_vision.transforms import scale_pixels_to_centimeters, camera_view_to_plate_view
import cv2
import numpy as np

QUEUE_SIZE = 7


class BallDetector:
    def __init__(self, camera_index=0, preview=False, memory=False):
        self.cap = cv2.VideoCapture(camera_index)
        self.RES_WIDTH = 480
        self.RES_HEIGHT = 480
        self.WINDOW_NAME = "Ball Detection"
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.RES_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.RES_HEIGHT)
        self.preview = preview
        self.memory = memory
        if self.memory:
            self.last_ball_position = (0.0, 0.0)

        # self.moving_avg_queue = deque()
        # total = [0.0, 0.0]
        # for _ in range(QUEUE_SIZE):
        #     ball_pos = self._get_ball_position_top_view()
        #     self.moving_avg_queue.append(ball_pos)
        #     total[0] += ball_pos[0]
        #     total[1] += ball_pos[1]
        # self.moving_avg = [total[0] / QUEUE_SIZE, total[1] / QUEUE_SIZE]

    def _get_frame(self):
        ret = None
        while ret is None:
            ret, frame = self.cap.read()
        return frame

    def _get_circle_coord_in_pixels(self, preview=False):
        frame = self._get_frame()
        frame_height, frame_width = frame.shape[:2]
        center_x = frame_width // 2
        center_y = frame_height // 2

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,  # Inverse ratio of the accumulator resolution to image resolution
            minDist=50,  # Minimum distance between detected centers
            param1=102,  # Higher threshold for Canny
            param2=25,  # Accumulator threshold for circle detection
            minRadius=40,  # Minimum radius of circles
            maxRadius=80,  # Maximum radius of circles
        )

        if circles is not None:
            circles = np.uint16(np.around(circles)).astype(np.int32)
            i = circles[0, 0]
            cv2.circle(frame, (i[0], i[1]), i[2], (0, 255, 0), -1, 8, 0)
            cv2.circle(frame, (i[0], i[1]), 2, (0, 0, 255), 3, 8, 0)

            relative_x = center_x - i[0]
            relative_y = center_y - i[1]
            self.last_ball_position = (relative_x, relative_y)
            # print(f"Circle at (x, y) = ({relative_x}, {relative_y}) with radius {i[2]}")
        elif self.memory:
            relative_x, relative_y = self.last_ball_position
        else:
            relative_x, relative_y = 0, 0

        if self.preview:
            cv2.circle(frame, (center_x, center_y), 2, (255, 0, 0), -1)
            cv2.imshow(self.WINDOW_NAME, frame)
            cv2.waitKey(1)

        return relative_x, relative_y

    def _get_ball_position_camera_view(self):
        circle_position_pixels = self._get_circle_coord_in_pixels()
        # print(f"pixels: {list(int(p) for p in circle_position_pixels)}")
        ball_position_centimeters = scale_pixels_to_centimeters(
            circle_position_pixels, self.RES_HEIGHT
        )
        # print(f"cm: {list(float(b) for b in ball_position_centimeters)}")
        return ball_position_centimeters

    def get_ball_position_plate_view(self):
        ball_position_bottom_view = self._get_ball_position_camera_view()
        # print(ball_position_bottom_view)
        ball_position_top_view_cm = camera_view_to_plate_view(ball_position_bottom_view)
        return ball_position_top_view_cm

    def close_stream(self):
        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    ball_detector = BallDetector(preview=True)
    while True:
        ball_detector.get_ball_position_plate_view()
