import React, {Component} from 'react';
import './App.css';
import Table from "./components/Table";
import Cells from "./components/Cells";


const DEFAULT_QUERY = 'redux';
const DEFAULT_HPP = '15';

const API_VERSION = 'v1';
// const PATH_BASE = `http://hn.algolia.com/api/${API_VERSION}`;
const PATH_BASE = `http://0.0.0.0:8000/dashboard/`;
const PATH_CELLS = `${PATH_BASE}cells/`;
const PATH_DASHBOARD = `${PATH_BASE}dashboard/`;
const PARAM_PROJECT = 'project=';
// const PARAM_BOARD_ID = 'board_id=';
// const PARAM_HPP = 'hitsPerPage=';

const create_dashboard_url = (project) =>
    `${PATH_DASHBOARD}?${PARAM_PROJECT}${project}`;

class App extends Component {
    constructor(props) {
        super(props);

        this.state = {
            future_sprint: '',
            cell: '',
            rows: null,
            cells: [],
        };
    }

    setCells(result) {
        this.setState({
            cells: result,
        })
    }

    fetchCells() {
        fetch(PATH_CELLS)
            .then(response => response.json())
            .then(result => this.setCells(result))
            .catch(error => error);
    }

    setDashboard(result) {
        const {rows, future_sprint, cell} = result;
        rows.sort((x, y) => (x.name > y.name) ? 1 : -1);

        this.setState({
            cell: cell,
            future_sprint: future_sprint,
            rows: rows,
        })
    }


    fetchDashboard(project) {
        fetch(create_dashboard_url(project))
            .then(response => response.json())
            .then(result => this.setDashboard(result))
            .catch(error => error);
    }

    componentDidMount() {
        this.fetchCells();
    }

    render() {
        const {rows, future_sprint, cell, cells} = this.state;
        const handle_click = e => this.fetchDashboard(e.target.id);
        // const page = (result && result.page) || 0;

        return (
            <div className='page'>
                <div className="interactions">
                    <h1>OpenCraft Sprint Planning Report</h1>
                    <h2>Commitments for Upcoming Sprint - {future_sprint}</h2>
                    {
                        rows
                            ? <Table
                                list={rows}
                            />
                            : cells
                                    ? <Cells
                                        list={cells}
                                        handle_click={handle_click}
                                    />
                                    : <p>Loading…</p>
                    }
                </div>
            </div>
        );
    }
}


export default App;
