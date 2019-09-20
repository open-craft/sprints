import {PARAM_FROM, PARAM_TO, PATH_SUSTAINABILITY_DASHBOARD} from "../constants";

const aggregateAccounts = (data) => {
    let result = {};

    for (const [account_type, accounts] of Object.entries(data)) {
        result[account_type] = {
            'overall': 0,
            'by_cell': {},
            'by_person': {},
        };

        for (const account of accounts) {
            // Calculate overall.
            result[account_type].overall = (result[account_type].overall || 0) + account.overall;

            // Calculate for each cell.
            for (const [cell, hours] of Object.entries(account.by_cell)) {
                result[account_type].by_cell[cell] = (result[account_type].by_cell[cell] || 0) + hours;
            }

            // Calculate for each person.
            for (const [person, hours] of Object.entries(account.by_person)) {
                result[account_type].by_person[person] = (result[account_type].by_person[person] || 0) + hours;
            }
        }
    }

    return result;
};

export const loadAccounts = (from, to) => {
    let sustainability_url = `${PATH_SUSTAINABILITY_DASHBOARD}?${PARAM_FROM}${from}&${PARAM_TO}${to}`;

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
                    let accounts = aggregateAccounts(result.data);
                    dispatch({type: 'ACCOUNTS_LOADED', accounts: accounts});
                    return accounts;
                } else if (result.status >= 400 && result.status < 500) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: result.data});
                    throw result.data;
                }
            });
    }
};
