import React from 'react';
import './Table.css';

const nameColumn = {width: '24%'};  // 1 cell
const spilloverColumn = {width: '29%'};   // 1 cell
const newWorkColumn = {width: '47%'};   // 1 cell
const timeColumn = {width: '6%'};  // 9 cells -> 54% total
const unestimatedColumn = {width: '11%'};  // 2 cells -> 22% total

const ISSUE_PATH = 'https://tasks.opencraft.com/browse/';  // TODO: Move this to config.

const Table = ({list}) =>
    <table className="table">
        <thead>
        <tr className="table-header">
            <td style={nameColumn}/>
            <td style={spilloverColumn}>
                Spillover
            </td>
            <td style={newWorkColumn}>
                New Work
            </td>
        </tr>
        <tr className="table-header">
            <td style={nameColumn}>
                User
            </td>
            <td style={timeColumn}>
                My Work
            </td>
            <td style={timeColumn}>
                Reviews
            </td>
            <td style={timeColumn}>
                Upstream
            </td>
            <td style={unestimatedColumn}>
                Unestimated
            </td>
            <td style={timeColumn}>
                My work
            </td>
            <td style={timeColumn}>
                Reviews
            </td>
            <td style={timeColumn}>
                Epic
            </td>
            <td style={unestimatedColumn}>
                Unestimated
            </td>
            <td style={timeColumn}>
                Committed
            </td>
            <td style={timeColumn}>
                Goal
            </td>
            <td style={timeColumn}>
                Remaining
            </td>
        </tr>
        </thead>
        <tbody>
        {list.map(item =>
            <tr key={item.name} className="table-row">
                <td style={nameColumn}>
                    {item.name}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.current_remaining_assignee_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.current_remaining_review_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.current_remaining_upstream_time / 3600)}
                </td>
                <td style={unestimatedColumn}>
                    {item.current_unestimated.map(ticket =>
                        <li key={ticket}>
                            <a href={ISSUE_PATH + ticket} target="_blank" rel="noopener noreferrer">{ticket}</a>
                        </li>
                    )}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.future_remaining_assignee_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.future_remaining_review_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.future_epic_management_time / 3600)}
                </td>
                <td style={unestimatedColumn}>
                    {item.future_unestimated.map(ticket =>
                        <li key={ticket}>
                            <a href={ISSUE_PATH + ticket} target="_blank" rel="noopener noreferrer">{ticket}</a>
                        </li>
                    )}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.committed_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.goal_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.remaining_time / 3600)}
                </td>
            </tr>,
        )}
        </tbody>
    </table>;

export default Table;
