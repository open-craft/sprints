import {createSelector} from 'reselect'
import {OTHER_CELL_NAME} from "../constants";

const calculateSprintTime = (board, data, overall, user_id) => {
    let prefix = overall ? 'overall_' : '';
    board.issues.forEach(issue => {
        try {
            if (issue.current_sprint) {
                if (issue.assignee !== OTHER_CELL_NAME && (!user_id || issue.assignee === user_id)) {
                    data[issue.account][prefix + 'left_this_sprint'] += issue.assignee_time / 3600;
                }
                if (issue.reviewer_1 !== OTHER_CELL_NAME && (!user_id || issue.reviewer_1 === user_id)) {
                    data[issue.account][prefix + 'left_this_sprint'] += issue.review_time / 3600;
                }
            } else {
                if (issue.assignee !== OTHER_CELL_NAME && (!user_id || issue.assignee === user_id)) {
                    data[issue.account][prefix + 'planned_next_sprint'] += issue.assignee_time / 3600;
                }
                if (issue.reviewer_1 !== OTHER_CELL_NAME && (!user_id || issue.reviewer_1 === user_id)) {
                    data[issue.account][prefix + 'planned_next_sprint'] += issue.review_time / 3600;
                }
            }
        } catch (e) {
            // Ignore closed accounts.
        }
    })
};

const getBudgets = state => state.sustainability.budgets;
const getBoards = state => state.sprints.boards;
const getCells = state => state.sprints.cells;
const getView = state => state.view || JSON.parse(sessionStorage.getItem("view")) || {'name': 'cells'};

export const getAccounts = createSelector(
    [getBudgets, getView, getBoards, getCells],
    (accounts, view, boards, cells) => {
        const {name: range, id} = view;
        if (!accounts || !Object.keys(accounts).length || !boards || (range === 'board' && !boards[id])) {
            return [];
        }

        // Operate on copies, so state changes will be handled correctly.
        accounts = JSON.parse(JSON.stringify(accounts));

        const data = {};

        Object.entries(accounts).forEach(([account_type, accounts]) => {
            accounts.forEach(account => {
                let entry = account;
                if (account_type.startsWith('billable')) {
                    entry.category = 'Billable';
                } else if (account_type.includes('responsible')) {
                    entry.category = 'Non-billable cell';
                } else {
                    entry.category = 'Non-billable non-cell';
                }
                entry.overall_left_this_sprint = 0;
                entry.overall_planned_next_sprint = 0;
                entry.left_this_sprint = 0;
                entry.planned_next_sprint = 0;
                entry.remaining_next_sprint = 0;
                data[account.name] = entry;
            });
        });

        Object.values(boards).forEach(board => calculateSprintTime(board, data, true));

        Object.values(data).forEach(account => {
            account.remaining_next_sprint = account.next_sprint_goal - account.ytd_overall - account.overall_left_this_sprint - account.overall_planned_next_sprint;
        });

        if (range === 'board' && Object.keys(boards).length) {
            const cell_name = cells[id];
            Object.values(data).forEach(account => {
                account.overall = account.by_project[cell_name] || 0;
                account.ytd_overall = account.ytd_by_project[cell_name] || 0;
            });
            Object.values(boards).forEach(board => calculateSprintTime(board, data, false, cell_name));

            calculateSprintTime(boards[id], data, false);
        } else if (range === 'user_board' && Object.keys(boards).length) {
             Object.values(data).forEach(account => {
                account.overall = account.by_person[id] || 0;
                account.ytd_overall = account.ytd_by_person[id] || 0;
            });
            Object.values(boards).forEach(board => calculateSprintTime(board, data, false, id));
        } else {
            Object.values(data).forEach(account => {
                account.left_this_sprint = account.overall_left_this_sprint;
                account.planned_next_sprint = account.overall_planned_next_sprint;
            });
        }

        // Calculate the overhead of the billable budgets.
        let ytd_overhead = 0;
        let period_overhead = 0;
        Object.values(data).forEach(account => {
            if (account.category === 'Billable') {
                ytd_overhead += Math.max(account.ytd_overall - account.ytd_goal, 0);
                period_overhead += Math.max(account.overall - account.period_goal, 0);
            }
        });

        data['Overhead'] = {
            name: 'Overhead',
            ytd_overall: ytd_overhead,
            overall: period_overhead,
            ytd_goal: 0,
            period_goal: 0,
            overall_left_this_sprint: 0,
            overall_planned_next_sprint: 0,
            left_this_sprint: 0,
            planned_next_sprint: 0,
            remaining_next_sprint: -ytd_overhead,
            category: 'Non-billable cell',
        };

        return Object.values(data);
    });
