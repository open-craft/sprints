import Button from "./Button";
import {connect} from "react-redux";
import React, {Component} from 'react';
import {auth} from "../actions";


class Logout extends Component {
    render() {
        return (
            <div className="logout">
                <Button onClick={this.props.logout}>Sign Out</Button>
            </div>
        );
    }
}

const mapStateToProps = state => {
    return {
        user: state.auth.user,
    }
};

const mapDispatchToProps = dispatch => {
    return {
        logout: () => dispatch(auth.logout()),
    }
};

export default connect(mapStateToProps, mapDispatchToProps)(Logout);
