(() => {
    let startDate = JSON.parse(sessionStorage.getItem("startDate"));
    let endDate = JSON.parse(sessionStorage.getItem("endDate"));

    if (!(startDate && endDate)) {  // Not found in sessionStorage, fallback to first and last day of the month.
        let date = new Date(), y = date.getFullYear(), m = date.getMonth();
        startDate = new Date(y, m, 1);
        endDate = new Date(y, m + 1, 0);

        sessionStorage.setItem("startDate", JSON.stringify(startDate));
        sessionStorage.setItem("endDate", JSON.stringify(endDate));
    }
})();

const initialState = {
    accountsLoading: false,
    accounts: JSON.parse(localStorage.getItem("accounts")) || {},
    budgets: JSON.parse(localStorage.getItem("budgets")) || {},
    startDate: new Date(JSON.parse(sessionStorage.getItem("startDate"))),
    endDate: new Date(JSON.parse(sessionStorage.getItem("endDate"))),
    year: JSON.parse(sessionStorage.getItem("year")) || new Date().getFullYear(),
};


export default function sustainability(state = initialState, action) {
    switch (action.type) {
        case 'ACCOUNTS_LOADING':
            return {...state, accountsLoading: true, budgetsLoading: true};

        case 'ACCOUNTS_LOADED':
            localStorage.setItem("accounts", JSON.stringify(action.accounts));
            localStorage.setItem("budgets", JSON.stringify(action.budgets));
            return {...state, accountsLoading: false, accounts: action.accounts, budgets: action.budgets};

        default:
            return state;
    }
}
