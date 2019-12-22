import React, {Component} from "react";
import DatePicker from "react-datepicker";
import SustainabilityTable from "./SustainabilityTable";
import {connect} from "react-redux";
import {auth, sustainability} from "../../actions";
import {
    COMPANY_NAME,
    MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO,
    MAX_NON_BILLABLE_TO_BILLABLE_RATIO, SUSTAINABILITY_DASHBOARD_DOCS
} from "../../constants";

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
            try {
                const project_name = this.viewName(range, id);
                data.billable = accounts.billable_accounts.by_project[project_name] || 0;
                data.non_billable = accounts.non_billable_accounts.by_project[project_name] || 0;
                data.non_billable_responsible = accounts.non_billable_responsible_accounts.by_project[project_name] || 0;
            }
            catch (e) {
                // Cell's board not loaded.
            }
        } else if (range === 'user_board') {
            data.billable = accounts.billable_accounts.by_person[id] || 0;
            data.non_billable = accounts.non_billable_accounts.by_person[id] || 0;
            data.non_billable_responsible = accounts.non_billable_responsible_accounts.by_person[id] || 0;
        } else {
            data.billable = accounts.billable_accounts.overall || 0;
            data.non_billable = accounts.non_billable_accounts.overall || 0;
            data.non_billable_responsible = accounts.non_billable_responsible_accounts.overall || 0;
        }
        data.non_billable_total = data.non_billable + data.non_billable_responsible;
        data.total = data.billable + data.non_billable_total;
        data.total_ratio = data.non_billable_total / data.total * 100;
        data.remaining = data.billable * MAX_NON_BILLABLE_TO_BILLABLE_RATIO / (1 - MAX_NON_BILLABLE_TO_BILLABLE_RATIO) - data.non_billable_total;
        data.cell_hours = data.billable + data.non_billable_responsible;
        data.responsible_ratio = data.non_billable_responsible / data.cell_hours * 100;
        data.remaining_responsible = data.billable * MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO / (1 - MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO) - data.non_billable_responsible;

        return data;
    }

    viewName(range, id) {
        if (range === 'board') {
            return this.props.sprints.cells[id];
        } else if (range === 'user_board') {
            return id;
        }
        return COMPANY_NAME;
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
        const view_name = this.viewName(name, id);

        return (
            <div className='sustainability'>
                <h2>
                    <a href={SUSTAINABILITY_DASHBOARD_DOCS} target='_blank' rel='noopener noreferrer'>
                        Sustainability
                    </a> of {view_name}
                </h2>
                From: &nbsp;
                <DatePicker
                    selected={this.state.startDate}
                    startDate={this.state.startDate}
                    endDate={this.state.endDate}
                    selectsStart
                    dateFormat="yyyy/MM/dd"
                    onChange={this.handleStartDateChange}
                /> &ensp;
                To: &nbsp;
                <DatePicker
                    selected={this.state.endDate}
                    startDate={this.state.startDate}
                    endDate={this.state.endDate}
                    selectsEnd
                    dateFormat="yyyy/MM/dd"
                    onChange={this.handleEndDateChange}
                />

                {
                    // Is data present + logical implication for checking whether the cell is loaded.
                    Object.keys(data).length && (name !== 'board' || this.props.sprints.boards[id])
                        ? <div>
                            {
                                accountsLoading
                                    ? <div className="loading">
                                        <div className="spinner-border"/>
                                        <p>You are viewing the cached version now. The dashboard is being reloaded…</p>
                                    </div>
                                    : <div/>
                            }
                            <SustainabilityTable accounts={data} view={name}/>
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
