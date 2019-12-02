import React from 'react';
import '../Table.css';
import {PATH_JIRA_ISSUE} from "../../constants";

const nameColumn = {width: '25%'};  // 1 cells -> 25% total
const timeColumn = {width: '15%'};  // 5 cells -> 75% total

const UserTable = ({list, username}) =>
    <table className="table">
        <thead>
        <tr className="table-header">
            <td style={timeColumn}>
                Key
            </td>
            <td style={timeColumn}>
                Working As
            </td>
            <td style={nameColumn}>
                Status
            </td>
            <td style={timeColumn}>
                Remaining Time
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
                <td style={timeColumn}>
                    {
                        item.assignee === username
                            ? item.reviewer_1 === username
                                ? "Both"
                                : "Assignee"
                            : "Reviewer"
                    }
                </td>
                <td style={nameColumn}>
                    {item.status}
                </td>
                <td style={timeColumn}>
                    {
                        item.assignee === username
                            ? item.reviewer_1 === username
                                ? Math.round((item.assignee_time + item.review_time) / 3600)
                                : Math.round(item.assignee_time / 3600)
                            : Math.round(item.review_time / 3600)
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
