"""
Pytest configuration and fixtures for testing.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_job_details():
    """Fixture providing sample job details for testing."""
    from parser import JobDetails
    
    return JobDetails(
        title='Senior Python Developer',
        company='Tech Company Inc.',
        description='We are looking for an experienced Python developer...',
        location='San Francisco, CA',
        salary_min=120000,
        salary_max=180000,
        job_type='Full-time',
        experience_level='Senior',
        requirements=['Python', 'Django', '5+ years experience'],
        benefits=['Health Insurance', '401k', 'Remote'],
    )


@pytest.fixture
def sample_raw_message():
    """Fixture providing sample raw vacancy message."""
    return """
    We are hiring a Senior Python Developer!
    
    Company: Tech Company Inc.
    Location: San Francisco, CA
    Salary: $120k - $180k
    Job Type: Full-time
    
    Requirements:
    - 5+ years of Python experience
    - Django expertise
    - Strong problem-solving skills
    
    Benefits:
    - Health Insurance
    - 401k matching
    - Remote work option
    
    Contact: careers@techcompany.com
    """
