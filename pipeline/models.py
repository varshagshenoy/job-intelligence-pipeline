
from pydantic import BaseModel, Field
from typing import Optional


class EvidenceItem(BaseModel):
    field_name: str
    snippet: str


class JobExtraction(BaseModel):
    is_relevant: bool = Field(
        description="Whether this is a Data, ML, Analytics, or Platform engineering role"
    )

    is_us_role: Optional[bool] = Field(
        default=None,
        description="True if the job is based in the US or explicitly offers US-remote work. False if explicitly outside the US. Null if unclear."
    )

    company: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None

    work_mode: Optional[str] = Field(
        default=None,
        description="Remote, Hybrid, On-site, or null if not stated"
    )

    employment_type: Optional[str] = None

    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None

    experience_years_min: Optional[float] = None
    experience_years_max: Optional[float] = None

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)

    description_summary: Optional[str] = None

    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Exact snippets supporting extracted fields"
    )
