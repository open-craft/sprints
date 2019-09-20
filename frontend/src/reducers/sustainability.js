(() => {
    let startDate = JSON.parse(sessionStorage.getItem("startDate"));
    let endDate = JSON.parse(sessionStorage.getItem("endDate"));

    if (!(startDate && endDate)) {  // Not found in sessionStorage, fallback to localStorage.
        startDate = JSON.parse(localStorage.getItem("startDate"));
        endDate = JSON.parse(localStorage.getItem("endDate"));

        if (!(startDate && endDate)) {  // Not found in localStorage, fallback to first and last day of the month.
            let date = new Date(), y = date.getFullYear(), m = date.getMonth();
            startDate = new Date(Date.UTC(y, m, 1));
            endDate = new Date(Date.UTC(y, m + 1, 0));

            localStorage.setItem("startDate", JSON.stringify(startDate));
            localStorage.setItem("endDate", JSON.stringify(endDate));
        }
        sessionStorage.setItem("startDate", JSON.stringify(startDate));
        sessionStorage.setItem("endDate", JSON.stringify(endDate));
    }
})();

const initialState = {
    accountsLoading: true,
    accounts: JSON.parse(localStorage.getItem("accounts")) || {},
    startDate: new Date(JSON.parse(sessionStorage.getItem("startDate"))),
    endDate: new Date(JSON.parse(sessionStorage.getItem("endDate"))),
};


export default function sustainability(state = initialState, action) {
    switch (action.type) {
        case 'ACCOUNTS_LOADING':
            return {...state, accountsLoading: true};

        case 'ACCOUNTS_LOADED':
            localStorage.setItem("accounts", JSON.stringify(action.accounts));
            return {...state, accountsLoading: false, accounts: action.accounts};

        default:
            return state;
    }
}
