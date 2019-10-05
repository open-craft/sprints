import React from 'react';
import '../Table.css';

const nameColumn = {width: '35%'};  // 1 cells -> 35 total
const timeColumn = {width: '9%'};  // 5 cells -> 45% total
const categoryColumn = {width: '20%'};  // 1 cells -> 20% total

const statusClass = (remaining, optional=0) => Math.round(remaining - optional) >= 0 ? 'on-track' : 'overtime';
const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const showBudget = (budgets) =>
    budgets
        ? budgets.reduce((result, budget, index) =>
            `${result}\n${monthNames[index]}: ${budget}`, '')
        : '';

const BudgetTable = ({accounts, view}) =>
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
                <tr key={item.name} className="table-row">
                    <td style={nameColumn}>
                        <abbr title={showBudget(item.budgets)}>
                            {item.name}
                        </abbr>
                    </td>
                    <td style={timeColumn} className={view === "cells" ? statusClass(item.ytd_goal, item.overall) : ''}>
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
