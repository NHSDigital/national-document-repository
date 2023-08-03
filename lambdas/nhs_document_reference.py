from datetime import datetime


class NHSDocumentReference:
    def __init__(self, reference_id, file_location, data) -> None:
        self.id = reference_id
        self.nhs_number = data["subject"]["identifier"]["value"]
        self.content_type = data["content"][0]["attachment"]["contentType"]
        self.file_name = data["description"]
        self.created = str(datetime.now())
        self.deleted = None
        self.uploaded = None
        self.virus_scanner_result = "Not Scanned"
        self.file_location = file_location

    def set_uploaded(self) -> None:
        self.uploaded = datetime.now()

    def set_deleted(self) -> None:
        self.deleted = datetime.now()

    def set_virus_scanner_result(self, updated_virus_scanner_result) -> None:
        self.virus_scanner_result = updated_virus_scanner_result

    def update_location(self, updated_file_location):
        self.file_location = updated_file_location

    def is_uploaded(self) -> bool:
        return bool(self.uploaded)

    def to_dict(self):
        document_metadata = {
            "ID": str(self.id),
            "NhsNumber": self.nhs_number,
            "FileName": self.file_name,
            "FileLocation": self.file_location,
            "Created": self.created,
            "ContentType": self.content_type,
            "VirusScannerResult": self.virus_scanner_result,
        }
        return document_metadata
