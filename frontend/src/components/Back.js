import Button from "./Button";
import React, {Component} from 'react';
import {Link} from "react-router-dom";


class Back extends Component {
    render() {
        // Strip the last two parts of the url (which are in format `/view/id` to go `up` in the dashboard's structure.
        const path = this.props.path.split("/").slice(0, -2).join("/") || "/";
        return (
            <Link to={path}><Button>Go back</Button></Link>
        );
    }
}

export default Back;
