import React, { Dispatch, SetStateAction } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { DOWNLOAD_STAGE } from '../../../types/generic/downloadStage';
import ServiceError from '../../layout/serviceErrorBox/ServiceErrorBox';
import { LG_RECORD_STAGE } from '../../../types/blocks/lloydGeorgeStages';
import useRole from '../../../helpers/hooks/useRole';
import { REPOSITORY_ROLE } from '../../../types/generic/authRole';
import { routes } from '../../../types/generic/routes';


function DocumentDownloadError() {
        return (

            <ServiceError message="An error has occurred during download." />
        );

}

export default DocumentDownloadError;
