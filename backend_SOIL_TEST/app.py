from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.get("/home")
def home():
    return {"message": "Hello World!"}