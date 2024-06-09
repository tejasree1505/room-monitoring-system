import socket
import json
from ultralytics import YOLO
import cv2
import pathlib
import xml.etree.ElementTree as ET
import math
from ultralytics.utils.plotting import Annotator

def extract_bounding_boxes(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    bounding_boxes = []
    for obj in root.findall('object'):
        ref_name = obj.find("name").text
        bbox = obj.find('bndbox')
        xmin = int(bbox.find('xmin').text)
        ymin = int(bbox.find('ymin').text)
        xmax = int(bbox.find('xmax').text)
        ymax = int(bbox.find('ymax').text)

        center_x = (xmin + xmax) / 2
        center_y = (ymin + ymax) / 2

        bounding_boxes.append({
            # 'xmin': xmin,   # left
            # 'ymin': ymin,   # bottom
            # 'xmax': xmax,   # right
            # 'ymax': ymax,   # top
            "name": ref_name,
            'center_x': center_x,
            'center_y': center_y
        })

    return bounding_boxes       # list of dictionaries of form: {name:"", x: "", y: ""}

def find_closest_ref(refs, objs):
    closest = dict()
    for obj in objs:
        dist = 9999
        for ref in refs:
            now = math.dist([ref["center_x"], ref["center_y"]], [obj["obj_x"], obj["obj_y"]])
            if(now<dist):
                dist = now
                fin = ref['name']
        closest[obj["name"]] = fin
    return closest

def find_object_centers(annotator, objects_array):
    objects = []
    for box in objects_array:
        b = box.xyxy[0]  # get box coordinates in (left, top, right, bottom) format
        c = box.cls
        annotator.box_label(b, model.names[int(c)])
        obj_x = (b[0] + b[2]) / 2   # (xmin + xmax) / 2
        obj_y = (b[3] + b[1]) / 2
        objects.append({
            "name": model.names[int(c)],
            'obj_x': obj_x,
            'obj_y': obj_y
        })
        print(f"obj: {model.names[int(c)]}, obj x: {obj_x}, obj y: {obj_y}")    
    return  objects

# Example usage
xml_path = './reference.xml'
boxes = extract_bounding_boxes(xml_path)

tcp_port = 1672
tcp_ip = '0.0.0.0'
buf_size = 1024

p = pathlib.Path("F:\\test-1\\output.txt")

print("Bounding Boxes Coordinates:")
for box in boxes:
    print(f"OBJ: {box['name']}, Center X: {box['center_x']}, Center Y: {box['center_y']}")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# load Ultralytics YOLOv8 model
model = YOLO('yolov8n.pt')
# '''
# # load video
# video_path = './test.mp4'
cap = cv2.VideoCapture(0)
# '''
# image_path = 'img1.jpg'

# set the desired size of the displayed frame
desired_size = (1366, 768)  # specify the width and height

# get the class names from the model
class_names = model.names

ret = True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

print("[INFO] Creating Socket...")
s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
print("[INFO] Socket successfully created")

s.bind((tcp_ip,tcp_port))
print("[INFO] Socket is binded to port",tcp_port)

s.listen(1)
print("[INFO] Socket is listening")

# =========================================================
n=1
while True:
    c,addr = s.accept()
    print("[INFO] Connection address from",addr)

    
    while True:

        data = c.recv(buf_size)
        msg = json.loads(data.decode())
        objects = msg.get('0')
        if(objects == "quit"):
            break
        print("\nClient asked for: ",objects)
        
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # get the class index for YOLOv8
        class_indices = [k for k, v in class_names.items() if v in objects]

        # read frames
        # while ret:
        ret, frame = cap.read()
        # frame = cv2.imread(image_path)

        if ret:
            # perform object detection and tracking using YOLOv8
            results = model.track(frame, classes=class_indices, persist=True)

            
            annotator = Annotator(frame)
            frame = annotator.result()
            objects = find_object_centers(annotator, results[0].boxes)    # will become list of dict

            closest = find_closest_ref(boxes, objects)
            print(closest)
            
            # show results for the first element in the list
            frame_ = results[0].plot()
            im = frame_
            im0 = frame.copy()

            # resize the frame to the desired size
            frame_resized = cv2.resize(frame_, desired_size)
            
            outed = model.predictor.write_results(0, results, (p, im, im0))

            if("no detections" in outed):
                msg = json.dumps({0:"0", 1: "Requested items were not found!"})
            else:
                output_image_path = "output.jpg"
                cv2.imwrite(output_image_path, frame_resized)
                msg = json.dumps({0:"1",1: closest})

            msgpckt = msg.encode()
            c.send(msgpckt)                 

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            
    c.close()
    break

print("\n[INFO] Disconnecting Socket...")
s.close()
print("[INFO] Socket disconnected successfully")