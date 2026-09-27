import serial
import time
import numpy as np
import cv2
import torch
import open_clip
from PIL import Image
import os

# --- ⚠️ CONFIGURATION ⚠️ ---
ESP32_PORT = "COM7" 
BAUD_RATE = 115200

print("Downloading AI Brain...")
model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
tokenizer = open_clip.get_tokenizer('ViT-B-32')

# We only use text to "diagnose" what went wrong IF the similarity fails
text_prompts = [
    "A perfect printed circuit board",
    "A defective printed circuit board with missing components or holes",
    "A scratched, blurry, or damaged printed circuit board"
]
text_tokens = tokenizer(text_prompts)

# --- 🌟 THE GOLDEN REFERENCE 🌟 ---
golden_img_path = "C:\Work\B.E Electronics and Communication Engineering\3rd Year - Sem 6\Mini Project\Final Execution\Golden_Reference.png"
if not os.path.exists(golden_img_path):
    print(f"\nERROR: '{golden_img_path}' not found!")
    print("Please rename your perfect 'esp32_cable_capture.jpg' to 'Golden_Reference.jpg' and restart.")
    exit()

print("Loading Golden Reference Image...")
ref_img = Image.open(golden_img_path).convert("RGB")
ref_tensor = preprocess(ref_img).unsqueeze(0)

# Calculate the perfect vector once
with torch.no_grad(), torch.cuda.amp.autocast():
    ref_features = model.encode_image(ref_tensor)
    ref_features /= ref_features.norm(dim=-1, keepdim=True)


def capture_and_process(ser):
    print("\nCommanding ESP32 over USB...")
    ser.write(b'S\n\r') 
    ser.flush() 
    
    timeout = time.time() + 8
    header = b""
    while time.time() < timeout:
        if ser.in_waiting:
            header += ser.read(1)
            if b"IMG_START" in header:
                break
    else:
        print("Error: No image header received. Listen to the buzzer!")
        return

    print("Downloading image data (~3 seconds)...")
    expected_bytes = 160 * 120 * 2
    raw_data = bytearray()
    
    while len(raw_data) < expected_bytes:
        if ser.in_waiting:
            raw_data += ser.read(ser.in_waiting)
            
    print("Image received successfully! Processing...")
    
    raw_bytes = np.frombuffer(raw_data[:expected_bytes], dtype=np.uint8)
    img_yuv = raw_bytes.reshape((120, 160, 2))
    img_rgb = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2RGB_YUYV)
    img_rgb = cv2.medianBlur(img_rgb, 3)
    
    cv2.imwrite("live_capture.jpg", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
    print("Saved live capture as 'live_capture.jpg'")

    pil_img = Image.fromarray(img_rgb)
    live_tensor = preprocess(pil_img).unsqueeze(0)

    print("Comparing against Golden Reference...")
    with torch.no_grad(), torch.cuda.amp.autocast():
        # Get live image vector
        live_features = model.encode_image(live_tensor)
        live_features /= live_features.norm(dim=-1, keepdim=True)

        # 1. CALCULATE SIMILARITY (The math between Live and Golden)
        similarity = (live_features @ ref_features.T).item() * 100

        # 2. IF FAILED: Calculate Text Diagnosis 
        text_features = model.encode_text(text_tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        text_probs = (100.0 * live_features @ text_features.T).softmax(dim=-1)

    print("\n" + "="*45)
    print(f"Similarity to Golden Reference: {similarity:.2f}%")
    
    # Threshold for Pass/Fail (Adjust this up or down based on your tests!)
    if similarity >= 85.0:
        print("✅ RESULT: PASS - Board is Good!")
    else:
        print("❌ RESULT: FAIL - Anomaly Detected!")
        
        # Pull the highest probability text prompt for the diagnosis
        best_guess_idx = text_probs[0].argmax().item()
        confidence = text_probs[0][best_guess_idx].item() * 100
        print(f"Diagnosis: {text_prompts[best_guess_idx]} ({confidence:.1f}% Match)")
    print("="*45 + "\n")


if __name__ == "__main__":
    try:
        print(f"Connecting to ESP32 on {ESP32_PORT}...")
        esp32_serial = serial.Serial(ESP32_PORT, BAUD_RATE, timeout=2)
        
        print("Waiting 4 seconds for ESP32 to reboot (Listen for the two startup beeps!)...")
        time.sleep(4) 
        
        print("Connected! System Armed.")
        
        while True:
            user_input = input("Press [ENTER] to inspect a PCB (or type 'q' to quit): ")
            if user_input.lower() == 'q':
                break
            
            esp32_serial.reset_input_buffer() 
            capture_and_process(esp32_serial)
            
    except Exception as e:
        print(f"Failed to connect. Make sure Arduino IDE is closed!")
        print(f"Error: {e}")
    finally:
        if 'esp32_serial' in locals() and esp32_serial.is_open:
            esp32_serial.close()
