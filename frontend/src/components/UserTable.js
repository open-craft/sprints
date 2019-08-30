import React from 'react';
import './Table.css';
import {PATH_JIRA_ISSUE} from "../constants";

const nameColumn = {width: '20%'};  // 2 cells -> 40%
const timeColumn = {width: '10%'};  // 6 cells -> 60% total

const UserTable = ({list, username}) =>
    <table className="table">
        <thead>
        <tr className="table-header">
            <td style={timeColumn}>
                Key
            </td>
            <td style={nameColumn}>
                Assignee
            </td>
            <td style={nameColumn}>
                Reviewer 1
            </td>
            <td style={timeColumn}>
                Status
            </td>
            <td style={timeColumn}>
                Assignee Time
            </td>
            <td style={timeColumn}>
                Reviewer Time
            </td>
            <td style={timeColumn}>
                Current Sprint
            </td>
            <td style={timeColumn}>
                Is Epic
            </td>
        </tr>
        </thead>
        <tbody>
        {list.map(item =>
            <tr key={item.key} className={"table-row"}>
                <td style={timeColumn}>
                    <a href={PATH_JIRA_ISSUE + item.key} title={item.summary} target="_blank"
                       rel="noopener noreferrer">{item.key}</a>
                </td>
                <td style={nameColumn}>
                    {item.assignee}
                </td>
                <td style={nameColumn}>
                    {item.reviewer_1}
                </td>
                <td style={timeColumn}>
                    {item.status}
                </td>
                <td style={timeColumn}>
                    {
                        item.assignee === username
                            ? Math.round(item.assignee_time / 3600)
                            : null
                    }
                </td>
                <td style={timeColumn}>
                    {
                        item.reviewer_1 === username
                            ? Math.round(item.review_time / 3600)
                            : null
                    }
                </td>
                <td style={timeColumn}>
                    {
                        item.current_sprint
                            ? "✔"
                            : ""
                    }
                </td>
                <td style={timeColumn}>
                    {
                        item.is_epic
                            ? "✔"
                            : ""
                    }
                </td>
            </tr>,
        )}
        </tbody>
    </table>;

export default UserTable;
