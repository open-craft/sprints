import React from 'react';
import '../Table.css';
import {ACCOUNT_STRIP_NAMES, DOCS} from "../../constants";

const nameColumn = {width: '35%'};  // 1 cells -> 35% total
const timeColumn = {width: '7.5%'};  // 6 cells -> 45% total
const categoryColumn = {width: '20%'};  // 1 cells -> 20% total

const statusClass = (remaining, optional = 0) => Math.round(remaining - optional) >= 0 ? 'on-track' : 'overtime';
const showBudget = budgets =>
    budgets
        ? Object.entries(budgets).reduce((result, [key, value]) =>
            `${result}\n${key}: ${value}`, '').trim()
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
                    <a href={`${DOCS}#column-budget`} title="Account name with the prefix stripped for better readability." target='_blank' rel='noopener noreferrer'>
                        Budget
                    </a>
                </td>
                <td style={timeColumn}>
                    <a href={`${DOCS}#column-ytd-spent`} title="Time spent from the beginning of the first year within the selected period." target='_blank' rel='noopener noreferrer'>
                        YTD Spent
                    </a>
                </td>
                <td style={timeColumn}>
                    <a href={`${DOCS}#column-ytd-goal`} title="Goal from the beginning of the first year within the selected period to the end of the next sprint." target='_blank' rel='noopener noreferrer'>
                        YTD Goal
                    </a>
                </td>
                <td style={timeColumn}>
                    <a href={`${DOCS}#column-period-spent`} title="Time spent during the selected period." target='_blank' rel='noopener noreferrer'>
                        Period Spent
                    </a>
                </td>
                <td style={timeColumn}>
                    <a href={`${DOCS}#column-period-goal`} title="Goal for the selected period." target='_blank' rel='noopener noreferrer'>
                        Period Goal
                    </a>
                </td>
                <td style={timeColumn}>
                    <a href={`${DOCS}#column-left-this-sprint`} title="Time scheduled for the incomplete tickets in the current sprint." target='_blank' rel='noopener noreferrer'>
                        Left this sprint
                    </a>
                </td>
                <td style={timeColumn}>
                    <a href={`${DOCS}#column-next-sprint`} title="Time scheduled for the tickets in the next sprint." target='_blank' rel='noopener noreferrer'>
                        Next sprint
                    </a>
                </td>
                <td style={timeColumn}>
                    <a href={`${DOCS}#column-remaining-for-next-sprint`} title="Time that can still be assigned for the next sprint. This value is the same for all views." target='_blank' rel='noopener noreferrer'>
                        Remaining for next sprint
                    </a>
                </td>
                <td style={categoryColumn}>
                    <a href={`${DOCS}#column-category`} target='_blank' rel='noopener noreferrer'>
                        Category
                    </a>
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
                        {
                            item.ytd_overall >= 1
                                ? Math.round(item.ytd_overall)
                                : item.ytd_overall.toFixed(1)
                        }
                    </td>
                    <td style={timeColumn}>
                        {Math.round(item.ytd_goal)}
                    </td>
                    <td style={timeColumn} className={view === "cells" ? statusClass(item.period_goal, item.overall) : ''}>
                        {item.overall >= 1 ? Math.round(item.overall) : item.overall.toFixed(1)}
                    </td>
                    <td style={timeColumn}>
                        {Math.round(item.period_goal)}
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
