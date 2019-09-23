import {PARAM_FROM, PARAM_TO, PARAM_YEAR, PATH_SUSTAINABILITY_DASHBOARD} from "../constants";

const aggregateAccounts = (data) => {
    let result = {};

    Object.entries(data).forEach(([account_type, accounts]) => {
        result[account_type] = {
            'overall': 0,
            'by_cell': {},
            'by_person': {},
        };

        accounts.forEach(account => {
            // Calculate overall.
            result[account_type].overall = (result[account_type].overall || 0) + account.overall;

            // Calculate for each cell.
            Object.entries(account.by_cell).forEach(([cell, hours]) => {
                result[account_type].by_cell[cell] = (result[account_type].by_cell[cell] || 0) + hours;
            });

            // Calculate for each person.
            Object.entries(account.by_person).forEach(([person, hours]) => {
                result[account_type].by_person[person] = (result[account_type].by_person[person] || 0) + hours;
            });
        });
    });

    return result;
};

export const loadAccounts = (from, to) => {
    let sustainability_url;
    if (to) {
        sustainability_url = `${PATH_SUSTAINABILITY_DASHBOARD}?${PARAM_FROM}${from}&${PARAM_TO}${to}`;
    } else {
        sustainability_url = `${PATH_SUSTAINABILITY_DASHBOARD}?${PARAM_YEAR}${from}`;
    }

    return (dispatch, getState) => {
        dispatch({type: "ACCOUNTS_LOADING"});

        let token = getState().auth.token;
        let headers = {
            "Content-Type": "application/json",
        };
        if (token) {
            headers["Authorization"] = `JWT ${token}`;
        }

        return fetch(sustainability_url, {headers,})
            .then(response => {
                if (response.status < 500) {
                    return response.json().then(data => {
                        return {status: response.status, data};
                    })
                } else {
                    console.log("Server Error!");
                    throw response;
                }
            })
            .then(result => {
                if (result.status === 200) {
                    // let accounts = to ? aggregateAccounts(result.data) : aggregateBudgets(data);
                    let accounts;
                    if (to) {
                        accounts = aggregateAccounts(result.data);
                        dispatch({type: 'ACCOUNTS_LOADED', accounts: accounts});
                    } else {
                        accounts = result.data;
                        dispatch({type: 'BUDGETS_LOADED', budgets: accounts});
                    }

                    return accounts;
                } else if (result.status >= 400 && result.status < 500) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: result.data});
                    throw result.data;
                }
            });
    }
};
