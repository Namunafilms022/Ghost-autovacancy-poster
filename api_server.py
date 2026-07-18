from __future__ import annotations

import logging
import sys
import time
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database.init import init_db as _init_db
from ghost_module.pipeline import process_message

logger = logging.getLogger('ghost.api')

app = FastAPI(
    title='Ghost AutoVacancy Poster API',
    version='1.0.0',
    description='Production REST API for processing and publishing job vacancies',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


class ProcessRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000,
                         description='Raw vacancy text to process')
    threshold: float = Field(default=0.7, ge=0.0, le=1.0,
                             description='Extraction confidence threshold')


class StageInfo(BaseModel):
    name: str
    success: bool
    duration: float
    details: Optional[str] = None


class ProcessResponse(BaseModel):
    success: bool
    vacancy_id: Optional[int] = None
    company: str = ''
    position: str = ''
    location: str = ''
    salary: str = ''
    status: str = ''
    is_duplicate: bool = False
    duplicate_score: float = 0.0
    validation_passed: bool = False
    validation_confidence: float = 0.0
    queue_id: Optional[int] = None
    stages: List[StageInfo] = []
    error: Optional[str] = None
    duration: float = 0.0


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: float


_start_time = time.time()


@app.get('/health', response_model=HealthResponse, tags=['System'])
def health():
    return HealthResponse(
        status='ok',
        version='1.0.0',
        uptime=time.time() - _start_time,
    )


@app.post('/api/process', response_model=ProcessResponse,
          status_code=200, tags=['Pipeline'],
          summary='Process a raw vacancy message',
          description='Extract, validate, generate poster and caption, enqueue for publishing')
def process(req: ProcessRequest):
    t0 = time.time()
    try:
        mr = process_message(req.message, 0, threshold=req.threshold)
        dur = time.time() - t0

        status = 'SKIPPED' if mr.skipped else ('FAILED' if mr.error else 'COMPLETED')

        return ProcessResponse(
            success=not mr.skipped and not mr.error,
            vacancy_id=mr.vacancy_id,
            company=mr.company,
            position=mr.position,
            location=mr.location,
            salary=mr.salary,
            status=status,
            is_duplicate=mr.is_duplicate,
            duplicate_score=mr.duplicate_score,
            validation_passed=mr.validation_passed,
            validation_confidence=mr.validation_confidence,
            queue_id=int(mr.ready_package_path) if mr.ready_package_path else None,
            stages=[StageInfo(
                name=s.name, success=s.success,
                duration=round(s.duration, 3),
                details=s.details,
            ) for s in mr.stages],
            error=mr.error,
            duration=round(dur, 3),
        )
    except Exception as e:
        logger.exception('Process request failed')
        raise HTTPException(status_code=500, detail=str(e))


def run_api(host: str = '0.0.0.0', port: int = 8000):
    _init_db()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    )
    logger.info(f'API server starting at http://{host}:{port}')
    uvicorn.run(app, host=host, port=port, log_level='info')
