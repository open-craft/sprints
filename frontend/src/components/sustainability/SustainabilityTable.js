import React from 'react';
import '../Table.css';
import {MAX_NON_BILLABLE_TO_BILLABLE_RATIO} from "../../constants";

const statusClass = (remaining) => Math.round(remaining) >= 0 ? 'on-track' : 'overtime';

const SustainabilityTable = ({accounts}) =>
    <div>
        <table className="table sustainability-table">
            <thead>
            <tr className="table-header">
                <td>
                    Billable hours
                </td>
                <td>
                    Non-billable cell hours
                </td>
                <td>
                    Non-billable to billable hours*
                </td>
                <td>
                    Remaining non-billable hours
                </td>
            </tr>
            </thead>
            <tbody>
            <tr className="table-row">
                <td>
                    {Math.round(accounts.billable)}
                </td>
                <td>
                    {Math.round(accounts.non_billable_responsible)}
                </td>
                <td className={statusClass(accounts.remaining)}>
                    {Math.round(accounts.responsible_ratio)}%
                </td>
                <td className={statusClass(accounts.remaining)}>
                    {Math.round(accounts.remaining)}
                </td>
            </tr>
            </tbody>
        </table>
        <div className="loading" align="left">
            * should be at most {MAX_NON_BILLABLE_TO_BILLABLE_RATIO * 100}%<br/>
            Total non-billable hours (non-billable hours + non-billable cell hours): {Math.round(accounts.non_billable_total)}<br/>
            Total non-billable to billable ratio: {Math.round(accounts.total_ratio)}%
        </div>
    </div>;

export default SustainabilityTable;
