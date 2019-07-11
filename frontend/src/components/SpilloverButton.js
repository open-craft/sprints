import {connect} from "react-redux";
import React, {Component} from 'react';

const PATH_END_SPRINT = `${process.env.REACT_APP_API_BASE}/dashboard/spillovers/`;


class SpilloverButton extends Component {
    uploadSpillovers = () => {
        this.btn.setAttribute("disabled", "disabled");
        let token = this.props.auth.token;
        let headers = {
            "Content-Type": "application/json",
        };
        if (token) {
            headers["Authorization"] = `JWT ${token}`;
        }

        fetch(PATH_END_SPRINT, {headers, body: "", method: "POST"})
            .then(response => response.json())
    };

    render() {
        return (
            <div className="spillovers">
                <button
                    className="btn-danger"
                    onClick={this.uploadSpillovers}
                    ref={btn => {
                        this.btn = btn;
                    }}
                >Upload spillovers
                </button>
            </div>
        );
    }
}

const mapStateToProps = state => {
    return {
        auth: state.auth,
    }
};

export default connect(mapStateToProps)(SpilloverButton);
