import React, { Dispatch, SetStateAction, useState } from 'react';
import { FieldValues, useForm } from 'react-hook-form';
import { Button, Fieldset, Radios, WarningCallout } from 'nhsuk-react-components';
import deleteAllDocuments, {
    DeleteResponse,
} from '../../../../helpers/requests/deleteAllDocuments';
import useBaseAPIHeaders from '../../../../helpers/hooks/useBaseAPIHeaders';
import { DOCUMENT_TYPE } from '../../../../types/pages/UploadDocumentsPage/types';
import { DOWNLOAD_STAGE } from '../../../../types/generic/downloadStage';
import SpinnerButton from '../../../generic/spinnerButton/SpinnerButton';
import ServiceError from '../../../layout/serviceErrorBox/ServiceErrorBox';
import { SUBMISSION_STATE } from '../../../../types/pages/documentSearchResultsPage/types';
import { AxiosError } from 'axios';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { Outlet, Route, Routes, useNavigate } from 'react-router-dom';
import useRole from '../../../../helpers/hooks/useRole';
import { REPOSITORY_ROLE } from '../../../../types/generic/authRole';
import useBaseAPIUrl from '../../../../helpers/hooks/useBaseAPIUrl';
import usePatient from '../../../../helpers/hooks/usePatient';
import { errorToParams } from '../../../../helpers/utils/errorToParams';
import { isMock } from '../../../../helpers/utils/isLocal';
import useConfig from '../../../../helpers/hooks/useConfig';
import useTitle from '../../../../helpers/hooks/useTitle';
import ErrorBox from '../../../layout/errorBox/ErrorBox';
import { getLastURLPath } from '../../../../helpers/utils/urlManipulations';
import DeleteResultStage from '../deleteResultStage/DeleteResultStage';
import BackButton from '../../../generic/backButton/BackButton';
import PatientSummary, { PatientInfo } from '../../../generic/patientSummary/PatientSummary';

export type Props = {
    docType: DOCUMENT_TYPE;
    numberOfFiles: number;
    setDownloadStage?: Dispatch<SetStateAction<DOWNLOAD_STAGE>>;
    recordType: string;
    resetDocState: () => void;
};

enum DELETE_DOCUMENTS_OPTION {
    YES = 'yes',
    NO = 'no',
}

type IndexViewProps = {
    docType: DOCUMENT_TYPE;
    recordType: string;
    resetDocState: () => void;
};

