import React from 'react';
import Button from './Button';

const Cells = ({list, handle_click}) =>
    <ul>
        {list.map(item =>
            <li key={item.name}>
                <Button
                    onClick={handle_click}
                    id={item.name}>
                    {item.name}
                </Button>
            </li>
        )}
    </ul>;

export default Cells;
