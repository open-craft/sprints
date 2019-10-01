import React, {Component} from 'react';
import './App.css';
import Cells from "./components/sprint/Cells";
import {BrowserRouter, Redirect, Route, Switch} from "react-router-dom";
import routes from './routes.js'
import Login from "./components/Login";
import {connect, Provider} from "react-redux";
import {auth} from "./actions/";
import {applyMiddleware, createStore} from "redux";
import thunk from "redux-thunk";
import reducer from "./reducers";
import Register from "./components/Register";
import Logout from "./components/Logout";
import VerifyEmail from "./components/VerifyEmail";
import Board from "./components/sprint/Board";
import UserBoard from "./components/sprint/UserBoard";
import SustainabilityBoard from "./components/sustainability/SustainabilityBoard";

let store = createStore(reducer, applyMiddleware(thunk));

export default class App extends Component {
    render() {
        return (
            <BrowserRouter>
                <Switch>
                    <Provider store={store}>
                        <Route component={RootContainer}/>
                    </Provider>
                </Switch>
            </BrowserRouter>
        )
    }
}

class RootContainerComponent extends Component {

    componentDidMount() {
        this.props.loadUser();
    }

    PrivateRoute = ({component: ChildComponent, ...rest}) => {
        return <Route {...rest} render={props => {
            if (this.props.auth.isLoading) {
                return <em>Loading...</em>;
            } else if (!this.props.auth.isAuthenticated) {
                let next_path = this.props.location.pathname;
                next_path = (next_path !== "/" && !next_path.startsWith("/login")) ? "?next=" + next_path : "";
                return <Redirect to={routes.login + next_path}/>;
            } else {
                return <ChildComponent {...props} />
            }
        }}/>
    };

    render() {
        let {PrivateRoute} = this;
        return (
            <div className="page app">
                <div className="page interactions">
                    {
                        this.props.auth.isAuthenticated
                            ? <div className="navbar">
                                <Logout/>
                            </div>
                            : <div/>
                    }
                </div>
                <h1>OpenCraft Sprint Planning Report</h1>

                <BrowserRouter>
                    <Switch>
                        <PrivateRoute exact path={routes.cells} component={Cells}/>
                        <PrivateRoute path={routes.user_board} component={UserBoard}/>
                        <PrivateRoute path={routes.board} component={Board}/>
                        <Route path={routes.login} component={Login}/>
                        <Route path={routes.register} component={Register}/>
                        <Route path={routes.verify_email} component={VerifyEmail}/>
                        <Route component={Login}/>
                    </Switch>
                </BrowserRouter>
                <PrivateRoute component={SustainabilityBoard}/>
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
