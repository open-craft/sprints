import {connect} from "react-redux";
import React, {Component} from 'react';
import {PARAM_BOARD_ID, PATH_COMPLETE_SPRINT} from "../constants";

class CompleteSprintButton extends Component {

    completeSprint = () => {
        if (window.confirm("Are you sure you want to end the current sprint?") !== true) {
            return;
        }

        this.btn.setAttribute("disabled", "disabled");
        let token = this.props.auth.token;
        let headers = {
            "Content-Type": "application/json",
        };
        if (token) {
            headers["Authorization"] = `JWT ${token}`;
        }

        let complete_url = `${PATH_COMPLETE_SPRINT}?${PARAM_BOARD_ID}${this.props.board_id}`;
        fetch(complete_url, {headers, body: "", method: "POST"})
            .then(response => response.json())
    };

    render() {
        return (
            <div className="complete_sprint">
                <button
                    className="btn-danger"
                    onClick={this.completeSprint}
                    ref={btn => {
                        this.btn = btn;
                    }}
                >Complete Sprint
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

export default connect(mapStateToProps)(CompleteSprintButton);
