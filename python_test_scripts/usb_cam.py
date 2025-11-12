import cv2
import os
print("Starting the script")
gstreamer_pipeline = (
    'v4l2src device=/dev/video0 ! '
    'image/jpeg, width=1280, height=960, framerate=100/1 ! '
    'jpegdec ! '
    'videoconvert ! '
    'appsink'
)

folder_path = "imgs_test_delete_later"
os.makedirs(folder_path, exist_ok=True)  # Ensure folder exists

cap = cv2.VideoCapture('/dev/video0')
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

i = 0
while True:
    ret, frame = cap.read()
    
    if not ret:
        print("Error: Could not read frame.")
        break

    print(frame.shape)
    
    frame_path = os.path.join(folder_path, f"images.png")
    if i%500 == 0: 
        cv2.imwrite(frame_path, frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    i += 1
    break

cap.release()
cv2.destroyAllWindows()
