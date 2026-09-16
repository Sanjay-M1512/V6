import cv2
import time
import os


def capture_live_face(
    camera_index=0,
    duration=5,
    output_path="outputs/faces/live_face.jpg"
):
    """
    Capture a live face from the webcam for a few seconds.

    The largest detected face is selected.

    Returns:
        {
            "success": True/False,
            "face_image": path,
            "message": ...
        }
    """

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        "haarcascade_frontalface_default.xml"
    )

    camera = cv2.VideoCapture(camera_index)

    if not camera.isOpened():
        return {
            "success": False,
            "face_image": None,
            "message": "Could not open camera."
        }

    start_time = time.time()
    best_face = None
    best_area = 0

    while True:

        ret, frame = camera.read()

        if not ret:
            continue

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        gray = cv2.equalizeHist(gray)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        # Find largest face
        for x, y, w, h in faces:

            area = w * h

            if area > best_area:

                best_area = area

                margin_x = int(w * 0.20)
                margin_y = int(h * 0.20)

                x1 = max(
                    0,
                    x - margin_x
                )

                y1 = max(
                    0,
                    y - margin_y
                )

                x2 = min(
                    frame.shape[1],
                    x + w + margin_x
                )

                y2 = min(
                    frame.shape[0],
                    y + h + margin_y
                )

                best_face = frame[
                    y1:y2,
                    x1:x2
                ].copy()

        # Display camera window
        display_frame = frame.copy()

        for x, y, w, h in faces:

            cv2.rectangle(
                display_frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

        remaining = duration - (
            time.time() - start_time
        )

        if remaining > 0:

            text = (
                f"Look at camera - "
                f"{remaining:.1f}s"
            )

        else:

            text = "Capture complete"

        cv2.putText(
            display_frame,
            text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.imshow(
            "TRUST-ID Live Verification",
            display_frame
        )

        # Stop after duration
        if time.time() - start_time >= duration:
            break

        # ESC key
        if cv2.waitKey(1) & 0xFF == 27:
            break

    camera.release()
    cv2.destroyAllWindows()

    if best_face is None:

        return {
            "success": False,
            "face_image": None,
            "message": (
                "No face detected. "
                "Please try again."
            )
        }

    # Normalize face
    best_face = cv2.resize(
        best_face,
        (112, 112),
        interpolation=cv2.INTER_AREA
    )

    # Create output directory
    directory = os.path.dirname(
        output_path
    )

    if directory:
        os.makedirs(
            directory,
            exist_ok=True
        )

    cv2.imwrite(
        output_path,
        best_face
    )

    return {
        "success": True,
        "face_image": output_path,
        "message": "Live face captured successfully."
    }