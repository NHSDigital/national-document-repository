import { Dispatch, SetStateAction, MouseEvent } from 'react';

export type Props = {
    totalPages: number;
    currentPage: number;
    setCurrentPage: Dispatch<SetStateAction<number>>;
};

const Pagination = ({ totalPages, currentPage, setCurrentPage }: Props): React.JSX.Element => {
    if (totalPages === 1) {
        return <></>;
    }

    const updateCurrentPage = (e: MouseEvent<HTMLButtonElement>, page: number): void => {
        e.preventDefault();
        setCurrentPage(page);
    };

    const pageNumber = (page: number | null, index: number): React.JSX.Element => {
        if (page === null) {
            return (
                <li
                    key={`separator-${index}`}
                    data-testid="page-separator"
                    className="govuk-pagination__item govuk-pagination__item--ellipses"
                >
                    ...
                </li>
            );
        }

        const displayPage = `${page + 1}`;

        return (
            <li
                key={page}
                className={`govuk-pagination__item 
                ${page === currentPage ? 'govuk-pagination__item--current' : ''}`}
            >
                <button
                    className="govuk-link govuk-pagination__link"
                    onClick={(e): void => updateCurrentPage(e, page)}
                    aria-label={`Page ${displayPage}`}
                    data-testid={`page-${displayPage}-button`}
                >
                    {displayPage}
                </button>
            </li>
        );
    };

    const firstSection = (): (number | null)[] => {
        const pages = [0];

        if (totalPages <= 7) {
            for (let i = 1; i < totalPages; i++) {
                pages.push(i);
            }
        } else if (currentPage < 3) {
            for (let i = 1; i < 5 && i < totalPages; i++) {
                pages.push(i);
            }
        }

        return pages;
    };

    const middleSection = (): (number | null)[] => {
        const pages = [];

        if (totalPages > 7 && currentPage >= 3 && currentPage < totalPages - 3) {
            pages.push(null, currentPage - 1, currentPage, currentPage + 1);
        }

        return pages;
    };

    const lastSection = (): (number | null)[] => {
        const pages: (number | null)[] = [];

        if (totalPages > 7) {
            if (currentPage < totalPages - 3) {
                pages.push(totalPages - 1);
            } else {
                for (let i = totalPages - 5; i < totalPages; i++) {
                    pages.push(i);
                }
            }
        }

        if (pages.length > 0) {
            pages.splice(0, 0, null);
        }
        return pages;
    };

    const pages = [...firstSection(), ...middleSection(), ...lastSection()];

    return (
        <nav className="govuk-pagination" aria-label="Pagination">
            {currentPage > 0 && (
                <div className="govuk-pagination__prev">
                    <button
                        className="govuk-link govuk-pagination__link"
                        data-testid="previous-page-button"
                        rel="prev"
                        onClick={(e): void => updateCurrentPage(e, currentPage - 1)}
                    >
                        <svg
                            className="govuk-pagination__icon govuk-pagination__icon--prev"
                            xmlns="http://www.w3.org/2000/svg"
                            height="13"
                            width="15"
                            aria-hidden="true"
                            focusable="false"
                            viewBox="0 0 15 13"
                        >
                            <path d="m6.5938-0.0078125-6.7266 6.7266 6.7441 6.4062 1.377-1.449-4.1856-3.9768h12.896v-2h-12.984l4.2931-4.293-1.414-1.414z"></path>
                        </svg>
                        <span className="govuk-pagination__link-title">
                            Previous<span className="govuk-visually-hidden"> page</span>
                        </span>
                    </button>
                </div>
            )}
            <ul className="govuk-pagination__list">{pages.map(pageNumber)}</ul>
            {currentPage < totalPages - 1 && (
                <div className="govuk-pagination__next">
                    <button
                        className="govuk-link govuk-pagination__link"
                        data-testid="next-page-button"
                        rel="next"
                        onClick={(e): void => updateCurrentPage(e, currentPage + 1)}
                    >
                        <span className="govuk-pagination__link-title">
                            Next<span className="govuk-visually-hidden"> page</span>
                        </span>
                        <svg
                            className="govuk-pagination__icon govuk-pagination__icon--next"
                            xmlns="http://www.w3.org/2000/svg"
                            height="13"
                            width="15"
                            aria-hidden="true"
                            focusable="false"
                            viewBox="0 0 15 13"
                        >
                            <path d="m8.107-0.0078125-1.4136 1.414 4.2926 4.293h-12.986v2h12.896l-4.1855 3.9766 1.377 1.4492 6.7441-6.4062-6.7246-6.7266z"></path>
                        </svg>
                    </button>
                </div>
            )}
        </nav>
    );
};

export default Pagination;
