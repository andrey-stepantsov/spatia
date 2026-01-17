import React from 'react';
import logoLight from '../assets/logo-light.png';
import logoDark from '../assets/logo-dark.png';

export const SpatiaLogo = ({ theme = 'dark', className = '', ...props }) => {
    // If theme is 'light', use logoLight (dark lines).
    // If theme is 'dark', use logoDark (light lines).

    const src = theme === 'light' ? logoLight : logoDark;

    return (
        <img
            src={src}
            alt="Spatia Logo"
            className={`select-none ${className}`}
            {...props}
        />
    );
};

export default SpatiaLogo;
