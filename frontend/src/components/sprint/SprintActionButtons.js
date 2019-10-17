import {connect} from "react-redux";
import React, {Component} from 'react';
import {PARAM_BOARD_ID, PATH_COMPLETE_SPRINT, PATH_CREATE_NEXT_SPRINT} from "../../constants";
import {callApi} from "../../middleware/api";
import {Link} from "react-router-dom";
import routes from "../../routes";
import Button from "../Button";

class SprintActionButton extends Component {

    sprintAction = () => {
        if (window.confirm(`Are you sure you want to ${this.props.action}?`) !== true) {
            return;
        }

        let action_url = `${this.props.url}?${PARAM_BOARD_ID}${this.props.board_id}`;
        callApi(action_url, "", "POST")
            .then(response => {
                if (response.status === 200) {
                    this.btn.setAttribute("disabled", "disabled");
                    this.btn.removeAttribute("class");
                    window.alert("The task has been successfully scheduled!\nYou can track its progress with Flower.");
                } else {
                    window.alert(`Error ${response.status} returned while scheduling the task.`);
                }
            })
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
        <Link to={routes.cells}><Button>Go back</Button></Link>
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
