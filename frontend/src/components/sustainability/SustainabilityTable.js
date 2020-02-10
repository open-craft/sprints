import React from 'react';
import '../Table.css';
import {DOCS, MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO, MAX_NON_BILLABLE_TO_BILLABLE_RATIO} from "../../constants";

const statusClass = (remaining) => Math.round(remaining) >= 0 ? 'on-track' : 'overtime';

const overall_headers =
    <>
        <td>
            <a href={`${DOCS}#column-overall-total-hours`} target='_blank' rel='noopener noreferrer'>
                Total hours
            </a>

        </td>
        <td>
            <a href={`${DOCS}#column-overall-billable-hours`} target='_blank' rel='noopener noreferrer'>
                Billable hours
            </a>

        </td>
        <td>
            <a href={`${DOCS}#column-overall-non-billable-hours`} target='_blank' rel='noopener noreferrer'>
                Total non-billable hours
            </a>
        </td>
        <td>
            <a href={`${DOCS}#column-overall-percent-of-non-billable-hours`} target='_blank' rel='noopener noreferrer'>
                % non-billable
            </a>
        </td>
    </>;

const overall_fields = accounts =>
    <>
        <td>
            {Math.round(accounts.billable)}
        </td>
        <td>
            {Math.round(accounts.non_billable_total)}
        </td>
        <td className={statusClass(accounts.remaining)}>
            {Math.round(accounts.total_ratio)}% (max {MAX_NON_BILLABLE_TO_BILLABLE_RATIO * 100}%)
        </td>
    </>;

const overall_hints =
    <>
        <li>Total non-billable hours = non-billable cell hours + non-billable non-cell hours</li>
        <li>% non-billable = total non-billable hours / total hours</li>
    </>;

const cell_headers =
    <>
        <td>
            <a href={`${DOCS}#column-total-hours`} target='_blank' rel='noopener noreferrer'>
                Total hours
            </a>
        </td>
        <td>
            <a href={`${DOCS}#column-non-cell-hours`} target='_blank' rel='noopener noreferrer'>
                Non-cell hours
            </a>
        </td>
        <td>
            <a href={`${DOCS}#column-billable-cell-hours`} target='_blank' rel='noopener noreferrer'>
                Billable cell hours
            </a>
        </td>
        <td>
            <a href={`${DOCS}#column-non-billable-cell-hours`} target='_blank' rel='noopener noreferrer'>
                Non-billable cell hours
            </a>
        </td>
        <td>
            <a href={`${DOCS}#column-percent-of-non-billable-hours`} target='_blank' rel='noopener noreferrer'>
                % non-billable cell
            </a>
        </td>
        <td>
            <a href={`${DOCS}#column-remaining-non-billable-hours`} target='_blank' rel='noopener noreferrer'>
                Remaining non-billable hours
            </a>
        </td>
    </>;

const cell_fields = accounts =>
    <>
        <td>
            {Math.round(accounts.non_billable)}
        </td>
        <td>
            {Math.round(accounts.billable)}
        </td>
        <td>
            {Math.round(accounts.non_billable_responsible)}
        </td>
        <td className={statusClass(accounts.remaining_responsible)}>
            {Math.round(accounts.responsible_ratio)}% (max {MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO * 100}%)
        </td>
        <td className={statusClass(accounts.remaining_responsible)}>
            {Math.round(accounts.remaining_responsible)}
        </td>
    </>;

const cell_hints = accounts =>
    <>
        <li>Total hours = non-cell hours + cell hours</li>
        <li>Non-cell hours = hours logged on a task not belonging to the current cell</li>
        <li>Cell hours = billable cell hours + non-billable cell hours</li>
        <li>% non-billable = non-billable cell hours / cell hours</li>
        <li>Total non-billable hours (non-cell hours + non-billable cell hours): {Math.round(accounts.non_billable_total)}</li>
    </>;

const SustainabilityTable = ({accounts, view}) =>
    <div>
        <table className="table sustainability-table">
            <thead>
            <tr className="table-header">
                {
                    view === "cells"
                        ? overall_headers
                        : cell_headers
                }
            </tr>
            </thead>
            <tbody>
            <tr className="table-row">
                <td>
                    {Math.round(accounts.total)}
                </td>
                {
                    view === "cells"
                        ? overall_fields(accounts)
                        : cell_fields(accounts)
                }
            </tr>
            </tbody>
        </table>
        <div className="loading" align="left">
            <ul>
                {
                    view === "cells"
                        ? overall_hints
                        : cell_hints(accounts)
                }
            </ul>
        </div>
    </div>;

export default SustainabilityTable;
