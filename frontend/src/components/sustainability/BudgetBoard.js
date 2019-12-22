import React, {Component} from "react";
import {connect} from "react-redux";
import {auth} from "../../actions";

import "react-datepicker/dist/react-datepicker.css";
import BudgetTable from "./BudgetTable";
import {getAccounts} from "../../selectors/sustainability";
import {BUDGET_DASHBOARD_DOCS} from "../../constants";

class BudgetBoard extends Component {
    constructor(props) {
        super(props);

        this.state = {
            year: this.props.sustainability.year,
        };
    }

    render() {
        const view = JSON.parse(sessionStorage.getItem("view")) || {'name': 'cells'};
        const {name, id} = view;
        const {accountsLoading} = this.props.sustainability;
        const data = this.props.accounts;
        const {boards, boardLoading} = this.props.sprints;
        const accounts = data.filter(account => account.overall);  // Hide unused accounts.

        return (
            <div className='sustainability'>
                <h2>
                    <a href={BUDGET_DASHBOARD_DOCS} target='_blank' ref='noopener noreferrer'>
                        Budget
                    </a>
                </h2>
                {
                    // Is data present + logical implication for checking whether the cell is loaded.
                    Object.keys(data).length && (name !== 'board' || boards[id])
                        ? <div>
                            {
                                accountsLoading
                                    ? <div className="loading">
                                        <div className="spinner-border"/>
                                        <p>You are viewing the cached version now. The dashboard is being reloaded…</p>
                                    </div>
                                    : <div/>
                            }
                            {
                                boardLoading
                                    ? <div className="loading">
                                        <div className="spinner-border"/>
                                        <p>The <i>Left this sprint</i> and <i>Next Sprint</i> columns are cached versions. The dashboard is being reloaded…</p>
                                    </div>
                                    : <div/>
                            }
                            {
                                !Object.keys(this.props.sprints.boards).length
                                    ? <div className="loading">
                                        <p>You need to load cells' boards before seeing the "Left this sprint" and "Next sprint" values.</p>
                                    </div>
                                    : <div/>
                            }
                            <BudgetTable accounts={accounts} view={name}/>
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
        accounts: getAccounts(state),
    }
};

const mapDispatchToProps = dispatch => {
    return {
        loadUser: () => {
            return dispatch(auth.loadUser());
        }
    }
};

export default connect(mapStateToProps, mapDispatchToProps)(BudgetBoard);
