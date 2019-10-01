import {combineReducers} from 'redux';
import auth from "./auth";
import sprints from "./sprints";
import sustainability from "./sustainability";


export default combineReducers({
    auth,
    sprints,
    sustainability,
});
