import cv2
import mediapipe as mp
from collections import deque
import time


class HeadScrollController:
    def __init__(self, zoom_callback=None, scroll_callback=None, camera_index=0):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Fix: properly initialize the camera capture
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.NOSE_TIP = 1
        self.FOREHEAD = 10
        self.CHIN = 152
        self.LEFT_EYE = 33
        self.RIGHT_EYE = 263

        self.deadzone = 0.02
        self.zoom_sensitivity = 0.1
        self.scroll_sensitivity = 15
        self.smoothing_factor = 0.3
        self.smoothed_z = 0
        self.smoothed_x = 0

        self.z_history = deque(maxlen=5)
        self.x_history = deque(maxlen=5)

        self.calibration_mode = True
        self.calibration_frames = 0
        self.max_calibration_frames = 60
        self.neutral_z = 0
        self.neutral_x = 0

        self.zoom_active = False
        self.scroll_active = False
        self.current_zoom_direction = 0
        self.current_scroll_direction = 0

        self.zoom_callback = zoom_callback
        self.scroll_callback = scroll_callback

        self.last_zoom_time = time.time()
        self.last_scroll_time = time.time()
        self.action_cooldown = 0.05

    def get_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        lean_z = 0
        turn_x = 0

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                lean_z = self.calculate_z_lean(face_landmarks)
                turn_x = self.calculate_x_turn(face_landmarks)

                if self.calibration_mode:
                    self.neutral_z += lean_z
                    self.neutral_x += turn_x
                    self.calibration_frames += 1
                    if self.calibration_frames >= self.max_calibration_frames:
                        self.neutral_z /= self.max_calibration_frames
                        self.neutral_x /= self.max_calibration_frames
                        self.calibration_mode = False
                        print("Calibration complete!")
                else:
                    raw_z = lean_z - self.neutral_z
                    raw_x = turn_x - self.neutral_x

                    if abs(raw_z) < self.deadzone:
                        raw_z = 0
                    if abs(raw_x) < self.deadzone:
                        raw_x = 0

                    smoothed_z = self.smooth_value_z(raw_z)
                    smoothed_x = self.smooth_value_x(raw_x)

                    self.process_zoom(smoothed_z)
                    self.process_scroll(smoothed_x)

                h, w = frame.shape[:2]
                nose = face_landmarks.landmark[self.NOSE_TIP]
                left_eye = face_landmarks.landmark[self.LEFT_EYE]
                right_eye = face_landmarks.landmark[self.RIGHT_EYE]

                cv2.circle(frame, (int(nose.x * w), int(nose.y * h)), 6, (0, 255, 0), -1)
                cv2.circle(frame, (int(left_eye.x * w), int(left_eye.y * h)), 4, (255, 0, 0), -1)
                cv2.circle(frame, (int(right_eye.x * w), int(right_eye.y * h)), 4, (255, 0, 0), -1)

        self.draw_feedback(frame, lean_z, turn_x)
        return frame

    def calculate_z_lean(self, landmarks):
        nose = landmarks.landmark[self.NOSE_TIP]
        forehead = landmarks.landmark[self.FOREHEAD]
        chin = landmarks.landmark[self.CHIN]
        face_height = chin.y - forehead.y
        nose_ratio = (nose.y - forehead.y) / face_height if face_height > 0 else 0.5
        return (nose_ratio - 0.5) * 2

    def calculate_x_turn(self, landmarks):
        nose = landmarks.landmark[self.NOSE_TIP]
        left_eye = landmarks.landmark[self.LEFT_EYE]
        right_eye = landmarks.landmark[self.RIGHT_EYE]
        face_width = abs(right_eye.x - left_eye.x)
        face_center_x = (left_eye.x + right_eye.x) / 2
        nose_offset = (nose.x - face_center_x) / face_width if face_width > 0 else 0
        return nose_offset * 2

    def smooth_value_z(self, new_z):
        self.z_history.append(new_z)
        avg_z = sum(self.z_history) / len(self.z_history)
        self.smoothed_z = self.smoothing_factor * avg_z + (1 - self.smoothing_factor) * self.smoothed_z
        return self.smoothed_z

    def smooth_value_x(self, new_x):
        self.x_history.append(new_x)
        avg_x = sum(self.x_history) / len(self.x_history)
        self.smoothed_x = self.smoothing_factor * avg_x + (1 - self.smoothing_factor) * self.smoothed_x
        return self.smoothed_x

    def process_zoom(self, z_value):
        current_time = time.time()
        if current_time - self.last_zoom_time < self.action_cooldown:
            return
        zoom_amount = abs(z_value) * self.zoom_sensitivity
        if zoom_amount > 0.01:
            if z_value > 0 and self.zoom_callback:
                self.zoom_callback(1.05)
                self.zoom_active = True
                self.current_zoom_direction = 1
                self.last_zoom_time = current_time
            elif z_value < 0 and self.zoom_callback:
                self.zoom_callback(0.95)
                self.zoom_active = True
                self.current_zoom_direction = -1
                self.last_zoom_time = current_time
            else:
                self.zoom_active = False
                self.current_zoom_direction = 0
        else:
            self.zoom_active = False
            self.current_zoom_direction = 0

    def process_scroll(self, x_value):
        current_time = time.time()
        if current_time - self.last_scroll_time < self.action_cooldown:
            return
        scroll_amount = int(abs(x_value) * self.scroll_sensitivity)
        if scroll_amount > 1:
            if x_value > 0 and self.scroll_callback:
                # Fix: scroll_callback expects (delta_x, delta_y) — head turns scroll horizontally
                self.scroll_callback(1, 0)
                self.scroll_active = True
                self.current_scroll_direction = 1
                self.last_scroll_time = current_time
            elif x_value < 0 and self.scroll_callback:
                self.scroll_callback(-1, 0)
                self.scroll_active = True
                self.current_scroll_direction = -1
                self.last_scroll_time = current_time
            else:
                self.scroll_active = False
                self.current_scroll_direction = 0
        else:
            self.scroll_active = False
            self.current_scroll_direction = 0

    def draw_feedback(self, frame, lean_z, turn_x):
        h, w = frame.shape[:2]
        if self.calibration_mode:
            cv2.putText(frame, f"CALIBRATING... {self.calibration_frames}/{self.max_calibration_frames}",
                        (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        if self.zoom_active:
            if self.current_zoom_direction > 0:
                zoom_status = "ZOOM IN"
                zoom_color = (0, 255, 0)
                cv2.arrowedLine(frame, (w // 2, h - 50), (w // 2, h - 100), zoom_color, 3)
            else:
                zoom_status = "ZOOM OUT"
                zoom_color = (0, 0, 255)
                cv2.arrowedLine(frame, (w // 2, h - 100), (w // 2, h - 50), zoom_color, 3)
        else:
            zoom_status = "ZOOM NEUTRAL"
            zoom_color = (255, 255, 255)

        if self.scroll_active:
            if self.current_scroll_direction > 0:
                scroll_status = "SCROLL RIGHT"
                scroll_color = (0, 255, 255)
                cv2.arrowedLine(frame, (w - 100, h // 2), (w - 50, h // 2), scroll_color, 3)
            else:
                scroll_status = "SCROLL LEFT"
                scroll_color = (255, 255, 0)
                cv2.arrowedLine(frame, (50, h // 2), (100, h // 2), scroll_color, 3)
        else:
            scroll_status = "SCROLL NEUTRAL"
            scroll_color = (255, 255, 255)

        cv2.putText(frame, zoom_status, (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, zoom_color, 2)
        cv2.putText(frame, scroll_status, (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, scroll_color, 2)
        cv2.putText(frame, f"Lean: {int(lean_z * 100)}%", (20, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Turn: {int(turn_x * 100)}%", (20, 160),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.line(frame, (w // 2 - 30, h // 2), (w // 2 + 30, h // 2), (100, 100, 100), 1)
        cv2.line(frame, (w // 2, h // 2 - 30), (w // 2, h // 2 + 30), (100, 100, 100), 1)

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None