const DeleteSubmitStageIndexView = ({
    docType,
    recordType,
    resetDocState,
}: IndexViewProps): React.JSX.Element => {
    const patientDetails = usePatient();
    const role = useRole();
    const { register, handleSubmit } = useForm();
    const { ref: deleteDocsRef, ...radioProps } = register('deleteDocs');
    const [deletionStage, setDeletionStage] = useState(SUBMISSION_STATE.INITIAL);
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const navigate = useNavigate();
    const config = useConfig();
    const nhsNumber: string = patientDetails?.nhsNumber ?? '';
    const [showNoOptionSelectedMessage, setShowNoOptionSelectedMessage] = useState<boolean>(false);
    const noOptionSelectedError =
        'Select whether you want to permanently delete these patient files';
    const userIsGP = role === REPOSITORY_ROLE.GP_ADMIN || role === REPOSITORY_ROLE.GP_CLINICAL;

    const handleYesOption = async (): Promise<void> => {
        const onSuccess = (): void => {
            resetDocState();
            setDeletionStage(SUBMISSION_STATE.SUCCEEDED);
            if (userIsGP) {
                navigate(routeChildren.LLOYD_GEORGE_DELETE_COMPLETE);
            } else {
                navigate(routeChildren.ARF_DELETE_COMPLETE);
            }
        };
        try {
            setDeletionStage(SUBMISSION_STATE.PENDING);
            const response: DeleteResponse = await deleteAllDocuments({
                docType: docType,
                nhsNumber: nhsNumber,
                baseUrl,
                baseHeaders,
            });

            if (response.status === 200) {
                onSuccess();
            }
        } catch (e) {
            const error = e as AxiosError;
            if (isMock(error) && !!config.mockLocal.recordUploaded) {
                onSuccess();
            } else {
                if (error.response?.status === 403) {
                    navigate(routes.SESSION_EXPIRED);
                } else {
                    navigate(routes.SERVER_ERROR + errorToParams(error));
                }
                setDeletionStage(SUBMISSION_STATE.FAILED);
            }
        }
    };

    const handleNoOption = (): void => {
        if (role === REPOSITORY_ROLE.GP_ADMIN) {
            navigate(routes.LLOYD_GEORGE);
        } else if (role === REPOSITORY_ROLE.PCSE) {
            navigate(routes.ARF_OVERVIEW);
        }
    };

    const submit = async (fieldValues: FieldValues): Promise<void> => {
        const allowedRoles = [REPOSITORY_ROLE.GP_ADMIN, REPOSITORY_ROLE.PCSE];
        if (role && allowedRoles.includes(role)) {
            if (fieldValues.deleteDocs === DELETE_DOCUMENTS_OPTION.YES) {
                await handleYesOption();
            } else if (fieldValues.deleteDocs === DELETE_DOCUMENTS_OPTION.NO) {
                handleNoOption();
            } else {
                setShowNoOptionSelectedMessage(true);
            }
        }
    };

    const pageTitle = `You are removing the ${recordType} record of`;
    useTitle({ pageTitle });

    return (
        <>
            <BackButton
                toLocation={
                    role !== REPOSITORY_ROLE.PCSE ? routes.LLOYD_GEORGE : routes.ARF_OVERVIEW
                }
                backLinkText="Go back"
            />
            {deletionStage === SUBMISSION_STATE.FAILED && <ServiceError />}
            {showNoOptionSelectedMessage && (
                <ErrorBox
                    messageTitle={'There is a problem '}
                    messageLinkBody={'You must select an option'}
                    errorBoxSummaryId={'error-box-summary'}
                    errorInputLink={'#delete-docs'}
                    dataTestId={'delete-error-box'}
                />
            )}
            <form onSubmit={handleSubmit(submit)}>
                <Fieldset id="radio-selection">
                    <Fieldset.Legend isPageHeading>{pageTitle}:</Fieldset.Legend>
                    <PatientSummary showDeceasedTag>
                        <PatientSummary.Child item={PatientInfo.FULL_NAME} />
                        <PatientSummary.Child item={PatientInfo.NHS_NUMBER} />
                        <PatientSummary.Child item={PatientInfo.BIRTH_DATE} />
                    </PatientSummary>

                    {!userIsGP && (
                        <WarningCallout>
                            <WarningCallout.Label>Before removing</WarningCallout.Label>
                            <p data-testid="remove-record-warning-text">
                                Only permanently remove this patient record if you have a valid
                                reason to. For example, you confirmed these files have reached the
                                end of their{' '}
                                <a
                                    href="https://transform.england.nhs.uk/information-governance/guidance/records-management-code/records-management-code-of-practice/#appendix-ii-retention-schedule"
                                    target="_blank"
                                    rel="noreferrer"
                                    aria-label="Retention schedule - this link will open in a new tab"
                                >
                                    retention period
                                </a>
                                .
                            </p>
                        </WarningCallout>
                    )}

                    <p>
                        Once you remove these files, you can not access this record using the
                        service. You may want to keep a copy of the paper record safe.
                    </p>
                    <h2 data-testid="delete-files-warning-message">
                        Are you sure you want to permanently remove this record?
                    </h2>
                    <div>
                        <WarningCallout>
                            <WarningCallout.Label>Important</WarningCallout.Label>
                            <p> This cannot be undone. </p>
                        </WarningCallout>
                    </div>
                    <Radios
                        id="delete-docs"
                        error={showNoOptionSelectedMessage && noOptionSelectedError}
                    >
                        <Radios.Radio
                            value={DELETE_DOCUMENTS_OPTION.YES}
                            inputRef={deleteDocsRef}
                            {...radioProps}
                            id="yes-radio-button"
                            data-testid="yes-radio-btn"
                        >
                            Yes
                        </Radios.Radio>
                        <Radios.Radio
                            value={DELETE_DOCUMENTS_OPTION.NO}
                            inputRef={deleteDocsRef}
                            {...radioProps}
                            id="no-radio-button"
                            data-testid="no-radio-btn"
                        >
                            No
                        </Radios.Radio>
                    </Radios>
                </Fieldset>
                {deletionStage === SUBMISSION_STATE.PENDING ? (
                    <SpinnerButton
                        id="delete-docs-spinner"
                        dataTestId="delete-submit-spinner-btn"
                        status="Deleting..."
                        disabled={true}
                    />
                ) : (
                    <Button type="submit" id="delete-submit-button" data-testid="delete-submit-btn">
                        Continue
                    </Button>
                )}
            </form>
        </>
    );
};

const DeleteSubmitStage = ({
    docType,
    numberOfFiles,
    setDownloadStage,
    recordType,
    resetDocState,
}: Props): React.JSX.Element => {
    const pageTitle = `You are removing the ${recordType} record of:`;
    useTitle({ pageTitle });

    return (
        <>
            <Routes>
                <Route
                    index
                    element={
                        <DeleteSubmitStageIndexView
                            docType={docType}
                            recordType={recordType}
                            resetDocState={resetDocState}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.ARF_DELETE_CONFIRMATION)}
                    element={
                        <DeleteSubmitStage
                            docType={docType}
                            numberOfFiles={numberOfFiles}
                            recordType={recordType}
                            resetDocState={resetDocState}
                        />
                    }
                ></Route>
                <Route
                    path={getLastURLPath(routeChildren.ARF_DELETE_COMPLETE)}
                    element={
                        <DeleteResultStage
                            numberOfFiles={numberOfFiles}
                            setDownloadStage={setDownloadStage}
                        />
                    }
                ></Route>
            </Routes>
            <Outlet />
        </>
    );
};
export default DeleteSubmitStage;
