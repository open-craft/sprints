import React from 'react';


const Button = ({onClick, id, className = '', children}) =>
    <button
        onClick={onClick}
        className={className}
        id={id}
        type="button"
    >
        {children}
    </button>;

export default Button;
