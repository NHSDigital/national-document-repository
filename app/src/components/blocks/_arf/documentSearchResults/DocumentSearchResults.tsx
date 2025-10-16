import { Table } from 'nhsuk-react-components';
import { SearchResult } from '../../../../types/generic/searchResult';
import { getFormattedDatetime } from '../../../../helpers/utils/formatDatetime';

type Props = {
    searchResults: Array<SearchResult>;
};

const DocumentSearchResults = (props: Props): React.JSX.Element => {
    const sortMethod = (a: SearchResult, b: SearchResult): number =>
        new Date(a.created) < new Date(b.created) ? 1 : -1;

    const orderedResults = [...props.searchResults].sort(sortMethod);
    const tableCaption = (
        <h2 className="document-search-table-caption">List of documents available</h2>
    );

    return (
        <Table id="available-files-table-title" caption={tableCaption}>
            <Table.Head>
                <Table.Row>
                    <Table.Cell className={'table-column-header'}>Filename</Table.Cell>
                    <Table.Cell className={'table-column-header'}>Uploaded At</Table.Cell>
                </Table.Row>
            </Table.Head>
            <Table.Body>
                {orderedResults.map((result, index) => (
                    <Table.Row
                        className={'available-files-row'}
                        id={'available-files-row-' + index}
                        key={`document-${result.fileName + result.created}`}
                        data-testid="search-result"
                    >
                        <Table.Cell
                            id={'available-files-row-' + index + '-filename'}
                            data-testid="filename"
                        >
                            {result.fileName}
                        </Table.Cell>
                        <Table.Cell
                            id={'available-files-row-' + index + '-created-date'}
                            data-testid="created"
                        >
                            {getFormattedDatetime(new Date(result.created))}
                        </Table.Cell>
                    </Table.Row>
                ))}
            </Table.Body>
        </Table>
    );
};

export default DocumentSearchResults;
