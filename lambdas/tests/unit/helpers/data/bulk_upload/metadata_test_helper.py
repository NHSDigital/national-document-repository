import os
from models.staging_metadata import MetadataFile, SqsMetadata

def convert_metadata_file_to_sqs_metadata(metadata_file: MetadataFile) -> SqsMetadata:
    return SqsMetadata(
        file_path=metadata_file.file_path,
        nhs_number=metadata_file.nhs_number,
        gp_practice_code=metadata_file.gp_practice_code,
        scan_date=metadata_file.scan_date,
        stored_file_name=os.path.basename(metadata_file.file_path),
    )