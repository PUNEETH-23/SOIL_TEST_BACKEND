# 🌱 SOIL_TEST_BACKEND

An IoT-based Soil Intelligence Platform using **ESP32 + FastAPI + Web Dashboard**.
This system enables remote soil testing, analysis, and smart crop recommendations.

---

## 🚀 Features

* 📡 ESP32-based soil data collection
* ⚡ FastAPI backend for processing & APIs
* 🌐 Web dashboard for Farmers & Admin
* 🌱 Soil health analysis & recommendations
* 📊 Admin panel for managing farmers, lands, and tests

---

## 🧱 Project Structure

```
SOIL_TEST_BACKEND/
│
├── backend_SOIL_TEST/
│   └── backend/
│       ├── app.py
│       ├── requirements.txt
│       └── venv/
│
├── frontend/
│   └── index.html
│
└── esp32/
    └── main.ino
```

---

## ⚙️ Backend Setup (FastAPI)

### 1️⃣ Navigate to backend

```
cd backend_SOIL_TEST/backend
```

---

### 2️⃣ Create Virtual Environment

```
python -m venv venv
```

---

### 3️⃣ Activate Virtual Environment

**Windows:**

```
venv\Scripts\activate
```

**Mac/Linux:**

```
source venv/bin/activate
```

---

### 4️⃣ Install Dependencies

```
pip install -r requirements.txt
```

---

### 5️⃣ Run Server

```
uvicorn app:app --reload
```

Backend will run at:

```
http://127.0.0.1:8000
```

---

## 🌐 Frontend Setup

1. Open the `index.html` file
2. Run using **Live Server** (VS Code extension)

Frontend will run at something like:

```
http://127.0.0.1:5500
```

---

## 🔗 Important Configuration

### Enable CORS in FastAPI

Add this in `app.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📡 API Endpoints (Basic)

| Method | Endpoint       | Description         |
| ------ | -------------- | ------------------- |
| GET    | `/`            | Check server status |
| GET    | `/farmer/{id}` | Get farmer data     |
| POST   | `/admin/login` | Admin login         |

> ⚠️ Make sure these endpoints are implemented in `app.py`

---

## 🔌 ESP32 Setup

* Code available in:

```
esp32/main.ino
```

* Upload using Arduino IDE / PlatformIO
* Configure:

  * WiFi credentials
  * Backend API URL

---

## ⚠️ Notes

* Backend must be running before opening frontend
* CORS must be enabled for frontend-backend communication
* Ensure API URLs match (`http://127.0.0.1:8000`)

---

## 🔮 Future Improvements

* 🤖 ML-based crop prediction
* ☁️ Cloud deployment (Render / AWS / HuggingFace)
* 📱 Mobile app integration
* 📊 Advanced analytics dashboard

---

## 👨‍💻 Author

Built as part of an IoT + AI project for smart agriculture 🌾
