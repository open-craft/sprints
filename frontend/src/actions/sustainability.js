import {PARAM_FROM, PARAM_TO, PATH_SUSTAINABILITY_DASHBOARD} from "../constants";
import {callApi} from "../middleware/api";

const aggregateAccounts = (data) => {
    let result = {};

    Object.entries(data).forEach(([account_type, accounts]) => {
        result[account_type] = {
            'overall': 0,
            'by_person': {},
        };

        accounts.forEach(account => {
            // Calculate overall.
            result[account_type].overall = (result[account_type].overall || 0) + account.overall;

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
    sustainability_url = `${PATH_SUSTAINABILITY_DASHBOARD}?${PARAM_FROM}${from}&${PARAM_TO}${to}`;

    return (dispatch) => {
        dispatch({type: "ACCOUNTS_LOADING"});

        return callApi(sustainability_url)
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
                    dispatch({type: 'ACCOUNTS_LOADED', accounts: accounts, budgets: result.data});

                    return result.data;
                } else if (result.status >= 400 && result.status < 500) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: result.data});
                    throw result.data;
                }
            });
    }
};
