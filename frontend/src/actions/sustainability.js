import {PARAM_FROM, PARAM_TO, PATH_SUSTAINABILITY_DASHBOARD} from "../constants";
import {callApi} from "../middleware/api";

const aggregateAccounts = (data) => {
    let result = {};

    Object.entries(data).forEach(([account_type, accounts]) => {
        result[account_type] = {
            'overall': 0,
            'by_project': {},
            'by_person': {},
        };

        accounts.forEach(account => {
            // Calculate overall.
            result[account_type].overall = (result[account_type].overall || 0) + account.overall;

            // Calculate for each cell.
            Object.entries(account.by_project).forEach(([project, hours]) => {
                result[account_type].by_project[project] = (result[account_type].by_project[project] || 0) + hours;
            });

            // Calculate for each person.
            Object.entries(account.by_person).forEach(([person, hours]) => {
                result[account_type].by_person[person] = (result[account_type].by_person[person] || 0) + hours;
            });
        });
    });

    return result;
};

const add_overhead = (accounts, budgets) => {
    budgets.billable_accounts.forEach(account => {
        // Calculate overall.
        accounts.billable_accounts.overall -= Math.max(account.overall - account.period_goal, 0);
        accounts.non_billable_responsible_accounts.overall += Math.max(account.overall - account.period_goal, 0);

        // Calculate for each cell.
        Object.entries(account.by_project).forEach(([project, hours]) => {
            accounts.billable_accounts.by_project[project] -= Math.max(account.by_project[project] - account.period_goal, 0);
            accounts.non_billable_responsible_accounts.by_project[project] += Math.max(account.by_project[project] - account.period_goal, 0);
        });

        // Calculate for each person.
        Object.entries(account.by_person).forEach(([person, hours]) => {
            accounts.billable_accounts.by_person[person] -= Math.max(account.by_person[person] - account.period_goal, 0);
            accounts.non_billable_responsible_accounts.by_person[person] += Math.max(account.by_person[person] - account.period_goal, 0);
        });
    })
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
                    add_overhead(accounts, result.data);
                    dispatch({type: 'ACCOUNTS_LOADED', accounts: accounts, budgets: result.data});

                    return result.data;
                } else if (result.status >= 400 && result.status < 500) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: result.data});
                    throw result.data;
                }
            });
    }
};
