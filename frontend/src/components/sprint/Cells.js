import React, {Component} from 'react';
import {Link} from "react-router-dom";
import {connect} from "react-redux";
import {auth, sprints} from "../../actions";


const CellsList = ({list}) => {
    const items = [];
    Object.entries(list).forEach(([id, name]) => items.push(
        <li key={name}>
            <Link to={`board/${id}`}>{name}</Link>
        </li>
    ));

    return <ul style={{listStyle: 'none', paddingLeft: 0}}>
        {items}
    </ul>;
};

class Cells extends Component {
    componentDidMount() {
        sessionStorage.setItem('view', JSON.stringify({'name': 'cells'}));
        this.loadCells();
    }

    loadCells() {
        // Reload dashboards for all cells (using the cache, if possible).
        this.props.loadCells()
            .then(result => {
                if (result && Object.keys(result).length) {
                    Object.keys(result).forEach(id => this.props.loadBoard(id));
                }
            });
    }

    render() {
        const {cells} = this.props.sprints;
        return (
            <div className='cells'>
                {
                    cells && !Array.isArray(cells) && Object.keys(cells).length
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
        },
        loadBoard: (board_id) => {
            return dispatch(sprints.loadBoard(board_id, true));
        }
    }
};

export default connect(mapStateToProps, mapDispatchToProps)(Cells);
