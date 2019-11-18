import React from 'react';
import '../Table.css';
import {ACCOUNT_STRIP_NAMES} from "../../constants";

const nameColumn = {width: '35%'};  // 1 cells -> 35 total
const timeColumn = {width: '9%'};  // 5 cells -> 45% total
const categoryColumn = {width: '20%'};  // 1 cells -> 20% total

const statusClass = (remaining, optional = 0) => Math.round(remaining - optional) >= 0 ? 'on-track' : 'overtime';
const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const showBudget = budgets =>
    budgets
        ? budgets.reduce((result, budget, index) =>
            `${result}\n${monthNames[index]}: ${budget}`, '')
        : '';
const stripAccountName = name => {
    ACCOUNT_STRIP_NAMES.forEach(strip => name = name.replace(strip, ''));
    return name;
};

const BudgetTable = ({accounts, view}) =>
    <div>
        <table className="table sustainability-table">
            <thead>
            <tr className="table-header">
                <td style={nameColumn}>
                    <abbr title="Account name with the prefix stripped for better readability.">
                        Budget
                    </abbr>
                </td>
                <td style={timeColumn}>
                    <abbr title="Time spent from the beginning of the first year within the selected period.">
                        YTD Spent
                    </abbr>
                </td>
                <td style={timeColumn}>
                    <abbr title="Goal from the beginning of the first year within the selected period and the end of the next sprint.">
                        YTD Goal
                    </abbr>
                </td>
                <td style={timeColumn}>
                    <abbr title="Time spent during the selected period.">
                        Period Spent
                    </abbr>
                </td>
                <td style={timeColumn}>
                    <abbr title="Time scheduled for the incomplete tickets in the current sprint.">
                        Left this sprint
                    </abbr>
                </td>
                <td style={timeColumn}>
                    <abbr title="Time scheduled for the tickets in the next sprint.">
                        Next sprint
                    </abbr>
                </td>
                <td style={timeColumn}>
                    <abbr title="Time that can still be assigned for the next sprint. This value is the same for all views.">
                        Remaining for next sprint
                    </abbr>
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
                            {stripAccountName(item.name)}
                        </abbr>
                    </td>
                    <td style={timeColumn} className={view === "cells" ? statusClass(item.ytd_goal, item.ytd_overall) : ''}>
                        {item.ytd_overall >= 1 ? Math.round(item.ytd_overall) : item.ytd_overall.toFixed(1)}
                    </td>
                    <td style={timeColumn}>
                        {Math.round(item.ytd_goal)}
                    </td>
                    <td style={timeColumn}>
                        {item.overall >= 1 ? Math.round(item.overall) : item.overall.toFixed(1)}
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
