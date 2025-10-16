import { Details } from 'nhsuk-react-components';
import { useState } from 'react';
import { GenericDocument } from '../../../types/generic/genericDocument';

interface Props {
    documentsList: Array<GenericDocument>;
    ariaLabel: string;
}

const DocumentsListView = ({ documentsList, ariaLabel }: Props): React.JSX.Element => {
    const [isExpanded, setIsExpanded] = useState(true);

    return (
        <Details open>
            <Details.Summary
                aria-label={ariaLabel}
                data-testid={ariaLabel}
                onClick={(): void => setIsExpanded(!isExpanded)}
            >
                {isExpanded ? 'Hide files' : 'View files'}
            </Details.Summary>
            <Details.Text>
                <ul className="document-list-view-list">
                    {documentsList?.map((document) => {
                        return (
                            <li
                                key={document.id}
                                data-ref={document.ref}
                                data-testid={document.fileName.split('_')[0]}
                            >
                                {document.fileName}
                            </li>
                        );
                    })}
                </ul>
            </Details.Text>
        </Details>
    );
};

export default DocumentsListView;
