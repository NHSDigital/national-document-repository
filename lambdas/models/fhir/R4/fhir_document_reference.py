from typing import Any, Dict, List, Literal, Optional

from enums.snomed_codes import SnomedCode, SnomedCodes
from models.document_reference import DocumentReference as NdrDocumentReference
from models.fhir.R4.base_models import (
    CodeableConcept,
    Coding,
    Extension,
    Meta,
    Period,
    Reference,
)
from pydantic import BaseModel, Field

# Constants
FHIR_BASE_URL = "https://fhir.nhs.uk/Id"
SNOMED_URL = "http://snomed.info/sct"
NRL_FORMAT_CODE_SYSTEM = "https://fhir.nhs.uk/England/CodeSystem/England-NRLFormatCode"
NRL_CONTENT_STABILITY_SYSTEM = (
    "https://fhir.nhs.uk/England/CodeSystem/England-NRLContentStability"
)
CONTENT_STABILITY_URL = (
    "https://fhir.nhs.uk/England/StructureDefinition/Extension-England-ContentStability"
)


class FormatCode(Coding):
    """Coding for specifying document format type."""

    system: Optional[str] = None
    code: Literal["urn:nhs-ic:record-contact", "urn:nhs-ic:unstructured"] = (
        "urn:nhs-ic:unstructured"
    )
    display: Literal["Contact details (HTTP Unsecured)", "Unstructured Document"] = (
        "Unstructured Document"
    )


class Attachment(BaseModel):
    """Represents a document attachment in FHIR."""

    contentType: str = "application/pdf"
    language: str = "en-GB"
    url: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None
    title: Optional[str] = None
    creation: Optional[str] = None
    data: Optional[bytes] = None


class ContentStabilityExtensionCoding(Coding):
    """Coding for content stability extension."""

    system: Literal[NRL_CONTENT_STABILITY_SYSTEM] = NRL_CONTENT_STABILITY_SYSTEM
    code: Literal["static", "dynamic"] = "static"
    display: Literal["Static", "Dynamic"] = "Static"


class ContentStabilityExtensionValueCodeableConcept(CodeableConcept):
    """CodeableConcept for content stability."""

    coding: List[ContentStabilityExtensionCoding] = Field(
        default_factory=lambda: [ContentStabilityExtensionCoding()]
    )


class ContentStabilityExtension(Extension):
    """Extension for content stability in NHS FHIR profiles."""

    url: Literal[CONTENT_STABILITY_URL] = CONTENT_STABILITY_URL
    valueCodeableConcept: ContentStabilityExtensionValueCodeableConcept = Field(
        default_factory=ContentStabilityExtensionValueCodeableConcept
    )


class DocumentReferenceContent(BaseModel):
    """Content section of a DocumentReference resource."""

    attachment: Attachment
    format: Optional[FormatCode] = None
    extension: Optional[List[ContentStabilityExtension]] = None


class DocumentReferenceContext(BaseModel):
    """Context information for a DocumentReference."""

    encounter: Optional[List[Reference]] = None
    event: Optional[List[CodeableConcept]] = None
    period: Optional[Period] = None
    facilityType: Optional[CodeableConcept] = None
    practiceSetting: CodeableConcept
    sourcePatientInfo: Optional[Reference] = None
    related: Optional[List[Reference]] = None


class DocumentReference(BaseModel):
    """FHIR DocumentReference resource."""

    id: Optional[str] = None
    resourceType: Literal["DocumentReference"]
    docStatus: Literal[
        "registered",
        "partial",
        "preliminary",
        "final",
        "amended",
        "corrected",
        "appended",
        "cancelled",
        "entered-in-error",
        "deprecated",
        "unknown",
    ] = "final"
    status: Literal["current", "superseded", "entered-in-error"] = "current"
    type: Optional[CodeableConcept]
    category: Optional[List[CodeableConcept]] = None
    subject: Optional[Reference]
    date: Optional[str] = None
    author: Optional[List[Reference]]
    authenticator: Optional[Reference] = None
    custodian: Optional[Reference] = None
    content: List[DocumentReferenceContent]
    context: Optional[DocumentReferenceContext] = None
    meta: Optional[Meta] = None


