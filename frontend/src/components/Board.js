import React, {Component} from "react";
import Table from "./Table";
import {connect} from "react-redux";
import {auth, sprints} from "../actions";
import SprintActionButtons from "./SprintActionButtons";

class Board extends Component {
    constructor(props) {
        super(props);

        this.state = {
            board_id: this.props.match.params.board_id,
        };
    }

    componentDidMount() {
        this.props.loadBoard(this.state.board_id);
    }

    render() {
        const {boardLoading, boards} = this.props.sprints;
        const board = boards[this.state.board_id] || {};
        const {rows, future_sprint} = board;
        const url = this.props.match.url.replace(/\/$/, '');  // Remove trailing slash, if needed.

        return (
            <div className='dashboard'>
                {
                    rows && rows.length
                        ? <div>
                            {
                                boardLoading
                                    ? <div className="loading">
                                        <div className="spinner-border"/>
                                        <p>You are viewing the cached version now. The dashboard is being reloaded…</p>
                                    </div>
                                    : <div/>
                            }
                            <h2>Commitments for Upcoming Sprint - {future_sprint}</h2>
                            <SprintActionButtons board_id={this.state.board_id}/>
                            <Table list={rows} url={url}/>
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

export default connect(mapStateToProps, mapDispatchToProps)(Board);
