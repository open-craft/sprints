import {connect} from "react-redux";
import React, {Component} from 'react';
import {PATH_COMPLETE_SPRINT, PATH_DASHBOARD} from "../../constants";
import {callApi} from "../../middleware/api";
import {Link} from "react-router-dom";
import routes from "../../routes";
import Button from "../Button";
import {sprints} from "../../actions";

class SprintActionButton extends Component {
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

    componentDidMount() {
        this.props.checkPermissions(this.props.action, this.props.url, this.props.board_id);
    }

    render() {
        const canUseButton = this.props.sprints.buttons[this.props.action] === true;

        if (this.props.is_restricted) {
            if (!this.props.auth.user.is_staff) {
                return null;
            }
        }

        return (
            <button
                className={this.props.is_restricted ? (canUseButton ? "btn-danger" : "" ) : "btn-warning"}
                disabled={this.props.is_restricted ? (canUseButton ? "" : "disabled") : ""}
                onClick={this.sprintAction}
                title={this.props.sprints.canCloseSprint}
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
        sprints: state.sprints,
    }
};

const mapDispatchToProps = dispatch => {
    return {
        checkPermissions: (action, url, board_id) => {
            return dispatch(sprints.checkPermissions(action, url, board_id));
        }
    }
};

let SprintActionButtonCombined = connect(mapStateToProps, mapDispatchToProps)(SprintActionButton);

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
