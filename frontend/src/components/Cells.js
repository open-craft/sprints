import React from 'react';
import {Link} from "react-router-dom";

const Cells = ({list}) =>
    <ul>
        {list.map(item =>
            <li key={item.name}>
                <Link to={`board/${item.board_id}`}>{item.name}</Link>
            </li>
        )}
    </ul>;

export default Cells;
