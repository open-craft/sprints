import React, {Component} from "react";
import {connect} from "react-redux";

import {Link, Redirect} from "react-router-dom";
import {auth} from "../actions";
import GoogleLogin from "react-google-login";


class Login extends Component {
    state = {
        email: "",
        password: "",
    };

    onSubmit = e => {
        e.preventDefault();
        this.props.login(this.state.email, this.state.password);
    };

    responseGoogle = response => {
        this.props.social_login(response.code);
    };

    render() {
        if (this.props.isAuthenticated) {
            return <Redirect to="/"/>
        }
        return (
            <form onSubmit={this.onSubmit}>
                <fieldset>
                    <legend>Login</legend>
                    <p>
                        <label htmlFor="email">Email</label>
                        <input
                            type="text" id="email"
                            onChange={e => this.setState({email: e.target.value})}/>
                    </p>
                    <p>
                        <label htmlFor="password">Password</label>
                        <input
                            type="password" id="password"
                            onChange={e => this.setState({password: e.target.value})}/>
                    </p>
                    <p>
                        <button type="submit">Login</button>
                    </p>

                    <p>
                        Don't have an account? <Link to="/register">Register</Link>
                    </p>
                    <p>
                        <GoogleLogin
                            clientId="TODO"  // FIXME: Move to env
                            buttonText="Login"
                            onSuccess={this.responseGoogle}
                            onFailure={this.responseGoogle}
                            responseType="code"
                            cookiePolicy={'single_host_origin'}
                          />
                    </p>
                </fieldset>
            </form>
        )
    }
}

const mapStateToProps = state => {
    let errors = [];
    if (state.auth.errors) {
        errors = Object.keys(state.auth.errors).map(field => {
            return {field, message: state.auth.errors[field]};
        });
    }
    return {
        errors,
        isAuthenticated: state.auth.isAuthenticated
    };
};

const mapDispatchToProps = dispatch => {
    return {
        login: (email, password) => {
            return dispatch(auth.login(email, password));
        },
        social_login: (code) => {
            return dispatch(auth.social_login(code));
        }
    };
};

export default connect(mapStateToProps, mapDispatchToProps)(Login);
