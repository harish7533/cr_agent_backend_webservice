<<<<<<< HEAD
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread

from job_store import create_job, get_job
from automation import run_automation

app = FastAPI()

# Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 START AUTOMATION
@app.post("/start")
async def start_job(data: dict):
    job_id = create_job()

    # Run automation in background
    thread = Thread(target=run_automation, args=(job_id, data))
    thread.start()

    return {"job_id": job_id}

# 📊 GET STATUS
@app.get("/status/{job_id}")
async def get_status(job_id: str):
=======
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread

from backend.job_store import create_job, get_job
from backend.automation import run_automation

app = FastAPI()

# Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 START AUTOMATION
@app.post("/start")
async def start_job(data: dict):
    job_id = create_job()

    # Run automation in background
    thread = Thread(target=run_automation, args=(job_id, data))
    thread.start()

    return {"job_id": job_id}

# 📊 GET STATUS
@app.get("/status/{job_id}")
async def get_status(job_id: str):
>>>>>>> 0126ba55be4ed45c80e3526250e8f756142baddd
    return get_job(job_id)