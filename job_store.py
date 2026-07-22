<<<<<<< HEAD
import uuid

jobs = {}

def create_job():
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "started",
        "progress": 0,
        "message": "Job initiated"
    }
    return job_id

def update_job(job_id, data):
    if job_id in jobs:
        jobs[job_id].update(data)

def get_job(job_id):
=======
import uuid

jobs = {}

def create_job():
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "started",
        "progress": 0,
        "message": "Job initiated"
    }
    return job_id

def update_job(job_id, data):
    if job_id in jobs:
        jobs[job_id].update(data)

def get_job(job_id):
>>>>>>> 0126ba55be4ed45c80e3526250e8f756142baddd
    return jobs.get(job_id, {"error": "Job not found"})