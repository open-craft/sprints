import React from 'react';
import '../Table.css';
import {MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO, MAX_NON_BILLABLE_TO_BILLABLE_RATIO} from "../../constants";

const statusClass = (remaining) => Math.round(remaining) >= 0 ? 'on-track' : 'overtime';

const overall_headers =
    <>
        <td>
            Billable hours
        </td>
        <td>
            Total non-billable hours
        </td>
        <td>
            % non-billable
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
            Non-cell hours
        </td>
        <td>
            Billable cell hours
        </td>
        <td>
            Non-billable cell hours
        </td>
        <td>
            % non-billable cell
        </td>
        <td>
            Remaining non-billable hours
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
        <li>Total non-billable hours (non-billable hours + non-billable cell hours): {Math.round(accounts.non_billable_total)}</li>
    </>;

const SustainabilityTable = ({accounts, view}) =>
    <div>
        <table className="table sustainability-table">
            <thead>
            <tr className="table-header">
                <td>
                    Total hours
                </td>
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
