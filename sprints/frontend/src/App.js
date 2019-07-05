import React, {Component} from 'react';
import './App.css';
import Table from "./components/Table";
import Cells from "./components/Cells";
import {BrowserRouter, Redirect, Route, Switch} from "react-router-dom";
import routes from './routes.js'
import Login from "./components/Login";
import {connect, Provider} from "react-redux";
import {auth} from "./actions/";
import {applyMiddleware, createStore} from "redux";
import thunk from "redux-thunk";
import sprints_reducers from "./reducers";
import Register from "./components/Register";
import Logout from "./components/Logout";
import VerifyEmail from "./components/VerifyEmail";


const PATH_BASE = `${process.env.REACT_APP_API_BASE}/dashboard/`;
const PATH_CELLS = `${PATH_BASE}cells/`;
const PATH_DASHBOARD = `${PATH_BASE}dashboard/`;
const PARAM_BOARD_ID = 'board_id=';

const create_dashboard_url = (board_id) =>
    `${PATH_DASHBOARD}?${PARAM_BOARD_ID}${board_id}`;

let store = createStore(sprints_reducers, applyMiddleware(thunk));


class RootContainerComponent extends Component {

    componentDidMount() {
        this.props.loadUser();
    }

    PrivateRoute = ({component: ChildComponent, ...rest}) => {
        return <Route {...rest} render={props => {
            if (this.props.auth.isLoading) {
                return <em>Loading...</em>;
            } else if (!this.props.auth.isAuthenticated) {
                return <Redirect to={routes.login}/>;
            } else {
                return <ChildComponent {...props} />
            }
        }}/>
    };

    render() {
        let {PrivateRoute} = this;
        return (
            <div className="page interactions">
                {
                    this.props.auth.isAuthenticated
                        ?
                        <Logout/>
                        :
                        <div/>
                }
                <Header/>
                <BrowserRouter>
                    <Switch>
                        <PrivateRoute exact path={routes.cells} component={CellContainer}/>
                        <PrivateRoute path={routes.board} component={BoardContainer}/>
                        <Route path={routes.login} component={Login}/>
                        <Route path={routes.register} component={Register}/>
                        <Route path={routes.verify_email} component={VerifyEmail}/>
                        <Route component={Login}/>
                    </Switch>
                </BrowserRouter>
            </div>
        );
    }
}

const mapStateToProps = state => {
    return {
        auth: state.auth,
    }
};

const mapDispatchToProps = dispatch => {
    return {
        loadUser: () => {
            return dispatch(auth.loadUser());
        }
    }
};

let RootContainer = connect(mapStateToProps, mapDispatchToProps)(RootContainerComponent);

export default class App extends Component {
    render() {
        return (
            <Provider store={store}>
                <RootContainer/>
            </Provider>
        )
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
        let token = this.props.auth.token;
        let headers = {
            "Content-Type": "application/json",
        };
        if (token) {
            headers["Authorization"] = `JWT ${token}`;
        }

        fetch(PATH_CELLS, {headers,})
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

let CellContainer = connect(mapStateToProps, mapDispatchToProps)(Cell);

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
        let token = this.props.auth.token;
        let headers = {
            "Content-Type": "application/json",
        };
        if (token) {
            headers["Authorization"] = `JWT ${token}`;
        }

        fetch(create_dashboard_url(board_id), {headers,})
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

let BoardContainer = connect(mapStateToProps, mapDispatchToProps)(Board);
