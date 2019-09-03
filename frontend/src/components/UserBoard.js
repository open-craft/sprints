import React, {Component} from "react";
import {connect} from "react-redux";
import {auth, sprints} from "../actions";
import UserTable from "./UserTable";

class UserBoard extends Component {
    constructor(props) {
        super(props);

        this.state = {
            board_id: this.props.match.params.board_id,
            username: this.props.match.params.username,
        };
    }

    componentDidMount() {
        this.props.loadBoard(this.state.board_id);
    }

    filterIssues(issues) {
        return issues.filter(el => el.assignee === this.state.username || el.reviewer_1 === this.state.username);
    }

    render() {
        const username = this.state.username;
        const {boardLoading, boards} = this.props.sprints;
        const board = boards[this.state.board_id] || {};

        const {issues} = board;
        const user_issues = this.filterIssues(issues);

        return (
            <div className='dashboard'>
                {
                    user_issues && user_issues.length
                        ? <div>
                            {
                                boardLoading
                                    ? <div className="loading">
                                        <div className="spinner-border"/>
                                        <p>You are viewing the cached version now. The dashboard is being reloaded…</p>
                                    </div>
                                    : <div/>
                            }
                            <h2>Commitments of {username} for the current and upcoming sprint</h2>
                            <UserTable list={user_issues} username={username}/>
                        </div>
                        : <div>
                            <div className="spinner-border"/>
                            <p>Loading the dashboard…</p>
                        </div>
                }
            </div>
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
        loadUser: () => {
            return dispatch(auth.loadUser());
        },
        loadBoard: (board_id) => {
            return dispatch(sprints.loadBoard(board_id));
        }
    }
};

export default connect(mapStateToProps, mapDispatchToProps)(UserBoard);
