from typing import List, Optional

from pydantic import BaseModel, Field


class Coding(BaseModel):
    system: Optional[str] = "http://hl7.org/fhir/issue-type"
    code: Optional[str] = None
    display: Optional[str] = None


class CodeableConcept(BaseModel):
    coding: Optional[List[Coding]] = None


class Extension(BaseModel):
    valueCodeableConcept: Optional[CodeableConcept] = None
    url: Optional[str] = None


class Period(BaseModel):
    id: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None


class Identifier(BaseModel):
    use: Optional[str] = None
    type: Optional[CodeableConcept] = None
    system: Optional[str] = None
    value: Optional[str] = None
    period: Optional[Period] = None


class Reference(BaseModel):
    reference: Optional[str] = None
    type: Optional[str] = None
    identifier: Optional[Identifier] = None
    display: Optional[str] = None


class Link(BaseModel):
    relation: str = Field(..., alias="relation")
    url: str


class Meta(BaseModel):
    security: Optional[List[Coding]] = None
    tag: Optional[List[Coding]] = None
    versionId: Optional[str] = None
