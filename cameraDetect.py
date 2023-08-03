import cv2

def find_camera_index():
    index = 0
    while True:
        cap = cv2.VideoCapture(index)
        if not cap.read()[0]:
            break
        cap.release()
        index += 1
    return index

camera_index = find_camera_index()
print("Индекс веб-камеры:", camera_index)
