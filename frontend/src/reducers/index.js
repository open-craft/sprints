import {combineReducers} from 'redux';
import auth from "./auth";
import sprints from "./sprints";


export default combineReducers({
    auth,
    sprints,
});
