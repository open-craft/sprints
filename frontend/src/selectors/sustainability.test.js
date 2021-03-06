import {getAccounts} from "./sustainability";
import {OTHER_CELL_NAME} from "../constants";

test("getAccounts returns empty array if there are no accounts", () => {
    const state = {
        sustainability: {
            budgets: {}
        },
        sprints: {
            board: {}
        },
    };
    expect(getAccounts(state)).toHaveLength(0);
});

test("getAccounts returns empty array if boards aren't loaded", () => {
    const state = {
        sustainability: {
            budgets: {
                'billable_accounts': [{
                    name: 'Billable1',
                    ytd_overall: 3.1415,
                    overall: 3.1415,
                    ytd_goal: 3,
                    period_goal: 2,
                    next_sprint_goal: 10,
                    budgets: [5, 5, 0, 0, 0, 0, 0, 0, 0, 0],
                    ytd_by_project: {
                        Project1: 3,
                        Project2: .1415,
                    },
                    by_project: {
                        Project1: 3,
                        Project2: .1415,
                    },
                    ytd_by_person: {
                        Member1: 3,
                        Member2: .1415,
                    },
                    by_person: {
                        Member1: 3,
                        Member2: .1415,
                    },
                }]
            }
        },
        sprints: {
            board: {}
        },
    };
    expect(getAccounts(state)).toHaveLength(0);
});

const valid_state = {
    sustainability: {
        budgets: {
            'billable_accounts': [{
                name: 'Billable1',
                ytd_overall: 3.1415,
                overall: 3.1415,
                ytd_goal: 2,
                period_goal: 3,
                next_sprint_goal: 10,
                budgets: [5, 5, 0, 0, 0, 0, 0, 0, 0, 0],
                ytd_by_project: {
                    Project1: 3,
                    Project2: .1415,
                },
                by_project: {
                    Project1: 3,
                    Project2: .1415,
                },
                ytd_by_person: {
                    Member1: 3,
                    Member2: .1415,
                },
                by_person: {
                    Member1: 3,
                    Member2: .1415,
                },
            }]
        }
    },
    sprints: {
        boards: {
            1: {
                'rows': [{
                    name: 'Member1',
                }],
                'issues': [{
                    key: "Issue1",
                    account: "Billable1",
                    assignee: 'Member1',
                    reviewer_1: OTHER_CELL_NAME,
                    assignee_time: 10800,
                    review_time: 509.4,
                    current_sprint: true,
                }, {
                    key: "Issue2",
                    account: "Billable1",
                    assignee: 'Member1',
                    reviewer_1: OTHER_CELL_NAME,
                    assignee_time: 7200,
                    review_time: 2585.52,
                    current_sprint: false,
                }]
            },
            2: {
                'rows': [{
                    name: 'Member2',
                }],
                'issues': [{
                    key: "Issue1",
                    account: "Billable1",
                    assignee: OTHER_CELL_NAME,
                    reviewer_1: 'Member2',
                    assignee_time: 10800,
                    review_time: 509.4,
                    current_sprint: true,
                }, {
                    key: "Issue2",
                    account: "Billable1",
                    assignee: OTHER_CELL_NAME,
                    reviewer_1: 'Member2',
                    assignee_time: 7200,
                    review_time: 2585.52,
                    current_sprint: false,
                }]
            },
        },
        cells: {
            1: "Project1",
            2: "Project2",
        },
    },
};

test("getAccounts properly computes overall data", () => {
    const result = getAccounts(valid_state);
    expect(result[0].name).toEqual('Billable1');
    expect(result[0].left_this_sprint).toEqual(3.1415);
    expect(result[0].planned_next_sprint).toEqual(2.7182);
    expect(result[0].remaining_next_sprint).toBeCloseTo(1);
});

test("getAccounts properly computes cell's data", () => {
    const state = JSON.parse(JSON.stringify(valid_state));
    state.view = {
        name: 'board',
        id: 1,
    };
    const result = getAccounts(state);
    expect(result[0].name).toEqual('Billable1');
    expect(result[0].ytd_overall).toEqual(3);
    expect(result[0].left_this_sprint).toEqual(3);
    expect(result[0].planned_next_sprint).toEqual(2);
});

test("getAccounts properly computes user's data", () => {
    const state = JSON.parse(JSON.stringify(valid_state));
    state.view = {
        name: 'user_board',
        id: 'Member2',
    };
    const result = getAccounts(state);
    expect(result[0].name).toEqual('Billable1');
    expect(result[0].ytd_overall).toEqual(0.1415);
    expect(result[0].left_this_sprint).toEqual(0.1415);
    expect(result[0].planned_next_sprint).toEqual(0.7182);
});


test("getAccounts creates Overhead account", () => {
    const result = getAccounts(valid_state);
    expect(result[result.length - 1].name).toEqual('Overhead');
    expect(result[result.length - 1].category).toEqual('Non-billable cell');
    expect(result[result.length - 1].ytd_overall).toBeCloseTo(1.1415);
    expect(result[result.length - 1].overall).toBeCloseTo(0.1415);
});
