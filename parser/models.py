from pydantic import BaseModel
from typing import Optional, List


class JobDetails(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    requirements: List[str] = []
    benefits: List[str] = []
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    raw_message: Optional[str] = None
