#include "esp_camera.h"
#include <WiFi.h> // We need this just to turn it off!

#define BUZZER_PIN 14 

// --- CAMERA PINS (30-Pin WROOM) ---
#define PWDN_GPIO_NUM     13 
#define RESET_GPIO_NUM    15 
#define XCLK_GPIO_NUM     21
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35 
#define Y8_GPIO_NUM       34 
#define Y7_GPIO_NUM       32 
#define Y6_GPIO_NUM       33 
#define Y5_GPIO_NUM       19 
#define Y4_GPIO_NUM       18 
#define Y3_GPIO_NUM       5  
#define Y2_GPIO_NUM       4  
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void setup() {
  Serial.begin(115200); 
  pinMode(BUZZER_PIN, OUTPUT);
  
  // --- NEW: MAXIMUM POWER SAVING ---
  // Physically cut power to the antennas so the camera has enough electricity
  WiFi.mode(WIFI_OFF);
  btStop();
  delay(1000); 
  
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM; config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM; config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM; config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM; config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM; config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM; config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM; config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM; config.pin_reset = RESET_GPIO_NUM;
  
  config.xclk_freq_hz = 20000000; 
  config.pixel_format = PIXFORMAT_YUV422; 
  config.frame_size = FRAMESIZE_QQVGA; 
  config.jpeg_quality = 12;               
  config.fb_count = 1;
  config.fb_location = CAMERA_FB_IN_DRAM; 

  if (esp_camera_init(&config) != ESP_OK) {
    tone(BUZZER_PIN, 500, 1000); // Fail beep
    return;
  }
  
  // --- NEW: THE DUMMY FRAME ---
  // Grab a garbage frame to "warm up" the sensor and stabilize the voltage
  camera_fb_t * fb = esp_camera_fb_get();
  if (fb) {
    esp_camera_fb_return(fb); 
  }

  // Happy beep! Ready for Python.
  tone(BUZZER_PIN, 2000, 150); 
  delay(200);
  tone(BUZZER_PIN, 2000, 150);
}

void loop() {
  if (Serial.available() > 0) {
    
    // Clear the buffer
    while(Serial.available()) { Serial.read(); }
    
    // Short Beep: "I heard Python!"
    tone(BUZZER_PIN, 1000, 50); 
    
    // --- NEW: THE 3-STRIKE RETRY LOOP ---
    // If the power dips, try again immediately up to 3 times
    camera_fb_t * fb = NULL;
    for(int i = 0; i < 3; i++) {
      fb = esp_camera_fb_get();
      if (fb) break; // If it worked, break out of the loop!
      delay(100);    // Wait 100ms for power to recover and try again
    }
    
    if (!fb) {
      // If it failed 3 times in a row, play the sad beep
      tone(BUZZER_PIN, 500, 1000); 
      return; 
    }

    // Success! Send the header and the image data
    Serial.print("IMG_START");
    Serial.write(fb->buf, fb->len);
    esp_camera_fb_return(fb);

    // High Happy Beep: "Image sent successfully!"
    tone(BUZZER_PIN, 3000, 100); 
  }
}
