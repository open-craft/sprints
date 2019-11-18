import {connect} from "react-redux";
import React, {Component} from 'react';
import {PATH_COMPLETE_SPRINT, PATH_DASHBOARD} from "../../constants";
import {callApi} from "../../middleware/api";
import {Link} from "react-router-dom";
import routes from "../../routes";
import Button from "../Button";

class SprintActionButton extends Component {
    checkAction = () => {
        let action_url = `${this.props.url}${this.props.board_id}/`;
        callApi(action_url)
            .then(response => {
                if (response.status === 200) {
                    this.btn.setAttribute("class", "btn-danger");
                    this.btn.removeAttribute("disabled");
                    this.btn.onclick = this.sprintAction;
                } else {
                    return response.json().then(data => {
                        if (data.detail) {
                            this.btn.setAttribute("title", data.detail);
                        }
                    });
                }
            })
    };

    sprintAction = () => {
        if (window.confirm(`Are you sure you want to ${this.props.action}?`) !== true) {
            return;
        }

        let action_url = `${this.props.url}${this.props.board_id}/`;
        callApi(action_url, "", "PUT")
            .then(response => {
                if (response.status === 200) {
                    this.btn.setAttribute("disabled", "disabled");
                    this.btn.removeAttribute("class");
                    window.alert("The task has been successfully scheduled!\nYou can track its progress with Flower.");
                } else {
                    return response.json().then(data => {
                        let error_message = data.detail ? `\n\n${data.detail}` : "";
                        window.alert(`Error ${response.status} returned while scheduling the task.${error_message}`);
                    })
                }
            });
    };

    render() {
        if (this.props.is_restricted) {
            if (!this.props.auth.user.is_staff) {
                return null;
            }

            this.checkAction();  // Restricted buttons require validation (obtained by sending `GET` to the same endpoint).
        }

        return (
            <button
                className={this.props.is_restricted ? "" : "btn-warning"}
                disabled={this.props.is_restricted ? "disabled" : ""}
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
            url={PATH_DASHBOARD}
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
