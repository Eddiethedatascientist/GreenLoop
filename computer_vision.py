#Libraries for processing image
#Model used
from ultralytics import YOLO
import cv2
import time
from math import sqrt
import serial
#Add 2 parameters a call_back function to send signal to database and a signal for the CV to stop
def run_vision(on_detection, stop_event):
    model = YOLO(r"runs/detect/train-8/weights/best.pt")
    #Establish serial communication with embedded system through pyserial
    try: 
        ser = serial.Serial(
            port='COM5',
            baudrate=115200,
            timeout=1
        )
        time.sleep(2)
        print("Connected to ESP 32 through COM5")
    except Exception as e:
        print(f"Cannot establish serial connection because of error {e}")
        ser = None

    #Computer Webcam
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    print("Computer Vision camera turned on!")
    count_image = 0
    last_roi_frame = None
    #Constant and variable to set up the stopping time for the machine
    WAITING_TIME = 5.0
    last_detect_time = 0
    try:
        while cap.isOpened() and not stop_event.is_set():
            ret, frame = cap.read()
            if ret == False:
                break
            else:
                count_image += 1
                current_time = time.time()
                h, w, _ = frame.shape
                RATIO_W = 0.6
                SIDE_CHANGE = sqrt(RATIO_W)
                h_roi = int(h * SIDE_CHANGE)
                w_roi = int(w * SIDE_CHANGE)
                y_min = int((h - h_roi) / 2)
                y_max = y_min + h_roi
                x_min = int((w - w_roi) / 2)
                x_max = x_min + w_roi
                display_frame = frame.copy()
                #ROI drawn on the display frame
                cv2.rectangle(display_frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                #Check if machine is in Cooling state
                is_cooling_mode = (current_time - last_detect_time) < WAITING_TIME
                #Machine operates when it's not in cooling mode
                if (count_image % 15 == 0) and (is_cooling_mode is False):
                    roi = frame[y_min:y_max, x_min:x_max]
                    result = model(roi)
                    annotated_roi = result[0].plot()
                    last_roi_frame = annotated_roi
                    display_frame[y_min:y_max, x_min:x_max] = annotated_roi
                    detected_object = False
                    for r in result:
                        for box in r.boxes:
                            class_id = int(box.cls[0])
                            class_name = model.names[class_id]
                            cf_level = float(box.conf[0])
                            if cf_level >= 0.6:
                                print(f"Detect the {class_name} object, class ID: {class_id} with confidence level {cf_level}")
                                #Packaged and send to the embedded system
                                if ser is not None and ser.is_open:
                                    message = class_name + "\n"
                                    ser.write(message.encode('utf-8'))
                                    ser.flush()
                                    print("Command sent to ESP 32. Look for action in the embedded system")
                                    time.sleep(3)
                                    print("Completed")
                                on_detection(class_name)
                                #Detected object = set new time
                                detected_object = True
                                #End the loop instantly
                                break
                    if detected_object is True:
                        last_detect_time = current_time
                        print(f"[STATE] Detect trash! YOLO enter cooling mode for {WAITING_TIME} seconds")
                if last_roi_frame is not None:
                    display_frame[y_min:y_max, x_min:x_max] = last_roi_frame
                cv2.imshow("GreenLoop Camera test", display_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        #Close serial port only once instead of inside loop -> port will never be opened
        if ser is not None and ser.is_open:
            ser.close()
            print("Close port COM5")
        cv2.destroyAllWindows()