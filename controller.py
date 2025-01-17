# created by Hussain most of the code is from
# https://www.pyimagesearch.com/2020/05/04/covid-19-face-mask-detector-with-opencv-keras-tensorflow-and-deep-learning
# / and has been adapted to our needs
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
import numpy as np
from imutils.video import VideoStream
import imutils
import time
import cv2
import os
from PIL import Image
from PIL import ImageTk

# This confidence is used as threshold for face detection
confidence = 0.50

# load our serialized face detector model from disk
print("[INFO] loading face detector model...")
prototxtPath = os.path.sep.join(["face_detector", "deploy.prototxt"])
weightsPath = os.path.sep.join(["face_detector",
                                "res10_300x300_ssd_iter_140000.caffemodel"])
net = cv2.dnn.readNet(prototxtPath, weightsPath)


# This method takes image or frame and the desired size of the returns images It prepares the image/frame for face
# detection and then perform it using FaceNet which returns a list of faces with their confidence and location
# which get pre-process to be classified

def process_image_frame(image_frame, model_size=(224, 224)):
    # load the input image from disk, clone it, and grab the image spatial
    # dimensions
    if type(image_frame) == str:
        image = cv2.imread(image_frame)
    else:
        image = image_frame
    orig = image.copy()
    (h, w) = image.shape[:2]
    # construct a blob from the image
    blob = cv2.dnn.blobFromImage(image, 1.0, (300, 300),
                                 (104.0, 177.0, 123.0))
    # pass the blob through the network and obtain the face detections
    print("[INFO] computing face detections...")
    net.setInput(blob)
    detections = net.forward()
    faces = []
    # loop over the detections
    for i in range(0, detections.shape[2]):
        # extract the confidence (i.e., probability) associated with
        # the detection
        face_confidence = detections[0, 0, i, 2]
        # filter out weak detections by ensuring the confidence is
        # greater than the minimum confidence
        if face_confidence > confidence:
            # compute the (x, y)-coordinates of the bounding box for
            # the object
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            # ensure the bounding boxes fall within the dimensions of
            # the frame
            (startX, startY) = (max(0, startX - 10), max(0, startY - 10))
            (endX, endY) = (min(w - 1, endX + 10), min(h - 1, endY + 10))
            # extract the face ROI, convert it from BGR to RGB channel
            # ordering, resize it to 224x224, and preprocess it
            face = image[startY:endY, startX:endX]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, model_size)
            face = img_to_array(face)
            face = preprocess_input(face)
            face = np.expand_dims(face, axis=0)
            faces.append([face, (startX, startY, endX, endY)])

    return faces


# This method takes the original image/frame, faces which will come from process_image_frame method, and the model
# for detecting masks It returns the image/frame after applying the classifier and counter of how many people wear
# mask and how many are not It processes all faces in an image/frame and classify whether a face wears a mask or not
def detect_mask_and_apply_modification_on(image_frame, faces, model):
    # determine the class label and color we'll use to draw
    # the bounding box and text
    count_mask = 0
    count_none_mask = 0
    for face in faces:
        # pass the face through the model to determine if the face
        # has a mask or not
        result = model.predict(face[0])
        withoutMask = result[0][0]
        mask = result[0][1]

        label = "Mask" if mask > withoutMask else "No Mask"
        if mask > withoutMask:
            count_mask = count_mask + 1
        else:
            count_none_mask = count_none_mask + 1
        color = (0, 255, 0) if label == "Mask" else (0, 0, 255)
        # include the probability in the label
        label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)
        # display the label and bounding box rectangle on the output
        # frame
        (startX, startY, endX, endY) = face[1]
        cv2.putText(image_frame, label, (startX, startY - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
        cv2.rectangle(image_frame, (startX, startY), (endX, endY), color, 2)
        # show the output image
    return image_frame, count_mask, count_none_mask


# It runs a video stream and processes each frame using process_image_frame and detect_mask_and_apply_modification_on
# and display the result in the stream
def video_detection(model, model_size=(224, 224)):
    wearing = 0
    notWearing = 0
    print("[INFO] starting video stream...")
    vs = VideoStream(src=0).start()
    time.sleep(2.0)
    # loop over the frames from the video stream
    while True:
        # grab the frame from the threaded video stream and resize it
        # to have a maximum width of 400 pixels
        try:
            frame = vs.read()
            if np.all(frame == None) or np.shape(frame) == () or np.asscalar(np.sum(frame.reshape(-1))) == 0:
                continue
            frame = imutils.resize(frame, width=500)
            image = cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB)
            image = Image.fromarray(image)
            image = ImageTk.PhotoImage(image)
            # detect faces in the frame and determine if they are wearing a
            # face mask or not
            faces = process_image_frame(frame, model_size)
            frame, count_mask, count_none_mask = detect_mask_and_apply_modification_on(frame, faces, model)
            wearing = count_mask
            notWearing = count_none_mask
            detected_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            detected_image = Image.fromarray(detected_image)
            detected_image = ImageTk.PhotoImage(detected_image)
            # show the output frame
            cv2.putText(frame, "Press esc to exit", (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255))
            cv2.imshow("Live Video in Progress, Press esc to Exit", frame)
            key = cv2.waitKey(1) & 0xFF
            # if the `q` key was pressed, break from the loop
            if key == ord("q"):
                break
            if key == 27:
                break
        except:
            pass
    cv2.destroyAllWindows()
    vs.stop()
    return image, detected_image, wearing, notWearing
