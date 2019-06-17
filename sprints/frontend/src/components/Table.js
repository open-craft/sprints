import React from 'react';

const largeColumn = {width: '40%'};
const midColumn = {width: '30%'};
const smallColumn = {width: '10%'};


const Table = ({list}) =>
    <div className="table">
        <div className="table-row">
            <span style={largeColumn}>
                Name
            </span>
            <span style={smallColumn}>
                My Work
            </span>
            <span style={smallColumn}>
                Reviews
            </span>
            <span style={smallColumn}>
                Upstream
            </span>
            <span style={smallColumn}>
                My work
            </span>
            <span style={smallColumn}>
                Reviews
            </span>
            <span style={smallColumn}>
                Epic
            </span>
            <span style={smallColumn}>
                Committed
            </span>
            <span style={smallColumn}>
                Goal
            </span>
            <span style={smallColumn}>
                Remaining
            </span>
        </div>
        {list.map(item =>
            <div key={item.name} className="table-row">
                <span style={largeColumn}>
                    {item.name}
                </span>
                <span style={smallColumn}>
                        {Math.round(item.current_remaining_assignee_time / 3600)}
                </span>
                <span style={smallColumn}>
                        {Math.round(item.current_remaining_review_time / 3600)}
                </span>
                <span style={smallColumn}>
                        {Math.round(item.current_remaining_upstream_time / 3600)}
                </span>
                <span style={smallColumn}>
                        {Math.round(item.future_remaining_assignee_time / 3600)}
                </span>
                <span style={smallColumn}>
                        {Math.round(item.future_remaining_review_time / 3600)}
                </span>
                <span style={smallColumn}>
                        {Math.round(item.future_epic_management_time / 3600)}
                </span>
                <span style={smallColumn}>
                        {Math.round(item.committed_time / 3600)}
                </span>
                <span style={smallColumn}>
                        {Math.round(item.goal_time / 3600)}
                </span>
                <span style={smallColumn}>
                        {Math.round(item.remaining_time / 3600)}
                </span>
            </div>,
        )

        }
    </div>;

export default Table;
