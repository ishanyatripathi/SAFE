# S.A.F.E – Smart Assistive Framework for Examination

## 🧠 Overview

S.A.F.E is a real-time, multi-modal Human-Computer Interaction (HCI) system designed for hands-free navigation of medical reports. It enables intuitive interaction using **hand gestures** and **head movements**, making it ideal for sterile environments, accessibility use-cases, and assistive healthcare applications.

The system integrates **computer vision (MediaPipe)** with a responsive GUI to deliver smooth, contactless control over digital content.

---

## 🚀 Features

### 🔹 Multi-Modal Interaction

* ✋ **H.A.N.D.S Module**

  * Left hand → Scroll (X & Y)
  * Right hand pinch → Zoom in/out

* 👤 **H.E.A.D Module**

  * Head tilt forward/back → Zoom
  * Head turn left/right → Horizontal scroll

---

### 🔹 Real-Time Performance

* Threaded video capture system
* Non-blocking frame queue
* Smooth UI updates (~60 FPS)

---

### 🔹 Smart UI System

* Fullscreen immersive interface
* Boot animation screen
* Module selection dashboard
* Live camera feed with overlays
* Medical report viewer with scroll & zoom

---

### 🔹 Dynamic Module Switching

* Switch between HANDS and HEAD control in real-time
* Safe camera release & reinitialization
* Visual feedback during transitions

---

### 🔹 Report Viewer

* Upload medical images (PNG, JPG, etc.)
* Zoom and scroll using gestures
* Smooth scaling with limits

---

## ⚙️ Tech Stack

* **Python**
* **OpenCV**
* **MediaPipe**
* **Tkinter (GUI)**
* **PIL (Image Processing)**
* **Multithreading & Queue**

---

## 🧩 How It Works

1. Camera captures live video feed
2. MediaPipe processes:

   * Hand landmarks OR
   * Face mesh landmarks
3. Gestures / head movements are detected
4. Converted into:

   * Scroll actions
   * Zoom actions
5. UI updates in real-time

---

## 🖥️ Installation

```bash
git clone https://github.com/ishanyatripathi/SAFE.git
cd SAFE
pip install -r requirements.txt
```

---

## ▶️ Run the Application

```bash
python main.py
```

---

## 🎮 Controls Summary

| Module    | Action | Input              |
| --------- | ------ | ------------------ |
| H.A.N.D.S | Scroll | Left hand movement |
| H.A.N.D.S | Zoom   | Right hand pinch   |
| H.E.A.D   | Scroll | Head turn          |
| H.E.A.D   | Zoom   | Head lean          |

---

## 🎯 Use Cases

* 🏥 Medical environments (hands-free report viewing)
* ♿ Assistive technology for physically challenged users
* 🧑‍⚕️ Sterile environments (no touch interaction)
* 💻 Experimental HCI systems

---

## ⚡ Key Highlights

* Real-time gesture recognition system
* Modular and scalable architecture
* Smooth multi-threaded performance
* Practical real-world application

---

## 🔮 Future Improvements

* 🎙️ Voice + Gesture fusion
* 👁️ Eye tracking support
* 🤖 AI-based gesture prediction
* 📄 OCR + medical report analysis
* 🌐 Web / cross-platform UI

---

## 📌 Project Status

✅ Functional Prototype
🚧 Actively Improving

---

## 👨‍💻 Author

**Ishanya Tripathi**
Electronics & Telecommunication Engineering
Lokmanya Tilak College of Engineering

---

## ⭐ Acknowledgements

* MediaPipe by Google
* OpenCV Community
* Python Open Source Ecosystem

---

## 📜 License

This project is open-source and available under the MIT License.
