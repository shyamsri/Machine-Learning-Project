"""
Application for Age and Gender Estimation
"""
import cv2
import os
import pafy
from time import sleep
import numpy as np
import argparse
import csv
import tkinter as tk
from wide_resnet import WideResNet
from keras.utils.data_utils import get_file
import PySimpleGUI as sg

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

class FaceCV(object):
    
    _vAR_config = ConfigParser()
    _vAR_config.read('test.ini')
    _vAR_CASE_PATH = _vAR_config.get('section_a', '_vAR_CASE_PATH')
    _vAR_WRN_WEIGHTS_PATH = _vAR_config.get('section_a', '_vAR_WRN_WEIGHTS_PATH')
     

    
    def __new__(cls, weight_file=None, depth=16, width=8, face_size=64):
        if not hasattr(cls, 'instance'):
            cls.instance = super(FaceCV, cls).__new__(cls)
        return cls.instance

    def __init__(self, depth=16, width=8, face_size=64):
        self.face_size = face_size
        self.model = WideResNet(face_size, depth=depth, k=width)()
        
        _vAR_fpath = self._vAR_WRN_WEIGHTS_PATH
        self.model.load_weights(_vAR_fpath)

    
    def draw_label(cls, image, point, label, font=cv2.FONT_HERSHEY_COMPLEX ,
                   font_scale=1, thickness=2):
        size = cv2.getTextSize(label, font, font_scale, thickness)[0]
        x, y = point
        cv2.rectangle(image, (x, y - size[1]), (x + size[0], y), (0, 0, 0), cv2.FILLED)
        cv2.putText(image, label, point, font, font_scale, (255, 255, 255), thickness)

    def crop_face(self, imgarray, section, margin=40, size=64):
        
        img_h, img_w, _ = imgarray.shape
        if section is None:
            section = [0, 0, img_w, img_h]
        (x, y, w, h) = section
        margin = int(min(w,h) * margin / 100)
        x_a = x - margin
        y_a = y - margin
        x_b = x + w + margin
        y_b = y + h + margin
        if x_a < 0:
            x_b = min(x_b - x_a, img_w-1)
            x_a = 0
        if y_a < 0:
            y_b = min(y_b - y_a, img_h-1)
            y_a = 0
        if x_b > img_w:
            x_a = max(x_a - (x_b - img_w), 0)
            x_b = img_w
        if y_b > img_h:
            y_a = max(y_a - (y_b - img_h), 0)
            y_b = img_h
        cropped = imgarray[y_a: y_b, x_a: x_b]
        resized_img = cv2.resize(cropped, (size, size), interpolation=cv2.INTER_AREA)
        resized_img = np.array(resized_img)
        return resized_img, (x_a, y_a, x_b - x_a, y_b - y_a)

    def detect_face(self):
        face_cascade = cv2.CascadeClassifier(self._vAR_CASE_PATH)

        #url = 'https://www.youtube.com/watch?v=ktKTPiOld1g'
        
        form = sg.FlexForm('Demo Chooser')

        layout = [ [sg.Text('Enter youtube link or 0 for webcam'), sg.InputText()], [sg.OK()] ]
           
        button, value = form.Layout(layout).Read()
        print(value[0])
        if value[0] == '0':
            video_capture = cv2.VideoCapture(0)
        else:
            url = value[0]
            vPafy = pafy.new(value[0])
            play = vPafy.getbest(preftype="mp4")
            video_capture = cv2.VideoCapture(play.url)
            
        # infinite loop, break by key ESC
        while True:
            if not video_capture.isOpened():
                sleep(5)
            # Capture each frame
            ret, frame = video_capture.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=10,
                minSize=(self.face_size, self.face_size)
            )
            
            face_imgs = np.empty((len(faces), self.face_size, self.face_size, 3))
            for i, face in enumerate(faces):
                face_img, cropped = self.crop_face(frame, face, margin=40, size=self.face_size)
                (x, y, w, h) = cropped
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
                face_imgs[i,:,:,:] = face_img
            if len(face_imgs) > 0:
                # age and gender model integration
                results = self.model.predict(face_imgs)
                predicted_genders = results[0]
                ages = np.arange(0, 101).reshape(101, 1)
                predicted_ages = results[1].dot(ages).flatten()
            
            for i, face in enumerate(faces):
                label = "{}, {}".format(int(predicted_ages[i]),
                                        "F" if predicted_genders[i][0] > 0.5 else "M")
                self.draw_label(frame, (face[0], face[1]), label)
                
            with open('csv_output.csv', 'a', newline='') as file1:
                  
                  writer = csv.writer(file1)
                  
                  for i, face in enumerate(faces):
                    
                    writer.writerow([int(predicted_ages[i]), "F" if predicted_genders[i][0] > 0.5 else "M"])

            cv2.imshow('Keras Faces', frame)
            if cv2.waitKey(5) == 27:  # ESC key press
                break
        
        video_capture.release()
        cv2.destroyAllWindows()    


def get_args():
    parser = argparse.ArgumentParser(description="This script detects faces from web cam input, "
                                                 "and estimates age and gender for the detected faces.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--depth", type=int, default=16,
                        help="depth of network")
    parser.add_argument("--width", type=int, default=8,
                        help="width of network")
    args = parser.parse_args()
    return args

def main():
    
    args = get_args()
    depth = args.depth
    width = args.width
    
    face = FaceCV(depth=depth, width=width)

    face.detect_face()

if __name__ == '__main__':
    main()
