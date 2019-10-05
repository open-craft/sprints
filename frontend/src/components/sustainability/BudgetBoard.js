import React, {Component} from "react";
import {connect} from "react-redux";
import {auth, sustainability} from "../../actions";

import "react-datepicker/dist/react-datepicker.css";
import BudgetTable from "./BudgetTable";
import {getAccounts} from "../../selectors/sustainability";

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

    render() {
        const view = JSON.parse(sessionStorage.getItem("view")) || {'name': 'cells'};
        const {name, id} = view;
        const {budgetsLoading} = this.props.sustainability;
        const data = this.props.accounts;

        return (
            <div className='sustainability'>
                <h2>Budget</h2>
                {
                    // Is data present + logical implication for checking whether the cell is loaded.
                    Object.keys(data).length && (name !== 'board' || this.props.sprints.boards[id])
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
                            <BudgetTable accounts={data} view={name}/>
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
        },
        loadAccounts: (from, to) => {
            return dispatch(sustainability.loadAccounts(from, to));
        }
    }
};

export default connect(mapStateToProps, mapDispatchToProps)(BudgetBoard);
