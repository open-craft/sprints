import React from 'react';
import '../Table.css';
import {Link} from "react-router-dom";
import {PATH_JIRA_ISSUE} from "../../constants";

const nameColumn = {width: '20%'};  // 1 cell
const spilloverColumn = {width: '28%'};   // 1 cell
const newWorkColumn = {width: '52%'};   // 1 cell
const timeColumn = {width: '6%'};  // 10 cells -> 60% total
const unestimatedColumn = {width: '10%'};  // 2 cells -> 20% total
const totalRowPlaceholder = {width: '62%'};  // 100% - nameColumn - 3 * timeColumn

const statusClass = (remaining) => Math.round(remaining) >= 0 ? '' : 'overcommitted';
const accumulateTime = (list, property) => {
    const accumulatedTime = list.reduce((acc, item) => acc + item[property], 0);
    return Math.round(accumulatedTime / 3600);
}

const Table = ({list, url}) =>
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
                Vacation
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
                    <Link to={`${url}/user/${item.name}`}>{item.name}</Link>
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
                            <a href={PATH_JIRA_ISSUE + ticket.key} title={ticket.summary} target="_blank" rel="noopener noreferrer">{ticket.key}</a>
                        </li>
                    )}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.future_assignee_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.future_review_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.future_epic_management_time / 3600)}
                </td>
                <td style={unestimatedColumn}>
                    {item.future_unestimated.map(ticket =>
                        <li key={ticket}>
                            <a href={PATH_JIRA_ISSUE + ticket.key} title={ticket.summary} target="_blank" rel="noopener noreferrer">{ticket.key}</a>
                        </li>
                    )}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.vacation_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.committed_time / 3600)}
                </td>
                <td style={timeColumn}>
                    {Math.round(item.goal_time / 3600)}
                </td>
                <td style={timeColumn} className={statusClass(item.remaining_time)}>
                    {Math.round(item.remaining_time / 3600)}
                </td>
            </tr>,
        )}
        <tr className="table-row">
            <td style={nameColumn}>
                <abbr title="Note that these might not be the accurate sums of the values above, because the calculations are performed on seconds and then they are rounded to hours.">
                    <b>Total</b>
                </abbr>
            </td>
            <td style={totalRowPlaceholder}/>
            <td style={timeColumn}>
                {accumulateTime(list, 'committed_time')}
            </td>
            <td style={timeColumn}>
                {accumulateTime(list, 'goal_time')}
            </td>
            <td style={timeColumn}>
                {accumulateTime(list, 'remaining_time')}
            </td>
        </tr>
        </tbody>
    </table>;

export default Table;
