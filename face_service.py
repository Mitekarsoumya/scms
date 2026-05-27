from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class RecognizedFace:
    student_id: int
    name: str
    confidence: float


class FaceRecognitionService:
    """Small OpenCV-based recognizer used by the attendance camera stream.

    If opencv-contrib is installed, LBPH is used. Otherwise the service falls
    back to comparing normalized face templates, which keeps the project easy
    to run and easy to explain.
    """

    def __init__(self):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(cascade_path)
        self.known_faces = []
        self.lbph_model = None
        self.label_to_student = {}
        self.use_lbph = hasattr(cv2, "face")

    def load_known_faces(self, students):
        templates = []
        labels = []
        self.label_to_student = {}

        for label, (student_id, name, image_path) in enumerate(students, start=1):
            face = self.extract_face_from_image(image_path)
            if face is None:
                continue
            templates.append((student_id, name, face))
            labels.append(label)
            self.label_to_student[label] = (student_id, name)

        self.known_faces = templates
        if self.use_lbph and templates:
            self.lbph_model = cv2.face.LBPHFaceRecognizer_create()
            faces = [item[2] for item in templates]
            self.lbph_model.train(faces, np.array(labels))
        else:
            self.lbph_model = None

    def extract_face_from_image(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            return None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
        if len(faces) == 0:
            return self.prepare_face(gray)
        x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
        return self.prepare_face(gray[y : y + h, x : x + w])

    def prepare_face(self, gray_face):
        resized = cv2.resize(gray_face, (160, 160))
        return cv2.equalizeHist(resized)

    def recognize_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
        recognized = []

        for x, y, w, h in faces:
            prepared_face = self.prepare_face(gray[y : y + h, x : x + w])
            match = self.match_face(prepared_face)
            color = (0, 128, 255)
            label = "Unknown"

            if match:
                recognized.append(match)
                color = (34, 197, 94)
                label = f"{match.name} ({match.confidence:.0f}%)"

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                frame,
                label,
                (x, max(30, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )

        return recognized, frame

    def match_face(self, prepared_face):
        if not self.known_faces:
            return None

        if self.lbph_model is not None:
            label, distance = self.lbph_model.predict(prepared_face)
            if distance <= 78:
                student_id, name = self.label_to_student[label]
                confidence = max(0, 100 - distance)
                return RecognizedFace(student_id, name, confidence)
            return None

        best_student = None
        best_score = float("inf")
        for student_id, name, known_face in self.known_faces:
            score = np.mean((prepared_face.astype("float") - known_face.astype("float")) ** 2)
            if score < best_score:
                best_score = score
                best_student = (student_id, name)

        if best_student and best_score < 2600:
            confidence = max(0, 100 - (best_score / 35))
            return RecognizedFace(best_student[0], best_student[1], confidence)
        return None

    def frame_response(self, frame):
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            return self.placeholder_response("Frame encoding failed")
        return b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"

    def placeholder_response(self, message):
        frame = np.full((480, 720, 3), 245, dtype=np.uint8)
        cv2.putText(
            frame,
            message,
            (40, 230),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (37, 99, 235),
            2,
        )
        return self.frame_response(frame)
