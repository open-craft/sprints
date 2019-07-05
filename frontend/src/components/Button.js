import React from 'react';


const Button = ({onClick, id, data = '', className = '', children}) =>
    <button
        onClick={onClick}
        className={className}
        id={id}
        data={data}
        type="button"
    >
        {children}
    </button>;

export default Button;
