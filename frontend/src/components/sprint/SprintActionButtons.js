import {connect} from "react-redux";
import React, {Component} from 'react';
import {PARAM_BOARD_ID, PATH_COMPLETE_SPRINT, PATH_CREATE_NEXT_SPRINT} from "../../constants";

class SprintActionButton extends Component {

    sprintAction = () => {
        if (window.confirm(`Are you sure you want to ${this.props.action}?`) !== true) {
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

        let complete_url = `${this.props.url}?${PARAM_BOARD_ID}${this.props.board_id}`;
        fetch(complete_url, {headers, body: "", method: "POST"})
            .then(response => response.json())
    };

    render() {
        if (this.props.is_restricted && !this.props.auth.user.is_staff) {
            return null;
        }

        return (
            <button
                className={this.props.is_restricted ? "btn-danger" : "btn-warning"}
                onClick={this.sprintAction}
                ref={btn => {
                    this.btn = btn;
                }}
            >{this.props.caption}
            </button>
        );
    }
}

const mapStateToProps = state => {
    return {
        auth: state.auth,
    }
};

let SprintActionButtonCombined = connect(mapStateToProps)(SprintActionButton);

const SprintActionButtons = ({board_id}) =>
    <div className="sprint_actions">
        <SprintActionButtonCombined
            board_id={board_id}
            caption="Create Next Sprint"
            action="create the next sprint"
            url={PATH_CREATE_NEXT_SPRINT}
            is_restricted={false}
        />
        <SprintActionButtonCombined
            board_id={board_id}
            caption="Complete Sprint"
            action="end the current sprint"
            url={PATH_COMPLETE_SPRINT}
            is_restricted={true}
        />
    </div>;

export default SprintActionButtons;
