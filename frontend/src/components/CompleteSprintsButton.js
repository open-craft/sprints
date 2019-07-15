import {connect} from "react-redux";
import React, {Component} from 'react';

const PATH_COMPLETE_SPRINTS = `${process.env.REACT_APP_API_BASE}/dashboard/complete_sprints/`;


class CompleteSprintsButton extends Component {
    completeSprints = () => {
        this.btn.setAttribute("disabled", "disabled");
        let token = this.props.auth.token;
        let headers = {
            "Content-Type": "application/json",
        };
        if (token) {
            headers["Authorization"] = `JWT ${token}`;
        }

        fetch(PATH_COMPLETE_SPRINTS, {headers, body: "", method: "POST"})
            .then(response => response.json())
    };

    render() {
        return (
            <div className="complete_sprints">
                <button
                    className="btn-danger"
                    onClick={this.completeSprints}
                    ref={btn => {
                        this.btn = btn;
                    }}
                >Complete Sprints
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

export default connect(mapStateToProps)(CompleteSprintsButton);
