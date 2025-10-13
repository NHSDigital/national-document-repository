import os
from collections import defaultdict
from datetime import date

from models.staging_metadata import NHS_NUMBER_FIELD_NAME
from services.bulk_upload_metadata_preprocessor_service import (
    MetadataPreprocessorService,
)
from utils.audit_logging_setup import LoggingService
from utils.exceptions import InvalidFileNameException
from utils.filename_utils import (
    assemble_lg_valid_file_name_full_path,
    extract_date_from_bulk_upload_file_name,
    extract_document_number_bulk_upload_file_name,
    extract_document_path,
    extract_nhs_number_from_bulk_upload_file_name,
    extract_patient_name_from_bulk_upload_file_name,
)

logger = LoggingService(__name__)


class MetadataUsbPreprocessorService(MetadataPreprocessorService):
    def __init__(self, practice_directory: str):
        super().__init__(practice_directory)
        self.nhs_number_counts = defaultdict(int)

    def generate_renaming_map(self, metadata_rows: list[dict]):
        valid_metadata_rows = []
        rejected_rows = []
        rejected_reasons = []

        for row in metadata_rows:
            file_name = row.get("FILEPATH", "N/A")
            try:
                nhs_number = row.get(NHS_NUMBER_FIELD_NAME, "N/A")
                self._validate_file_extension(file_name)
                self._count_files_for_patient(nhs_number)
                valid_metadata_rows.append(row)

            except InvalidFileNameException as error:
                rejected_rows.append(row)
                rejected_reasons.append({"FILEPATH": file_name, "REASON": str(error)})

        renaming_map, super_rejected_rows, super_rejected_reasons = (
            super().generate_renaming_map(valid_metadata_rows)
        )

        rejected_rows.extend(super_rejected_rows)
        rejected_reasons.extend(super_rejected_reasons)

        return renaming_map, rejected_rows, rejected_reasons

    def validate_record_filename(
        self, file_path, metadata_nhs_number=None, *args, **kwargs
    ) -> str:
        self._validate_single_file_for_patient(metadata_nhs_number)
        directory_path, file_name = extract_document_path(file_path)

        self._validate_document_parts(file_path, file_name)

        self._validate_file_extension(file_name)

        (
            nhs_number,
            patient_name,
            date_of_birth,
        ) = self._extract_metadata_from_path(directory_path)

        if nhs_number != metadata_nhs_number:
            logger.warning(
                f"File as it does not match the metadata NHS number: {file_path}"
            )

        return assemble_lg_valid_file_name_full_path(
            file_path_prefix=directory_path + "/",
            first_document_number=1,
            second_document_number=1,
            patient_name=patient_name,
            nhs_number=nhs_number,
            date_object=date_of_birth,
            file_extension=".pdf",
        )

    def _count_files_for_patient(self, nhs_number):
        self.nhs_number_counts[nhs_number] += 1

    def _validate_single_file_for_patient(self, nhs_number):
        if self.nhs_number_counts[nhs_number] > 1:
            raise InvalidFileNameException(
                f"More than one file is found for {nhs_number}"
            )

    def _validate_file_extension(self, file_name: str) -> str:
        file_extension = os.path.splitext(file_name)[1]
        if file_extension != ".pdf":
            logger.info("Rejecting file as it is not a PDF")
            raise InvalidFileNameException(
                f"File extension {file_extension} is not supported"
            )
        return file_extension

    def _validate_document_parts(self, file_path: str, file_name: str):
        try:
            numbers = extract_document_number_bulk_upload_file_name(file_name)
        except InvalidFileNameException:
            numbers = None

        if numbers:
            first_document_number, total_document_number, _ = numbers
            if first_document_number != 1 or total_document_number != 1:
                logger.info(
                    f"Rejecting file as it is part of a multi-part document: {file_path}"
                )
                raise InvalidFileNameException("Multi-part documents are not supported")

    def _extract_metadata_from_path(self, directory_path: str) -> tuple[str, str, date]:
        nhs_number, remaining_path = extract_nhs_number_from_bulk_upload_file_name(
            directory_path
        )
        patient_name, remaining_path = extract_patient_name_from_bulk_upload_file_name(
            remaining_path
        )
        date_of_birth, _ = extract_date_from_bulk_upload_file_name(remaining_path)
        return nhs_number, patient_name, date_of_birth
