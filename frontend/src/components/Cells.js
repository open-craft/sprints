import React, {Component} from 'react';
import {Link} from "react-router-dom";
import {connect} from "react-redux";
import {auth, sprints} from "../actions";


const CellsList = ({list}) =>
    <ul>
        {list.map(item =>
            <li key={item.name}>
                <Link to={`board/${item.board_id}`}>{item.name}</Link>
            </li>
        )}
    </ul>;

class Cells extends Component {
    componentDidMount() {
        this.props.loadCells();
    }

    render() {
        const {cells} = this.props.sprints;
        return (
            <div className='cells'>
                {
                    cells && cells.length
                        ? <CellsList list={cells}/>
                        : <div>
                            <div className="spinner-border"/>
                            <p>Loading the list of cells…</p>
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
        loadCells: () => {
            return dispatch(sprints.loadCells());
        }
    }
};

export default connect(mapStateToProps, mapDispatchToProps)(Cells);
