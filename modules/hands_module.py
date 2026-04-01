import cv2
import mediapipe as mp
import numpy as np
from math import hypot


class HandsController:

    def __init__(self, scroll_callback=None, zoom_callback=None, camera_index=0):
        # Fix: properly initialize the camera capture
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            max_num_hands=2
        )
        self.mpDraw = mp.solutions.drawing_utils

        self.scroll_callback = scroll_callback
        self.zoom_callback = zoom_callback

        self.scroll_sensitivity = 30
        self.dead_zone = 20

        self.center_x = 320
        self.center_y = 240

        self.min_pinch = 25
        self.max_pinch = 120
        self.last_pinch_dist = None

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        self.center_x = w // 2
        self.center_y = h // 2

        imgRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(imgRGB)

        lmDict_right = {}
        lmDict_left = {}

        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmark, hand_handedness in zip(
                results.multi_hand_landmarks,
                results.multi_handedness
            ):
                label = hand_handedness.classification[0].label
                lmDict = {}
                for id, lm in enumerate(hand_landmark.landmark):
                    lmDict[id] = (int(lm.x * w), int(lm.y * h))

                if label == "Right":
                    lmDict_right = lmDict
                else:
                    lmDict_left = lmDict

                self.mpDraw.draw_landmarks(
                    frame,
                    hand_landmark,
                    self.mpHands.HAND_CONNECTIONS
                )

        # LEFT HAND → SCROLL (passes delta_x=0, delta_y as scroll)
        if 8 in lmDict_left and self.scroll_callback:
            x, y = lmDict_left[8]
            dx = self.center_x - x
            dy = self.center_y - y

            if abs(dx) < self.dead_zone:
                dx = 0
            if abs(dy) < self.dead_zone:
                dy = 0

            delta_x = dx / self.scroll_sensitivity
            delta_y = dy / self.scroll_sensitivity
            # Fix: scroll_callback expects (delta_x, delta_y)
            self.scroll_callback(delta_x, delta_y)

            cv2.putText(frame, "SCROLL ACTIVE", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)

        # RIGHT HAND → ZOOM
        if 4 in lmDict_right and 8 in lmDict_right and self.zoom_callback:
            dist = hypot(
                lmDict_right[4][0] - lmDict_right[8][0],
                lmDict_right[4][1] - lmDict_right[8][1]
            )

            if self.last_pinch_dist is not None:
                diff = dist - self.last_pinch_dist
                if abs(diff) > 2:
                    zoom_factor = 1 + (diff / 200)
                    zoom_factor = max(0.95, min(1.05, zoom_factor))
                    self.zoom_callback(zoom_factor)

            self.last_pinch_dist = dist
            cv2.putText(frame, "ZOOM ACTIVE", (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        else:
            self.last_pinch_dist = None

        # UI overlay
        cv2.line(frame, (self.center_x, 0), (self.center_x, h), (50, 50, 50), 1)
        cv2.line(frame, (0, self.center_y), (w, self.center_y), (50, 50, 50), 1)
        cv2.putText(frame, "H.A.N.D.S ACTIVE", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return frame

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.hands is not None:
            self.hands.close()
            self.hands = None
