import React from 'react';
import '../Table.css';

const nameColumn = {width: '35%'};  // 1 cells -> 35 total
const timeColumn = {width: '9%'};  // 5 cells -> 45% total
const categoryColumn = {width: '20%'};  // 1 cells -> 20% total

const statusClass = (remaining) => Math.round(remaining) >= 0 ? 'on-track' : 'overtime';

const BudgetTable = ({accounts}) =>
    <div>
        <table className="table sustainability-table">
            <thead>
            <tr className="table-header">
                <td style={nameColumn}>
                    Budget
                </td>
                <td style={timeColumn}>
                    YTD Spent
                </td>
                <td style={timeColumn}>
                    YTD Goal
                </td>
                <td style={timeColumn}>
                    Left this sprint
                </td>
                <td style={timeColumn}>
                    Next sprint
                </td>
                <td style={timeColumn}>
                    Remaining for next sprint
                </td>
                <td style={categoryColumn}>
                    Category
                </td>
            </tr>
            </thead>
            <tbody>
            {accounts.map(item =>
                <tr key={item.key} className="table-row">
                    <td style={nameColumn}>
                        {item.name}
                    </td>
                    <td style={timeColumn}>
                        {Math.round(item.overall)}
                    </td>
                    <td style={timeColumn}>
                        {Math.round(item.ytd_goal)}
                    </td>
                    <td style={timeColumn}>
                        {Math.round(item.left_this_sprint)}
                    </td>
                    <td style={timeColumn}>
                        {Math.round(item.planned_next_sprint)}
                    </td>
                    <td style={timeColumn} className={statusClass(item.remaining_next_sprint)}>
                        {Math.round(item.remaining_next_sprint)}
                    </td>
                    <td style={categoryColumn}>
                        {item.category}
                    </td>
                </tr>
            )}
            </tbody>
        </table>
    </div>;

export default BudgetTable;
