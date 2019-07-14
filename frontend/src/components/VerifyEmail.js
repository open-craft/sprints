import React, {Component} from "react";
import {connect} from "react-redux";

import {Redirect} from "react-router-dom";

import {auth} from "../actions";

class VerifyEmail extends Component {
    componentDidMount() {
        const {key} = this.props.match.params;
        this.props.verify_email(key);
    }

    render() {
        return <Redirect to="/"/>
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
        verify_email: (key) => dispatch(auth.verify_email(key)),
    };
};

export default connect(mapStateToProps, mapDispatchToProps)(VerifyEmail);