class DocumentReferenceInfo(BaseModel):
    """Information needed to create a DocumentReference resource."""

    nhs_number: str
    custodian: Optional[str] = None
    snomed_code_doc_type: SnomedCode = SnomedCodes.LLOYD_GEORGE.value
    snomed_code_category: SnomedCode = SnomedCodes.CARE_PLAN.value
    snomed_code_practice_setting: SnomedCode = (
        SnomedCodes.GENERAL_MEDICAL_PRACTICE.value
    )
    attachment: Attachment = Field(default_factory=Attachment)
    author: Optional[str] = None

    def _create_identifier(self, system_suffix: str, value: str) -> Dict[str, Any]:
        """Helper method to create FHIR identifiers.

        Args:
            system_suffix: The suffix to append to FHIR_BASE_URL
            value: The identifier value

        Returns:
            Dictionary representing a FHIR identifier
        """
        return {
            "identifier": {
                "system": f"{FHIR_BASE_URL}/{system_suffix}",
                "value": value,
            }
        }

    def _create_snomed_coding(self, snomed_code: SnomedCode) -> List[Dict[str, str]]:
        """Helper method to create SNOMED CT codings.

        Args:
            snomed_code: The SNOMED code object

        Returns:
            List of dictionaries representing FHIR codings
        """
        return [
            {
                "system": SNOMED_URL,
                "code": snomed_code.code,
                "display": snomed_code.display_name,
            }
        ]

    def create_nrl_fhir_document_reference_object(self) -> DocumentReference:
        """Create a fully populated FHIR DocumentReference for the NHS NRL.

        Returns:
            DocumentReference: A FHIR DocumentReference resource
        """
        if not self.custodian:
            raise ValueError("Custodian is required for NRL document references")

        nrl_format_code = FormatCode(system=NRL_FORMAT_CODE_SYSTEM)
        nrl_content_stability_extension = [ContentStabilityExtension()]

        fhir_document_ref = DocumentReference(
            resourceType="DocumentReference",
            subject=Reference(**self._create_identifier("nhs-number", self.nhs_number)),
            content=[DocumentReferenceContent(attachment=self.attachment)],
            custodian=Reference(
                **self._create_identifier("ods-organization-code", self.custodian)
            ),
            type=CodeableConcept(
                coding=self._create_snomed_coding(self.snomed_code_doc_type)
            ),
            category=[
                CodeableConcept(
                    coding=self._create_snomed_coding(self.snomed_code_category)
                )
            ],
            author=[
                Reference(
                    **self._create_identifier("ods-organization-code", self.custodian)
                )
            ],
            context=DocumentReferenceContext(
                practiceSetting=CodeableConcept(
                    coding=self._create_snomed_coding(self.snomed_code_practice_setting)
                )
            ),
        )

        # Add NRL-specific format and extension
        fhir_document_ref.content[0].format = nrl_format_code
        fhir_document_ref.content[0].extension = nrl_content_stability_extension

        return fhir_document_ref

    def create_fhir_document_reference_object(
        self, document: NdrDocumentReference
    ) -> DocumentReference:
        """Create a FHIR DocumentReference .

        Returns:
            DocumentReference: A FHIR DocumentReference resource
        """

        return DocumentReference(
            resourceType="DocumentReference",
            id=f"{self.snomed_code_doc_type.code}~{document.id}",
            docStatus=document.doc_status,
            type=CodeableConcept(
                coding=self._create_snomed_coding(self.snomed_code_doc_type)
            ),
            subject=Reference(**self._create_identifier("nhs-number", self.nhs_number)),
            content=[DocumentReferenceContent(attachment=self.attachment)],
            date=document.created,
            author=[
                Reference(
                    **self._create_identifier(
                        "ods-organization-code", document.author or self.custodian
                    )
                )
            ],
            custodian=Reference(
                **self._create_identifier(
                    "ods-organization-code", document.custodian or self.custodian
                )
            ),
            meta=Meta(versionId = document.version)
        )

    def create_fhir_document_reference_object_basic(self, original_id: str) -> DocumentReference:
        return DocumentReference(
            resourceType="DocumentReference",
            id=f"{self.snomed_code_doc_type.code}~{original_id}",
            type=CodeableConcept(
                coding=self._create_snomed_coding(self.snomed_code_doc_type)
            ),
            subject=Reference(**self._create_identifier("nhs-number", self.nhs_number)),
            content=[DocumentReferenceContent(attachment=self.attachment)],
            author=[
                Reference(
                    **self._create_identifier(
                        "ods-organization-code", self.author or self.custodian
                    )
                )
            ],
        )