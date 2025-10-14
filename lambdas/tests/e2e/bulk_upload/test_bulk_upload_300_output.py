from services.base.dynamo_service import DynamoDBService
from tests.e2e.conftest import BULK_REPORT_TABLE, LG_METADATA_TABLE, LG_UNSTITCHED_TABLE

dynamo_service = DynamoDBService()


def test_bulk_upload_300_patients_with_3_files():

    # assert bulk upload report table values
    bulk_upload_table = dynamo_service.scan_whole_table(
        BULK_REPORT_TABLE, "Reason, UploadStatus, NhsNumber"
    )
    assert len(bulk_upload_table) == 868

    complete_uploads = []
    failed_uploads = []
    name_mismatch_rejections = []
    dob_mismatch_rejections = []

    for item in bulk_upload_table:
        if item.get("UploadStatus") == "complete":
            complete_uploads.append(item)
        elif item.get("UploadStatus") == "failed":
            failed_uploads.append(item)
            if item.get("Reason") == "Patient name does not match our records":
                name_mismatch_rejections.append(item)
            elif item.get("Reason") == "Patient DoB does not match our records":
                dob_mismatch_rejections.append(item)

    assert len(complete_uploads) == 765
    assert len(failed_uploads) == 103
    assert len(name_mismatch_rejections) == 6
    assert len(dob_mismatch_rejections) == 27

    # assert lloyd george metadata values, this will also validate the files were stitched
    lg_metadata_table = dynamo_service.scan_whole_table(
        LG_METADATA_TABLE, "CurrentGpOds, NhsNumber"
    )
    assert len(lg_metadata_table) == 255

    dece_records = []
    susp_records = []
    rest_records = []

    for item in lg_metadata_table:
        ods_code = item.get("CurrentGpOds")
        if ods_code == "DECE":
            dece_records.append(item)
        elif ods_code == "SUSP":
            susp_records.append(item)
        elif ods_code == "REST":
            rest_records.append(item)

    assert len(dece_records) == 4
    assert len(susp_records) == 4
    assert len(rest_records) == 9

    # assert unstitched metadata contains original unstitched files
    lg_unstitched_metadata_table = dynamo_service.scan_whole_table(
        LG_UNSTITCHED_TABLE, "CurrentGpOds"
    )
    assert len(lg_unstitched_metadata_table) == 765
