# backend/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload, questions, tags

app = FastAPI(title="Error Book API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(questions.router, prefix="/questions", tags=["questions"])
app.include_router(tags.router, prefix="/tags", tags=["tags"])
