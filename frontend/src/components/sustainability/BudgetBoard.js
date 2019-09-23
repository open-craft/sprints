import React, {Component} from "react";
import {connect} from "react-redux";
import {auth, sustainability} from "../../actions";

import "react-datepicker/dist/react-datepicker.css";
import BudgetTable from "./BudgetTable";

class BudgetBoard extends Component {
    constructor(props) {
        super(props);

        this.state = {
            year: this.props.sustainability.year,
        };
    }

    loadAccounts = () => this.props.loadAccounts(this.state.year);

    componentDidMount() {
        this.loadAccounts();
    }

    prepareData(accounts, range, id) {
        if (!accounts || !Object.keys(accounts).length) {
            return [];
        }

        const data = {};
        let overhead = 0;  // Calculate the overhead of the billable budgets.

        Object.entries(accounts).forEach(([account_type, accounts]) => {
            accounts.forEach(account => {
                let entry = account;
                if (account_type.startsWith('billable')) {
                    entry.category = 'Billable';
                    overhead += Math.max(account.overall - account.ytd_goal, 0)
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
                data[account.key] = entry;
            });
        });

        Object.values(this.props.sprints.boards).forEach(board => {
            board.issues.forEach(issue => {
                try {
                    if (issue.current_sprint) {
                        data[issue.account].overall_left_this_sprint += (issue.assignee_time + issue.review_time) / 3600;
                    } else {
                        data[issue.account].overall_planned_next_sprint += (issue.assignee_time + issue.review_time) / 3600;
                    }
                } catch (e) {
                    // Ignore closed accounts.
                }
            })
        });

        Object.values(data).forEach(account => {
            account.remaining_next_sprint = account.ytd_goal - account.overall - account.overall_left_this_sprint - account.overall_planned_next_sprint;
        });


        if (range === 'board' && Object.keys(this.props.sprints.boards).length) {
            this.props.sprints.boards[id].issues.forEach(issue => {
                try {
                    if (issue.current_sprint) {
                        data[issue.account].left_this_sprint += (issue.assignee_time + issue.review_time) / 3600;
                    } else {
                        data[issue.account].planned_next_sprint += (issue.assignee_time + issue.review_time) / 3600;
                    }
                } catch (e) {
                    // Ignore closed accounts.
                }
            });
        } else if (range === 'user_board' && Object.keys(this.props.sprints.boards).length) {
            Object.values(this.props.sprints.boards).forEach(board => {
                board.issues.forEach(issue => {
                    try {
                        if (issue.current_sprint) {
                            if (issue.assignee === id) {
                                data[issue.account].left_this_sprint += issue.assignee_time / 3600;
                            } else if (issue.reviewer_1 === id) {
                                data[issue.account].left_this_sprint += issue.review_time / 3600;
                            }
                        } else {
                            if (issue.assignee === id) {
                                data[issue.account].planned_next_sprint += issue.assignee_time / 3600;
                            } else if (issue.reviewer_1 === id) {
                                data[issue.account].planned_next_sprint += issue.review_time / 3600;
                            }
                        }
                    } catch (e) {
                        // Ignore closed accounts.
                    }
                })
            });
        } else {
            Object.values(data).forEach(account => {
                account.left_this_sprint = account.overall_left_this_sprint;
                account.planned_next_sprint = account.overall_planned_next_sprint;
            });
        }

        data['Overhead'] = {
            name: 'Overhead',
            key: 'Overhead',
            overall: overhead,
            ytd_goal: 0,
            overall_left_this_sprint: 0,
            overall_planned_next_sprint: 0,
            left_this_sprint: 0,
            planned_next_sprint: 0,
            remaining_next_sprint: -overhead,
        };

        return Object.values(data);
    }

    render() {
        const view = JSON.parse(sessionStorage.getItem("view")) || {'name': 'cells'};
        const {name, id} = view;
        const {budgetsLoading, budgets} = this.props.sustainability;
        const data = this.prepareData(budgets, name, id);

        return (
            <div className='sustainability'>
                <h2>Budget</h2>
                {
                    Object.keys(data).length
                        ? <div>
                            {
                                budgetsLoading
                                    ? <div className="loading">
                                        <div className="spinner-border"/>
                                        <p>You are viewing the cached version now. The dashboard is being reloaded…</p>
                                    </div>
                                    : <div/>
                            }
                            {
                                !Object.keys(this.props.sprints.boards).length
                                    ? <div className="loading">
                                        <p>You need to load cells' boards before seeing the "Left this sprint" and "Next sprint"
                                            values.</p>
                                    </div>
                                    : <div/>
                            }
                            <BudgetTable accounts={data}/>
                        </div>
                        : <div>
                            <div className="spinner-border"/>
                            <p>Loading the dashboard…</p>
                        </div>
                }
            </div>
        );
    }
}

const mapStateToProps = state => {
    return {
        auth: state.auth,
        sprints: state.sprints,
        sustainability: state.sustainability,
    }
};

const mapDispatchToProps = dispatch => {
    return {
        loadUser: () => {
            return dispatch(auth.loadUser());
        },
        loadAccounts: (from, to) => {
            return dispatch(sustainability.loadAccounts(from, to));
        }
    }
};

export default connect(mapStateToProps, mapDispatchToProps)(BudgetBoard);
