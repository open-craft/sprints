import React, {Component} from "react";
import {connect} from "react-redux";

import {Link, Redirect} from "react-router-dom";

import {auth} from "../actions";

class Login extends Component {

    state = {
        email: "",
        password1: "",
        password2: "",
    };

    onSubmit = e => {
        e.preventDefault();
        this.props.register(this.state.email, this.state.password1, this.state.password2);
    };

    render() {
        if (this.props.isAuthenticated) {
            return <Redirect to="/"/>
        }
        return (
            <form onSubmit={this.onSubmit}>
                <fieldset>
                    <legend>Register</legend>
                    {this.props.errors.length > 0 && (
                        <ul>
                            {this.props.errors.map(error => (
                                <li key={error.field}>{error.message}</li>
                            ))}
                        </ul>
                    )}
                    <p>
                        <label htmlFor="email">Email</label>
                        <input
                            type="text" id="email"
                            onChange={e => this.setState({email: e.target.value})}/>
                    </p>
                    <p>
                        <label htmlFor="password1">Password</label>
                        <input
                            type="password" id="password1"
                            onChange={e => this.setState({password1: e.target.value})}/>
                    </p>
                    <p>
                        <label htmlFor="password2">Repeat Password</label>
                        <input
                            type="password" id="password2"
                            onChange={e => this.setState({password2: e.target.value})}/>
                    </p>
                    <p>
                        <button type="submit">Register</button>
                    </p>

                    <p>
                        Already have an account? <Link to="/login">Login</Link>
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
        register: (email, password1, password2) => dispatch(auth.register(email, password1, password2)),
    };
};

export default connect(mapStateToProps, mapDispatchToProps)(Login);
