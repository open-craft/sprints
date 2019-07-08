import {combineReducers} from 'redux';
import auth from "./auth";


const sprints_reducers = combineReducers({
    auth,
});

export default sprints_reducers;
