import React, {Component} from "react";
import DatePicker from "react-datepicker";
import SustainabilityTable from "./SustainabilityTable";
import {connect} from "react-redux";
import {auth, sustainability} from "../../actions";
import {MAX_NON_BILLABLE_TO_BILLABLE_RATIO} from "../../constants";

import "react-datepicker/dist/react-datepicker.css";

class SustainabilityBoard extends Component {
    constructor(props) {
        super(props);

        this.state = {
            startDate: this.props.sustainability.startDate,
            endDate: this.props.sustainability.endDate,
        };
    }

    // Because everyone counts months from 0.
    dateString = (d) => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;

    loadAccounts = () => this.props.loadAccounts(this.dateString(this.state.startDate), this.dateString(this.state.endDate));

    componentDidMount() {
        this.loadAccounts();
    }

    prepareData(accounts, range, id) {
        if (!accounts || !Object.keys(accounts).length) {
            return {};
        }

        const data = {};

        if (range === 'board') {
            const cell_name = this.props.sprints.cells[id];
            data.billable = accounts.billable_accounts.by_cell[cell_name];
            data.non_billable = accounts.non_billable_accounts.by_cell[cell_name];
            data.non_billable_responsible = accounts.non_billable_responsible_accounts.by_cell[cell_name];
        } else if (range === 'user_board') {
            data.billable = accounts.billable_accounts.by_person[id];
            data.non_billable = accounts.non_billable_accounts.by_person[id];
            data.non_billable_responsible = accounts.non_billable_responsible_accounts.by_person[id];
        } else {
            data.billable = accounts.billable_accounts.overall;
            data.non_billable = accounts.non_billable_accounts.overall;
            data.non_billable_responsible = accounts.non_billable_responsible_accounts.overall;
        }
        data.non_billable_total = data.non_billable + data.non_billable_responsible;
        data.responsible_ratio = data.non_billable_responsible / data.billable * 100;
        data.total_ratio = data.non_billable_total / data.billable * 100;
        data.remaining = data.billable * MAX_NON_BILLABLE_TO_BILLABLE_RATIO - data.non_billable_responsible;

        return data;
    }

    handleStartDateChange = date => {
        sessionStorage.setItem("startDate", JSON.stringify(date));
        localStorage.setItem("startDate", JSON.stringify(date));
        // Invoke `loadAccounts` as a callback, because `setState` is asynchronous.
        this.setState({startDate: date}, this.loadAccounts);
    };

    handleEndDateChange = date => {
        sessionStorage.setItem("endDate", JSON.stringify(date));
        localStorage.setItem("endDate", JSON.stringify(date));
        // Invoke `loadAccounts` as a callback, because `setState` is asynchronous.
        this.setState({endDate: date}, this.loadAccounts);
    };

    render() {
        const view = JSON.parse(sessionStorage.getItem("view")) || {'name': 'cells'};
        const {name, id} = view;
        const {accountsLoading, accounts} = this.props.sustainability;
        const data = this.prepareData(accounts, name, id);

        return (
            <div className='sustainability'>
                <h2>Sustainability</h2>
                From: &nbsp;
                <DatePicker
                    selected={this.state.startDate}
                    startDate={this.state.startDate}
                    endDate={this.state.endDate}
                    selectsStart
                    dateFormat="dd/MM/yyyy"
                    onChange={this.handleStartDateChange}
                /> &ensp;
                To: &nbsp;
                <DatePicker
                    selected={this.state.endDate}
                    startDate={this.state.startDate}
                    endDate={this.state.endDate}
                    selectsEnd
                    dateFormat="dd/MM/yyyy"
                    onChange={this.handleEndDateChange}
                />

                {
                    Object.keys(data).length
                        ? <div>
                            {
                                accountsLoading
                                    ? <div className="loading">
                                        <div className="spinner-border"/>
                                        <p>You are viewing the cached version now. The dashboard is being reloaded…</p>
                                    </div>
                                    : <div/>
                            }
                            <SustainabilityTable accounts={data}/>
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

export default connect(mapStateToProps, mapDispatchToProps)(SustainabilityBoard);
