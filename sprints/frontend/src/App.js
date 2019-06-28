import React, {Component} from 'react';
import './App.css';
import Table from "./components/Table";
import Cells from "./components/Cells";
import {BrowserRouter as Router, Route} from "react-router-dom";
import routes from './routes.js'


const PATH_BASE = `http://0.0.0.0:8000/dashboard/`;  // TODO: Move this to config.
const PATH_CELLS = `${PATH_BASE}cells/`;
const PATH_DASHBOARD = `${PATH_BASE}dashboard/`;
const PARAM_BOARD_ID = 'board_id=';

const create_dashboard_url = (board_id) =>
    `${PATH_DASHBOARD}?${PARAM_BOARD_ID}${board_id}`;

class App extends Component {
    render() {
        return (
            <div className="page interactions">
                <Header/>
                <Router>
                    <div>
                        <Route exact path={routes.cells} component={Cell}/>
                        <Route path={routes.board} component={Board}/>
                    </div>
                </Router>
            </div>
        );
    }
}

class Header extends Component {
    render() {
        return (
            <h1>OpenCraft Sprint Planning Report</h1>
        );
    }
}

class Cell extends Component {
    constructor(props) {
        super(props);

        this.state = {
            cell: '',
            cells: null,
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

    componentDidMount() {
        this.fetchCells();
    }

    render() {
        const {cells} = this.state;
        return (
            <div className='cells'>
                {
                    cells
                        ? <Cells list={cells}/>
                        : <div>
                            <div className="spinner-border"/>
                            <p>Loading the list of cells…</p>
                        </div>
                }
            </div>
        );
    }
}

class Board extends Component {
    constructor(props) {
        super(props);

        this.state = {
            future_sprint: '',
            rows: null,
        };
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


    fetchDashboard(board_id) {
        fetch(create_dashboard_url(board_id))
            .then(response => response.json())
            .then(result => this.setDashboard(result))
            .catch(error => error);
    }

    componentDidMount() {
        const {board_id} = this.props.match.params;
        this.fetchDashboard(board_id);
    }

    render() {
        const {rows, future_sprint} = this.state;
        return (
            <div className='dashboard'>
                {
                    rows
                        ? <div>
                            <h2>Commitments for Upcoming Sprint - {future_sprint}</h2>
                            <Table list={rows}/>
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


export default App;
